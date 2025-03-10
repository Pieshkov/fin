import logging
import os
import random
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)
from django.conf import settings
from fin.models import Account, Category, Transaction
from decimal import Decimal
from asgiref.sync import sync_to_async
from django.db.models import Sum
from datetime import datetime, timedelta
import calendar
import csv
import os
from django.utils import timezone
from django.db import transaction

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Жартівливі фрази
GREETING_PHRASES = [
    "О, кого я бачу! Знову прийшов грошенята рахувати? 💰",
    "Привіт, транжиро! Показуй свої фінансові подвиги! 🎭",
    "Ого, живий! А я думав ти вже все профукав! 😅",
    "Знову ти? Ну давай подивимось, що там у твоєму гаманці... 👀",
    "О, мій улюблений марнотратник! Що будемо робити? 🎪"
]

BALANCE_PHRASES = [
    "Тримайся міцніше, зараз покажу твої багатства! 💎",
    "Так-так, подивимось що ти там назбирав... 🔍",
    "Барабанний дріб! Ось твої фінансові досягнення: 🥁",
    "Увага! Зараз буде боляче... але ось твої баланси: 💉",
    "Присядь, бо від цих цифр можна знепритомніти! 😱"
]

SUCCESS_TRANSACTION_PHRASES = [
    "Єєєє! Транзакцію записано! Може ще щось намутимо? 🎯",
    "Готово! Гроші успішно протрачено/зароблено! 🎪",
    "Ще одна транзакція в копілочку! Що далі, фінансовий геній? 🧠",
    "Бінго! Операцію записано. Продовжуємо збагачуватись? 💫",
    "Готово! Давай ще щось запишемо, поки я добрий! 😈"
]

CANCEL_PHRASES = [
    "Ех, а я тільки розігрівся... Ну добре, що далі робимо? 🎭",
    "Скасовано! Злякався великих цифр? 😱",
    "Нічого-нічого, наступного разу пощастить! Що робимо? 🎲",
    "Операцію скасовано! Може спробуємо щось інше? 🎪",
    "Ну і правильно, нащо воно тобі треба... То що далі? 😏"
]

# Keyboard layouts
main_keyboard = [
    ['💰 Додати транзакцію', '🏦 Додати рахунок'],
    ['📊 Баланси рахунків', '📈 Статистика'],
    ['📥 Імпорт CSV', '🏷️ Додати категорію'],
    ['🗑️ Очистити транзакції']
]

transaction_types = [
    ['💵 Прибуток', '💸 Витрата'],
    ['↩️ Назад до меню'],
]

# Conversation states
(
    START_STATE,
    CHOOSING_ACTION,
    ADDING_TRANSACTION,
    CHOOSING_TRANSACTION_TYPE,
    ENTERING_AMOUNT,
    CHOOSING_ACCOUNT,
    CHOOSING_CATEGORY,
    ENTERING_COMMENT,
    CONFIRM_TRANSACTION,
    CHOOSING_STATS_PERIOD,
    UPLOADING_CSV,
    CHOOSING_CSV_ACCOUNT,
    CONFIRM_CLEAR,
    CONFIRMING_CLEAR,
) = range(14)

# Асинхронні функції для роботи з моделями
@sync_to_async
def get_all_accounts():
    return list(Account.objects.all())

@sync_to_async
def get_all_categories():
    return list(Category.objects.all())

@sync_to_async
def get_account_by_name(name):
    return Account.objects.get(name=name)

@sync_to_async
def get_category_by_name(name):
    return Category.objects.get(name=name)

@sync_to_async
def create_new_account(name, account_type, currency):
    return Account.objects.create(
        name=name,
        account_type=account_type,
        currency=currency,
        balance=0
    )

@sync_to_async
def create_new_category(name):
    return Category.objects.create(name=name)

@sync_to_async
def create_new_transaction(transaction_type, amount, account, category, currency):
    return Transaction.objects.create(
        transaction_type=transaction_type,
        amount=amount,
        account=account,
        category=category,
        currency=currency
    )

@sync_to_async
def get_expenses_statistics(start_date):
    return list(Transaction.objects.filter(
        transaction_type='EXPENSE',
        date__gte=start_date
    ).values(
        'category__name',
        'currency'
    ).annotate(
        total=Sum('amount')
    ).order_by('-total'))

