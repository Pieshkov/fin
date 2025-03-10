import logging
import os
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

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Log the token (temporary for debugging)
logger.info(f"Bot token from settings: {settings.TELEGRAM_BOT_TOKEN}")

# Conversation states
(
    CHOOSING_ACTION,
    ADDING_ACCOUNT,
    ADDING_CATEGORY,
    ADDING_TRANSACTION,
    CHOOSING_TRANSACTION_TYPE,
    ENTERING_AMOUNT,
    CHOOSING_ACCOUNT,
    CHOOSING_CATEGORY,
    ENTERING_COMMENT,
) = range(9)

# Keyboard layouts
main_keyboard = [
    [' Add Transaction', ' Add Account'],
    [' View Balances', ' Add Category'],
]

transaction_types = [
    [' Income', ' Expense'],
    [' Back to Main Menu'],
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and show main menu."""
    reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Welcome to Finance Manager Bot! What would you like to do?",
        reply_markup=reply_markup,
    )
    return CHOOSING_ACTION

async def view_balances(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show all accounts and their balances."""
    accounts = Account.objects.all()
    if not accounts:
        await update.message.reply_text("No accounts found. Please add an account first.")
        return CHOOSING_ACTION

    message = " Current Account Balances:\n\n"
    for account in accounts:
        message += f"{account.name}: {account.balance} {account.currency}\n"

    await update.message.reply_text(message)
    return CHOOSING_ACTION

async def add_account_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the account creation process."""
    await update.message.reply_text(
        "Please enter the account name:"
    )
    return ADDING_ACCOUNT

async def add_account_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the account name and ask for account type."""
    context.user_data['account_name'] = update.message.text
    keyboard = [[type[1]] for type in Account.ACCOUNT_TYPES]
    keyboard.append([' Cancel'])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "Please select the account type:",
        reply_markup=reply_markup,
    )
    return ADDING_ACCOUNT

async def add_category_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the category creation process."""
    await update.message.reply_text(
        "Please enter the category name:"
    )
    return ADDING_CATEGORY

async def add_category_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the category name and create the category."""
    category_name = update.message.text
    try:
        category = Category.objects.create(name=category_name)
        await update.message.reply_text(f"Category '{category.name}' has been created!")
    except Exception as e:
        await update.message.reply_text(f"Error creating category: {str(e)}")
    
    reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
    await update.message.reply_text("What would you like to do next?", reply_markup=reply_markup)
    return CHOOSING_ACTION

async def add_transaction_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the transaction creation process."""
    reply_markup = ReplyKeyboardMarkup(transaction_types, resize_keyboard=True)
    await update.message.reply_text(
        "What type of transaction would you like to add?",
        reply_markup=reply_markup,
    )
    return CHOOSING_TRANSACTION_TYPE

async def choose_transaction_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the transaction type and ask for amount."""
    text = update.message.text
    if text == ' Income':
        context.user_data['transaction_type'] = 'INCOME'
    elif text == ' Expense':
        context.user_data['transaction_type'] = 'EXPENSE'
    else:
        return CHOOSING_ACTION

    await update.message.reply_text("Please enter the amount:")
    return ENTERING_AMOUNT

async def enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the amount and ask for account selection."""
    try:
        amount = Decimal(update.message.text)
        context.user_data['amount'] = amount
        
        accounts = Account.objects.all()
        if not accounts:
            await update.message.reply_text("No accounts found. Please add an account first.")
            return CHOOSING_ACTION
        
        keyboard = [[account.name] for account in accounts]
        keyboard.append([' Cancel'])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "Please select an account:",
            reply_markup=reply_markup,
        )
        return CHOOSING_ACCOUNT
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return ENTERING_AMOUNT

async def choose_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the account selection and ask for category."""
    account_name = update.message.text
    try:
        account = Account.objects.get(name=account_name)
        context.user_data['account'] = account
        
        categories = Category.objects.all()
        if not categories:
            await update.message.reply_text("No categories found. Please add a category first.")
            return CHOOSING_ACTION
        
        keyboard = [[category.name] for category in categories]
        keyboard.append([' Cancel'])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "Please select a category:",
            reply_markup=reply_markup,
        )
        return CHOOSING_CATEGORY
    except Account.DoesNotExist:
        await update.message.reply_text("Account not found. Please try again.")
        return CHOOSING_ACCOUNT

async def choose_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the category selection and create the transaction."""
    category_name = update.message.text
    try:
        category = Category.objects.get(name=category_name)
        
        # Create the transaction
        transaction = Transaction.objects.create(
            transaction_type=context.user_data['transaction_type'],
            amount=context.user_data['amount'],
            account=context.user_data['account'],
            category=category,
            currency=context.user_data['account'].currency
        )
        
        # Clear user data
        context.user_data.clear()
        
        await update.message.reply_text(f"Transaction recorded successfully!")
        
        # Show main menu
        reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "What would you like to do next?",
            reply_markup=reply_markup,
        )
        return CHOOSING_ACTION
    except Category.DoesNotExist:
        await update.message.reply_text("Category not found. Please try again.")
        return CHOOSING_CATEGORY
    except Exception as e:
        await update.message.reply_text(f"Error creating transaction: {str(e)}")
        return CHOOSING_ACTION

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the current operation and return to main menu."""
    context.user_data.clear()
    reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Operation cancelled. What would you like to do?",
        reply_markup=reply_markup,
    )
    return CHOOSING_ACTION

def run_bot():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_ACTION: [
                MessageHandler(filters.Regex("^ Add Transaction$"), add_transaction_start),
                MessageHandler(filters.Regex("^ Add Account$"), add_account_start),
                MessageHandler(filters.Regex("^ View Balances$"), view_balances),
                MessageHandler(filters.Regex("^ Add Category$"), add_category_start),
            ],
            ADDING_ACCOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_account_name),
            ],
            ADDING_CATEGORY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_category_name),
            ],
            CHOOSING_TRANSACTION_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, choose_transaction_type),
            ],
            ENTERING_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_amount),
            ],
            CHOOSING_ACCOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, choose_account),
            ],
            CHOOSING_CATEGORY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, choose_category),
            ],
        },
        fallbacks=[MessageHandler(filters.Regex("^ Cancel$|^ Back to Main Menu$"), cancel)],
    )

    application.add_handler(conv_handler)

    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)
