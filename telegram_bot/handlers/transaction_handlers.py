from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from decimal import Decimal
from django.db import transaction
from fin.models import Transaction, Account, Category
from ..utils.keyboards import get_keyboard
from ..utils.constants import STATES
from ..utils.messages import random_message
from .account_handlers import get_account_by_name
from .category_handlers import get_all_categories, get_category_by_name

@sync_to_async
def create_new_transaction(transaction_type, amount, account, category, currency):
    """Create a new transaction."""
    return Transaction.objects.create(
        transaction_type=transaction_type,
        amount=amount,
        account=account,
        category=category,
        currency=currency
    )

async def add_transaction_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the transaction creation process."""
    await update.message.reply_text(
        "Виберіть тип транзакції:",
        reply_markup=get_keyboard('transaction_types')
    )
    return STATES.CHOOSING_TRANSACTION_TYPE

async def choose_transaction_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the transaction type and ask for amount."""
    transaction_type = update.message.text
    
    if transaction_type == '💵 Прибуток':
        context.user_data['transaction_type'] = 'INCOME'
    elif transaction_type == '💸 Витрата':
        context.user_data['transaction_type'] = 'EXPENSE'
    else:
        await update.message.reply_text(
            "❌ Невірний тип транзакції. Спробуйте ще раз.",
            reply_markup=get_keyboard('transaction_types')
        )
        return STATES.CHOOSING_TRANSACTION_TYPE
    
    await update.message.reply_text(
        "Введіть суму:",
        reply_markup=get_keyboard('back')
    )
    return STATES.ENTERING_AMOUNT

async def enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the amount and ask for account selection."""
    try:
        amount = Decimal(update.message.text.replace(',', '.'))
        if amount <= 0:
            raise ValueError("Amount must be positive")
        context.user_data['amount'] = amount
        
        accounts = await get_all_accounts()
        if not accounts:
            await update.message.reply_text(
                "❌ У вас ще немає жодного рахунку. Спочатку створіть рахунок!",
                reply_markup=get_keyboard('main')
            )
            return STATES.CHOOSING_ACTION
        
        keyboard = [[account.name] for account in accounts]
        keyboard.append(['↩️ Назад до меню'])
        
        await update.message.reply_text(
            "Виберіть рахунок:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return STATES.CHOOSING_ACCOUNT
        
    except (ValueError, TypeError) as e:
        await update.message.reply_text(
            "❌ Невірний формат суми. Введіть число більше 0:",
            reply_markup=get_keyboard('back')
        )
        return STATES.ENTERING_AMOUNT

async def choose_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the account selection and ask for category."""
    account_name = update.message.text
    
    try:
        account = await get_account_by_name(account_name)
        context.user_data['account'] = account
        
        categories = await get_all_categories()
        if not categories:
            await update.message.reply_text(
                "❌ У вас ще немає жодної категорії. Спочатку створіть категорію!",
                reply_markup=get_keyboard('main')
            )
            return STATES.CHOOSING_ACTION
        
        keyboard = [[category.name] for category in categories]
        keyboard.append(['↩️ Назад до меню'])
        
        await update.message.reply_text(
            "Виберіть категорію:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return STATES.CHOOSING_CATEGORY
        
    except Account.DoesNotExist:
        await update.message.reply_text(
            "❌ Рахунок не знайдено. Спробуйте ще раз.",
            reply_markup=get_keyboard('main')
        )
        return STATES.CHOOSING_ACTION

async def choose_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the category selection and create the transaction."""
    category_name = update.message.text
    
    try:
        category = await get_category_by_name(category_name)
        account = context.user_data['account']
        
        # Create transaction
        with transaction.atomic():
            new_transaction = await create_new_transaction(
                context.user_data['transaction_type'],
                context.user_data['amount'],
                account,
                category,
                account.currency
            )
            
            # Update account balance
            if context.user_data['transaction_type'] == 'INCOME':
                account.balance += context.user_data['amount']
            else:
                if account.balance < context.user_data['amount']:
                    raise ValueError(f'Недостатньо коштів на рахунку {account.name}')
                account.balance -= context.user_data['amount']
            
            await sync_to_async(account.save)()
        
        await update.message.reply_text(
            random_message('SUCCESS_TRANSACTION'),
            reply_markup=get_keyboard('main')
        )
        return STATES.CHOOSING_ACTION
        
    except Category.DoesNotExist:
        await update.message.reply_text(
            "❌ Категорію не знайдено. Спробуйте ще раз.",
            reply_markup=get_keyboard('main')
        )
        return STATES.CHOOSING_ACTION
    except ValueError as e:
        await update.message.reply_text(
            f"❌ {str(e)}",
            reply_markup=get_keyboard('main')
        )
        return STATES.CHOOSING_ACTION
    except Exception as e:
        print(f"Error creating transaction: {e}")
        await update.message.reply_text(
            "❌ Помилка при створенні транзакції. Спробуйте ще раз.",
            reply_markup=get_keyboard('main')
        )
        return STATES.CHOOSING_ACTION