@sync_to_async
def get_incomes_statistics(start_date):
    return list(Transaction.objects.filter(
        transaction_type='INCOME',
        date__gte=start_date
    ).values(
        'category__name',
        'currency'
    ).annotate(
        total=Sum('amount')
    ).order_by('-total'))

@sync_to_async
def get_statistics(period):
    """Get statistics for given period."""
    try:
        now = timezone.now()
        
        if period == 'week':
            start_date = now - timedelta(days=7)
            period_name = "за тиждень"
        elif period == 'month':
            start_date = now - timedelta(days=30)
            period_name = "за місяць"
        elif period == 'year':
            start_date = now - timedelta(days=365)
            period_name = "за рік"
        
        # Отримуємо всі транзакції за період
        expenses = Transaction.objects.filter(
            transaction_type='EXPENSE',
            date__gte=start_date
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        incomes = Transaction.objects.filter(
            transaction_type='INCOME',
            date__gte=start_date
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        # Отримуємо статистику по категоріях для витрат
        expenses_by_category = list(Transaction.objects.filter(
            transaction_type='EXPENSE',
            date__gte=start_date
        ).values(
            'category__name'
        ).annotate(
            total=Sum('amount')
        ).order_by('-total'))
        
        # Отримуємо статистику по категоріях для доходів
        incomes_by_category = list(Transaction.objects.filter(
            transaction_type='INCOME',
            date__gte=start_date
        ).values(
            'category__name'
        ).annotate(
            total=Sum('amount')
        ).order_by('-total'))
        
        return expenses, incomes, period_name, expenses_by_category, incomes_by_category
    except Exception as e:
        print(f"Error in get_statistics: {e}")
        raise

@sync_to_async
def get_all_time_statistics():
    """Get statistics for all time."""
    try:
        # Отримуємо всі транзакції
        expenses = Transaction.objects.filter(
            transaction_type='EXPENSE'
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        incomes = Transaction.objects.filter(
            transaction_type='INCOME'
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        # Отримуємо статистику по категоріях для витрат
        expenses_by_category = list(Transaction.objects.filter(
            transaction_type='EXPENSE'
        ).values(
            'category__name'
        ).annotate(
            total=Sum('amount')
        ).order_by('-total'))
        
        # Отримуємо статистику по категоріях для доходів
        incomes_by_category = list(Transaction.objects.filter(
            transaction_type='INCOME'
        ).values(
            'category__name'
        ).annotate(
            total=Sum('amount')
        ).order_by('-total'))
        
        return expenses, incomes, "за весь час", expenses_by_category, incomes_by_category
    except Exception as e:
        print(f"Error in get_all_time_statistics: {e}")
        raise

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and show main menu."""
    reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
    await update.message.reply_text(
        random.choice(GREETING_PHRASES),
        reply_markup=reply_markup,
    )
    return CHOOSING_ACTION

async def view_balances(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show all accounts and their balances."""
    accounts = await get_all_accounts()
    
    if not accounts:
        await update.message.reply_text("Йой, а в тебе ще немає жодного рахунку! Давай створимо, бо так діла не буде! 😱")
        return CHOOSING_ACTION
    
    message = f"{random.choice(BALANCE_PHRASES)}\n\n"
    for account in accounts:
        message += f"💼 {account.name}: {account.balance} {account.currency}\n"

    await update.message.reply_text(message)
    return CHOOSING_ACTION

async def add_account_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the account creation process."""
    await update.message.reply_text(
        "Давай створимо новий рахунок! Як назвемо? 🤔",
        reply_markup=ReplyKeyboardMarkup([['↩️ Скасувати']], resize_keyboard=True),
    )
    return ADDING_TRANSACTION

async def add_account_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the account name and ask for account type."""
    context.user_data['account_name'] = update.message.text
    keyboard = [['💵 CASH', '💳 CARD'], ['🏦 SAVINGS', '📦 OTHER'], ['↩️ Скасувати']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "А тепер обери тип рахунку, тільки не помились! 🎯",
        reply_markup=reply_markup,
    )
    return CHOOSING_TRANSACTION_TYPE

async def add_account_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the account type and ask for currency."""
    text = update.message.text
    if text == '↩️ Скасувати':
        return await cancel(update, context)

    type_mapping = {
        '💵 CASH': 'CASH',
        '💳 CARD': 'CARD',
        '🏦 SAVINGS': 'SAVINGS',
        '📦 OTHER': 'OTHER'
    }
    
    account_type = type_mapping.get(text)
    if not account_type:
        await update.message.reply_text("Ой, щось не те... Обери тип рахунку з кнопок! 🎯")
        return CHOOSING_TRANSACTION_TYPE

    context.user_data['account_type'] = account_type
    keyboard = [['💶 EUR', '💵 USD', '💴 UAH'], ['↩️ Скасувати']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "І яка валюта буде в цьому рахунку? 💰",
        reply_markup=reply_markup,
    )
    return ENTERING_AMOUNT

async def add_account_currency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the currency and create the account."""
    text = update.message.text
    if text == '↩️ Скасувати':
        return await cancel(update, context)

    currency_mapping = {
        '💶 EUR': 'EUR',
        '💵 USD': 'USD',
        '💴 UAH': 'UAH'
    }
    
    currency = currency_mapping.get(text)
    if not currency:
        await update.message.reply_text("Ой, щось не те... Обери валюту з кнопок! 💰")
        return ENTERING_AMOUNT

    try:
        account = await create_new_account(
            name=context.user_data['account_name'],
            account_type=context.user_data['account_type'],
            currency=currency
        )
        await update.message.reply_text(
            f"Єєє! Рахунок '{account.name}' створено! Тепер можна починати збагачуватись! 🎉"
        )
    except Exception as e:
        await update.message.reply_text(f"Ой-ой, щось пішло не так: {str(e)} 😅")
        return CHOOSING_ACTION
    
    # Clear user data
    context.user_data.clear()
    
    # Show main menu
    reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Що далі робимо, фінансовий геній? 🧠",
        reply_markup=reply_markup,
    )
    return CHOOSING_ACTION

async def add_category_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the category creation process."""
    await update.message.reply_text(
        "О, нова категорія? Давай придумаємо їй круту назву! 🎨"
    )
    return ADDING_TRANSACTION

async def add_category_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the category name and create the category."""
    category_name = update.message.text
    try:
        category = await create_new_category(name=category_name)
        await update.message.reply_text(f"Єєє! Категорію '{category.name}' створено! Тепер можна сміливо гроші витрачати! 🎉")
    except Exception as e:
        await update.message.reply_text(f"Ой-ой, щось пішло не так: {str(e)} 😅")
    
    reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
    await update.message.reply_text("Що далі робимо, фінансовий геній? 🧠", reply_markup=reply_markup)
    return CHOOSING_ACTION

async def add_transaction_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the transaction creation process."""
    reply_markup = ReplyKeyboardMarkup(transaction_types, resize_keyboard=True)
    await update.message.reply_text(
        "Що там у нас - збагачуємось чи збіднюємось? 💸",
        reply_markup=reply_markup,
    )
    return CHOOSING_TRANSACTION_TYPE

async def choose_transaction_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the transaction type and ask for amount."""
    text = update.message.text
    if text == '💵 Прибуток':
        context.user_data['transaction_type'] = 'INCOME'
        await update.message.reply_text("Ого! Скільки грошенят привалило? 🤑")
    elif text == '💸 Витрата':
        context.user_data['transaction_type'] = 'EXPENSE'
        await update.message.reply_text("Ну і скільки цього разу профукали? 💸")
    else:
        return CHOOSING_ACTION
    return ENTERING_AMOUNT

async def enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the amount and ask for account selection."""
    try:
        amount = Decimal(update.message.text)
        context.user_data['amount'] = amount
        
        accounts = await get_all_accounts()
        if not accounts:
            await update.message.reply_text("Ой, а де ж рахунки? Треба спочатку створити хоч один! 😱")
            return CHOOSING_ACTION
        
        keyboard = [[account.name] for account in accounts]
        keyboard.append(['↩️ Скасувати'])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "А тепер обери рахунок, куди запишемо цю операцію: 📝",
            reply_markup=reply_markup,
        )
        return CHOOSING_ACCOUNT
    except ValueError:
        await update.message.reply_text("Ей! Це що за ієрогліфи? Давай нормальне число! 🤨")
        return ENTERING_AMOUNT

async def choose_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the account selection and ask for category."""
    account_name = update.message.text
    try:
        account = await get_account_by_name(account_name)
        context.user_data['account'] = account
        
        categories = await get_all_categories()
        if not categories:
            await update.message.reply_text("Ой, а категорій то немає! Давай створимо хоч одну! 🎨")
            return CHOOSING_ACTION
        
        keyboard = [[category.name] for category in categories]
        keyboard.append(['↩️ Скасувати'])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "І під яку категорію це діло підпадає? 🎯",
            reply_markup=reply_markup,
        )
        return CHOOSING_CATEGORY
    except Account.DoesNotExist:
        await update.message.reply_text("Хм... Щось я такого рахунку не знаю. Спробуй ще раз! 🔍")
        return CHOOSING_ACCOUNT

async def choose_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the category selection and create the transaction."""
    category_name = update.message.text
    try:
        category = await get_category_by_name(category_name)
        
        # Create the transaction
        transaction = await create_new_transaction(
            transaction_type=context.user_data['transaction_type'],
            amount=context.user_data['amount'],
            account=context.user_data['account'],
            category=category,
            currency=context.user_data['account'].currency
        )
        
        # Clear user data
        context.user_data.clear()
        
        await update.message.reply_text(random.choice(SUCCESS_TRANSACTION_PHRASES))
        
        # Show main menu
        reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "Що далі будемо робити? 🎲",
            reply_markup=reply_markup,
        )
        return CHOOSING_ACTION
    except Category.DoesNotExist:
        await update.message.reply_text("Хм... Такої категорії немає. Може спробуєш іншу? 🤔")
        return CHOOSING_CATEGORY
    except Exception as e:
        await update.message.reply_text(f"Ой-ой! Щось пішло не так: {str(e)} 😅")
        return CHOOSING_ACTION

async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show statistics menu."""
    keyboard = [
        ['📊 За тиждень', '📈 За місяць'],
        ['📉 За рік', '📋 За весь час'],
        ['↩️ Назад до меню']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "📊 Виберіть період для перегляду статистики:",
        reply_markup=reply_markup
    )
    
    return CHOOSING_STATS_PERIOD

async def show_period_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show statistics for selected period."""
    try:
        if update.message.text == '📊 За тиждень':
            expenses, incomes, period_name, expenses_by_category, incomes_by_category = await get_statistics('week')
        elif update.message.text == '📈 За місяць':
            expenses, incomes, period_name, expenses_by_category, incomes_by_category = await get_statistics('month')
        elif update.message.text == '📉 За рік':
            expenses, incomes, period_name, expenses_by_category, incomes_by_category = await get_statistics('year')
        elif update.message.text == '📋 За весь час':
            expenses, incomes, period_name, expenses_by_category, incomes_by_category = await get_all_time_statistics()
        else:
            await update.message.reply_text(
                "❌ Невірний вибір періоду. Спробуйте ще раз.",
                reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
            )
            return CHOOSING_ACTION
        
        # Форматуємо повідомлення
        message = f"📊 Статистика {period_name}:\n\n"
        message += f"💰 Загальний дохід: {float(incomes):,.2f} €\n"
        message += f"💸 Загальні витрати: {float(expenses):,.2f} €\n"
        message += f"📈 Баланс: {float(incomes - expenses):,.2f} €\n"
        
        # Додаємо статистику по категоріях
        if expenses_by_category:
            message += "\n💸 Витрати по категоріях:\n"
            for cat in expenses_by_category:
                name = cat['category__name'] or 'Без категорії'
                total = float(cat['total'])
                percent = (total / float(expenses) * 100) if expenses and expenses != 0 else 0
                message += f"- {name}: {total:,.2f} € ({percent:.1f}%)\n"
        
        if incomes_by_category:
            message += "\n💰 Доходи по категоріях:\n"
            for cat in incomes_by_category:
                name = cat['category__name'] or 'Без категорії'
                total = float(cat['total'])
                percent = (total / float(incomes) * 100) if incomes and incomes != 0 else 0
                message += f"- {name}: {total:,.2f} € ({percent:.1f}%)\n"
        
        await update.message.reply_text(
            message,
            reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
        )
        
    except Exception as e:
        print(f"Error in show_period_statistics: {e}")
        await update.message.reply_text(
            "❌ Помилка при отриманні статистики.\n"
            f"Деталі помилки: {str(e)}",
            reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
        )
    
    return CHOOSING_ACTION

@sync_to_async
def clear_all_transactions():
    """Clear all transactions and reset account balances."""
    try:
        # Використовуємо транзакцію бази даних
        with transaction.atomic():
            # Видаляємо всі транзакції
            Transaction.objects.all().delete()
            
            # Скидаємо баланси рахунків
            Account.objects.all().update(balance=Decimal('0'))
            
        return True
    except Exception as e:
        print(f"Error clearing transactions: {e}")
        return False

async def start_clear_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the clear transactions process."""
    keyboard = [
        ['✅ Так, видалити все', '❌ Ні, скасувати'],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "⚠️ Ви впевнені, що хочете видалити ВСІ транзакції?\n"
        "Це також скине баланси всіх рахунків до нуля!\n"
        "Цю дію неможливо скасувати!",
        reply_markup=reply_markup
    )
    
    return CONFIRM_CLEAR

async def confirm_clear_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle clear transactions confirmation."""
    if update.message.text == '✅ Так, видалити все':
        # Спробуємо видалити транзакції
        if await clear_all_transactions():
            await update.message.reply_text(
                "✅ Всі транзакції видалено.\n"
                "Баланси рахунків скинуто до нуля.",
                reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
            )
        else:
            await update.message.reply_text(
                "❌ Помилка при видаленні транзакцій.\n"
                "Спробуйте ще раз або зверніться до адміністратора.",
                reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
            )
    else:
        await update.message.reply_text(
            "Операцію скасовано.",
            reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
        )
    
    return CHOOSING_ACTION

async def start_csv_import(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start CSV import process."""
    await update.message.reply_text(
        "📤 Будь ласка, надішліть файл виписки з банку у форматі CSV.\n\n"
        "❗️ Важливо: файл має бути у форматі DKB банку.",
        reply_markup=ReplyKeyboardMarkup([['↩️ Скасувати']], resize_keyboard=True)
    )
    return UPLOADING_CSV

async def handle_csv_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle CSV file upload."""
    # Перевіряємо чи є файл
    if not update.message.document:
        await update.message.reply_text(
            "❌ Будь ласка, надішліть файл у форматі CSV.",
            reply_markup=ReplyKeyboardMarkup([['↩️ Скасувати']], resize_keyboard=True)
        )
        return UPLOADING_CSV
    
    # Перевіряємо розширення файлу
    if not update.message.document.file_name.lower().endswith('.csv'):
        await update.message.reply_text(
            "❌ Файл має бути у форматі CSV.",
            reply_markup=ReplyKeyboardMarkup([['↩️ Скасувати']], resize_keyboard=True)
        )
        return UPLOADING_CSV
    
    try:
        # Перевіряємо чи є рахунок "Основний"
        account = await get_account_by_name("Основний")
        if not account:
            await update.message.reply_text(
                "❌ Спочатку створіть рахунок з назвою 'Основний' в євро! 🏦",
                reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
            )
            return CHOOSING_ACTION
        
        # Завантажуємо файл
        file = await context.bot.get_file(update.message.document.file_id)
        
        # Створюємо тимчасовий файл
        temp_path = f"/tmp/{update.message.document.file_name}"
        await file.download_to_drive(temp_path)
        
        # Імпортуємо дані
        imported, skipped = await import_dkb_csv(temp_path, account)
        
        # Видаляємо тимчасовий файл
        os.remove(temp_path)
        
        message = f"✅ Імпорт завершено!\n\n"
        message += f"📥 Імпортовано транзакцій: {imported}\n"
        message += f"⏭️ Пропущено дублікатів: {skipped}\n\n"
        message += f"💡 Всі транзакції додано до рахунку 'Основний' з категорією 'DKB Import'"
        
        await update.message.reply_text(
            message,
            reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
        )
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ Помилка при імпорті: {str(e)}",
            reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
        )
    
    return CHOOSING_ACTION

@sync_to_async
def import_dkb_csv(file_path, account):
    """Import transactions from DKB CSV file."""
    imported_count = 0
    skipped_count = 0
    
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as csvfile:
            content = csvfile.readlines()
            
            # Знаходимо рядок з заголовками
            header_index = 0
            for i, line in enumerate(content):
                if 'Buchungsdatum' in line:
                    header_index = i
                    break
            
            # Створюємо CSV reader з правильного місця
            reader = csv.DictReader(content[header_index:], delimiter=';')
            
            # Сортуємо транзакції за датою (спочатку доходи)
            transactions = []
            for row in reader:
                try:
                    date_str = row['Buchungsdatum'].strip()
                    if not date_str:
                        continue
                    
                    # Створюємо aware datetime об'єкт
                    naive_date = datetime.strptime(date_str, '%d.%m.%y')
                    aware_date = timezone.make_aware(naive_date, timezone.get_current_timezone())
                    
                    # Визначаємо тип транзакції і суму
                    is_income = row['Umsatztyp'].strip() == 'Eingang'
                    amount_str = row['Betrag (€)'].replace('.', '').replace(',', '.').strip()
                    if not amount_str:
                        continue
                    
                    amount = abs(Decimal(amount_str))
                    
                    # Формуємо опис транзакції
                    payer = row.get('Zahlungspflichtige*r', '').strip()
                    receiver = row.get('Zahlungsempfänger*in', '').strip()
                    purpose = row.get('Verwendungszweck', '').strip()
                    comment = f"{payer or receiver}: {purpose}"
                    
                    transactions.append({
                        'date': aware_date,
                        'is_income': is_income,
                        'amount': amount,
                        'comment': comment
                    })
                except Exception as e:
                    print(f"Error parsing row: {e}")
                    skipped_count += 1
            
            # Сортуємо транзакції: спочатку доходи, потім за датою
            transactions.sort(key=lambda x: (not x['is_income'], x['date']))
            
            # Використовуємо транзакцію бази даних
            with transaction.atomic():
                # Отримуємо або створюємо категорію
                category = Category.objects.get_or_create(name='DKB Import')[0]
                
                # Імпортуємо транзакції
                for t in transactions:
                    try:
                        # Перевіряємо чи транзакція вже існує
                        existing = Transaction.objects.filter(
                            date=t['date'],
                            amount=t['amount'],
                            account=account,
                            transaction_type='INCOME' if t['is_income'] else 'EXPENSE',
                            comment=t['comment']
                        ).exists()
                        
                        if not existing:
                            # Створюємо транзакцію
                            Transaction.objects.create(
                                date=t['date'],
                                amount=t['amount'],
                                account=account,
                                category=category,
                                transaction_type='INCOME' if t['is_income'] else 'EXPENSE',
                                currency='EUR',
                                comment=t['comment']
                            )
                            
                            # Оновлюємо баланс рахунку
                            if t['is_income']:
                                account.balance += t['amount']
                            else:
                                account.balance -= t['amount']
                            
                            imported_count += 1
                        else:
                            skipped_count += 1
                            
                    except Exception as e:
                        print(f"Error importing transaction: {e}")
                        skipped_count += 1
                
                # Зберігаємо оновлений баланс рахунку
                account.save()
                
        return imported_count, skipped_count
        
    except Exception as e:
        print(f"Error processing CSV file: {e}")
        return 0, 0

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the current operation and return to main menu."""
    context.user_data.clear()
    reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
    await update.message.reply_text(
        random.choice(CANCEL_PHRASES),
        reply_markup=reply_markup,
    )
    return CHOOSING_ACTION

def run_bot():
    """Start the bot."""
    print("Starting Telegram bot...")
    
    # Create the Application
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_ACTION: [
                MessageHandler(filters.Regex("^💰 Додати транзакцію$"), add_transaction_start),
                MessageHandler(filters.Regex("^🏦 Додати рахунок$"), add_account_start),
                MessageHandler(filters.Regex("^📊 Баланси рахунків$"), view_balances),
                MessageHandler(filters.Regex("^🏷️ Додати категорію$"), add_category_start),
                MessageHandler(filters.Regex("^📈 Статистика$"), show_statistics),
                MessageHandler(filters.Regex("^📥 Імпорт CSV$"), start_csv_import),
                MessageHandler(filters.Regex("^🗑️ Очистити транзакції$"), start_clear_transactions),
            ],
            ADDING_TRANSACTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_account_name),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_category_name),
            ],
            CHOOSING_TRANSACTION_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_account_type),
                MessageHandler(filters.TEXT & ~filters.COMMAND, choose_transaction_type),
            ],
            ENTERING_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_account_currency),
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_amount),
            ],
            CHOOSING_ACCOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, choose_account),
            ],
            CHOOSING_CATEGORY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, choose_category),
            ],
            CHOOSING_STATS_PERIOD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, show_period_statistics),
            ],
            UPLOADING_CSV: [
                MessageHandler(filters.Document.ALL, handle_csv_upload),
            ],
            CONFIRM_CLEAR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_clear_transactions),
            ],
            CONFIRMING_CLEAR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_clear_transactions),
            ],
        },
        fallbacks=[MessageHandler(filters.Regex("^↩️ Скасувати$|^↩️ Назад до меню$"), cancel)],
    )

    application.add_handler(conv_handler)

    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)
