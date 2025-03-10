import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)
from django.conf import settings

import os
import sys
import django

# Налаштовуємо Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from telegram_bot.handlers.account_handlers import (
    view_balances,
    add_account_start,
    add_account_name,
    add_account_type,
    add_account_currency,
)
from telegram_bot.handlers.category_handlers import (
    add_category_start,
    add_category_name,
)
from telegram_bot.handlers.transaction_handlers import (
    add_transaction_start,
    choose_transaction_type,
    enter_amount,
    choose_account,
    choose_category,
)
from telegram_bot.handlers.statistics_handlers import (
    show_statistics,
    show_period_statistics,
)
from telegram_bot.handlers.data_handlers import (
    start_clear_transactions,
    confirm_clear_transactions,
    start_csv_import,
    handle_csv_upload,
    choose_csv_account,
)
from telegram_bot.utils.constants import STATES
from telegram_bot.utils.keyboards import get_keyboard
from telegram_bot.utils.messages import random_message

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update, context):
    """Start the conversation and show main menu."""
    await update.message.reply_text(
        random_message('GREETING'),
        reply_markup=get_keyboard('main')
    )
    return STATES.CHOOSING_ACTION

async def cancel(update, context):
    """Cancel and end the conversation."""
    await update.message.reply_text(
        random_message('CANCEL'),
        reply_markup=get_keyboard('main')
    )
    return STATES.CHOOSING_ACTION

def run_bot():
    """Start the bot."""
    print("Starting Telegram bot...")
    
    # Create the Application
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    
    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            STATES.CHOOSING_ACTION: [
                MessageHandler(filters.Regex("^💰 Додати транзакцію$"), add_transaction_start),
                MessageHandler(filters.Regex("^🏦 Додати рахунок$"), add_account_start),
                MessageHandler(filters.Regex("^📊 Баланси рахунків$"), view_balances),
                MessageHandler(filters.Regex("^📈 Статистика$"), show_statistics),
                MessageHandler(filters.Regex("^📥 Імпорт CSV$"), start_csv_import),
                MessageHandler(filters.Regex("^🏷️ Додати категорію$"), add_category_start),
                MessageHandler(filters.Regex("^🗑️ Очистити транзакції$"), start_clear_transactions),
            ],
            STATES.CHOOSING_TRANSACTION_TYPE: [
                MessageHandler(
                    filters.Regex("^(💵 Прибуток|💸 Витрата)$"),
                    choose_transaction_type
                ),
            ],
            STATES.ENTERING_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_amount),
            ],
            STATES.CHOOSING_ACCOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, choose_account),
            ],
            STATES.CHOOSING_CATEGORY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, choose_category),
            ],
            STATES.CHOOSING_STATS_PERIOD: [
                MessageHandler(
                    filters.Regex("^(📊 За тиждень|📈 За місяць|📉 За рік|📋 За весь час)$"),
                    show_period_statistics
                ),
            ],
            STATES.UPLOADING_CSV: [
                MessageHandler(filters.Document.ALL, handle_csv_upload),
            ],
            STATES.CHOOSING_CSV_ACCOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, choose_csv_account),
            ],
            STATES.CONFIRMING_CLEAR: [
                MessageHandler(
                    filters.Regex("^(✅ Так, очистити все|❌ Ні, скасувати)$"),
                    confirm_clear_transactions
                ),
            ],
            STATES.ADDING_ACCOUNT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_account_name),
            ],
            STATES.ADDING_ACCOUNT_TYPE: [
                MessageHandler(
                    filters.Regex("^(💳 Карта|💰 Готівка|💶 Депозит|💸 Інвестиції)$"),
                    add_account_type
                ),
            ],
            STATES.ADDING_ACCOUNT_CURRENCY: [
                MessageHandler(
                    filters.Regex("^(€ EUR|\\$ USD|₴ UAH|£ GBP)$"),
                    add_account_currency
                ),
            ],
            STATES.ADDING_CATEGORY_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_category_name),
            ],
        },
        fallbacks=[
            MessageHandler(filters.Regex("^↩️ Назад до меню$"), cancel),
            CommandHandler("cancel", cancel),
        ],
    )
    
    application.add_handler(conv_handler)
    
    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    run_bot()
