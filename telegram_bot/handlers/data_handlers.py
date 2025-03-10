from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from decimal import Decimal
import csv
import os
from django.db import transaction
from fin.models import Transaction, Account, Category
from ..utils.keyboards import get_keyboard
from ..utils.constants import STATES
from ..utils.messages import random_message
from .account_handlers import get_all_accounts

@sync_to_async
def clear_all_transactions():
    """Clear all transactions and reset account balances."""
    try:
        with transaction.atomic():
            # Очищаємо всі транзакції
            Transaction.objects.all().delete()
            
            # Скидаємо баланси рахунків
            for account in Account.objects.all():
                account.balance = 0
                account.save()
            
            return True
    except Exception as e:
        print(f"Error clearing transactions: {e}")
        return False

async def start_clear_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the clear transactions process."""
    keyboard = [
        ['✅ Так, очистити все', '❌ Ні, скасувати'],
        ['↩️ Назад до меню']
    ]
    
    await update.message.reply_text(
        "⚠️ Ви впевнені, що хочете видалити ВСІ транзакції?\n"
        "Це скине баланси всіх рахунків до 0!",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return STATES.CONFIRMING_CLEAR

async def confirm_clear_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle clear transactions confirmation."""
    if update.message.text == '✅ Так, очистити все':
        success = await clear_all_transactions()
        
        if success:
            await update.message.reply_text(
                "✅ Всі транзакції видалено!\n"
                "Баланси рахунків скинуто до 0.",
                reply_markup=get_keyboard('main')
            )
        else:
            await update.message.reply_text(
                "❌ Помилка при очищенні транзакцій.\n"
                "Спробуйте ще раз або зверніться до адміністратора.",
                reply_markup=get_keyboard('main')
            )
    else:
        await update.message.reply_text(
            random_message('CANCEL'),
            reply_markup=get_keyboard('main')
        )
    
    return STATES.CHOOSING_ACTION

async def start_csv_import(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start CSV import process."""
    await update.message.reply_text(
        "📥 Надішліть файл виписки з банку у форматі CSV:",
        reply_markup=get_keyboard('back')
    )
    return STATES.UPLOADING_CSV

async def handle_csv_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle CSV file upload."""
    try:
        # Перевіряємо чи є документ
        if not update.message.document:
            await update.message.reply_text(
                "❌ Будь ласка, надішліть файл CSV.",
                reply_markup=get_keyboard('main')
            )
            return STATES.CHOOSING_ACTION

        # Перевіряємо розширення файлу
        file_name = update.message.document.file_name
        if not file_name.lower().endswith('.csv'):
            await update.message.reply_text(
                "❌ Файл повинен мати розширення .csv",
                reply_markup=get_keyboard('main')
            )
            return STATES.CHOOSING_ACTION

        # Перевіряємо розмір файлу (максимум 10MB)
        if update.message.document.file_size > 10 * 1024 * 1024:
            await update.message.reply_text(
                "❌ Файл занадто великий. Максимальний розмір - 10MB.",
                reply_markup=get_keyboard('main')
            )
            return STATES.CHOOSING_ACTION

        # Отримуємо файл
        file = await update.message.document.get_file()
        file_path = os.path.join(os.getcwd(), f"temp_{file_name}")
        
        # Завантажуємо файл
        await update.message.reply_text(
            "⏳ Завантажую файл..."
        )
        await file.download_to_drive(file_path)

        # Перевіряємо чи можемо відкрити файл як CSV
        try:
            # Спробуємо різні кодування
            encodings = ['utf-8-sig', 'utf-8', 'cp1251', 'latin1']
            csv_content = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as test_file:
                        content = test_file.read()
                        if content.strip():  # Перевіряємо чи файл не порожній
                            csv_content = content
                            break
                except UnicodeDecodeError:
                    continue
            
            if csv_content is None:
                raise ValueError('Не вдалося прочитати файл в жодному з підтримуваних кодувань')
            
            # Перевіряємо чи це дійсно CSV файл
            import io
            csv_file = io.StringIO(csv_content)
            csv_reader = csv.reader(csv_file, delimiter=';')
            # Пробуємо прочитати перший рядок
            first_row = next(csv_reader)
            
            # Перевіряємо чи це файл DKB банку
            if not (len(first_row) >= 2 and 'Girokonto' in first_row[0]):
                raise ValueError('Це не схоже на виписку з DKB банку')
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            await update.message.reply_text(
                f"❌ Не вдалося прочитати CSV файл: {str(e)}\n"
                "Переконайтеся, що файл має правильний формат.",
                reply_markup=get_keyboard('main')
            )
            return STATES.CHOOSING_ACTION

        # Зберігаємо шлях до файлу
        context.user_data['csv_file_path'] = file_path
        
        # Показуємо список рахунків
        accounts = await get_all_accounts()
        if not accounts:
            if os.path.exists(file_path):
                os.remove(file_path)
            await update.message.reply_text(
                "❌ У вас ще немає жодного рахунку. Спочатку створіть рахунок!",
                reply_markup=get_keyboard('main')
            )
            return STATES.CHOOSING_ACTION
        
        keyboard = [[account.name] for account in accounts]
        keyboard.append(['↩️ Назад до меню'])
        
        await update.message.reply_text(
            "✅ Файл успішно завантажено!\n"
            "Виберіть рахунок для імпорту транзакцій:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return STATES.CHOOSING_CSV_ACCOUNT
        
    except Exception as e:
        print(f"Error handling CSV upload: {e}")
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        await update.message.reply_text(
            f"❌ Помилка при завантаженні файлу: {str(e)}\n"
            "Спробуйте ще раз.",
            reply_markup=get_keyboard('main')
        )
        return STATES.CHOOSING_ACTION

async def choose_csv_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle account selection for CSV import."""
    account_name = update.message.text
    file_path = context.user_data.get('csv_file_path')
    
    try:
        # Отримуємо рахунок за іменем
        from .account_handlers import get_account_by_name
        account = await get_account_by_name(account_name)
        
        # Імпортуємо транзакції
        await update.message.reply_text(
            "⏳ Імпортую транзакції..."
        )
        
        imported_count = await import_dkb_csv(file_path, account)
        
        # Видаляємо тимчасовий файл
        if os.path.exists(file_path):
            os.remove(file_path)
        
        await update.message.reply_text(
            f"✅ Імпорт завершено! Імпортовано {imported_count} транзакцій.",
            reply_markup=get_keyboard('main')
        )
        return STATES.CHOOSING_ACTION
        
    except Account.DoesNotExist:
        if os.path.exists(file_path):
            os.remove(file_path)
        await update.message.reply_text(
            "❌ Рахунок не знайдено. Спробуйте ще раз.",
            reply_markup=get_keyboard('main')
        )
        return STATES.CHOOSING_ACTION
    except Exception as e:
        print(f"Error importing CSV: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
        await update.message.reply_text(
            f"❌ Помилка при імпорті: {str(e)}\n"
            "Спробуйте ще раз.",
            reply_markup=get_keyboard('main')
        )
        return STATES.CHOOSING_ACTION

@sync_to_async
def import_dkb_csv(file_path, account):
    """Import transactions from DKB CSV file."""
    try:
        from ..utils.transaction_categories import get_category_by_description
        imported_count = 0
        errors_count = 0
        
        # Спробуємо різні кодування
        encodings = ['utf-8-sig', 'utf-8', 'cp1251', 'latin1']
        csv_content = None
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as test_file:
                    content = test_file.read()
                    if content.strip():  # Перевіряємо чи файл не порожній
                        csv_content = content
                        break
            except UnicodeDecodeError:
                continue
        
        if csv_content is None:
            raise ValueError('Не вдалося прочитати файл в жодному з підтримуваних кодувань')
        
        # Переводимо вміст в StringIO для роботи з CSV
        import io
        csv_file = io.StringIO(csv_content)
        reader = csv.reader(csv_file, delimiter=';')
        
        # Пропускаємо заголовки
        next(reader)  # Girokonto
        next(reader)  # Порожній рядок
        next(reader)  # Kontostand
        next(reader)  # Порожній рядок
        next(reader)  # Заголовки колонок
            
        # Читаємо транзакції
        transactions_to_create = []
        
        # Спочатку збираємо всі транзакції
        for row in reader:
            try:
                from datetime import datetime
                # Перетворюємо дату з формату DD.MM.YY в повний формат
                date = datetime.strptime(row[0], '%d.%m.%y')
                payer = row[3]  # Платник
                recipient = row[4]  # Отримувач
                purpose = row[5]  # Призначення платежу
                amount_str = row[8].replace('.', '').replace(',', '.')
                amount = Decimal(amount_str)
                
                # Визначаємо тип транзакції
                transaction_type = 'INCOME' if amount > 0 else 'EXPENSE'
                amount = abs(amount)
                
                # Формуємо повний опис для визначення категорії
                full_description = f"{recipient} {purpose}"
                
                # Визначаємо категорію
                category_name = get_category_by_description(
                    full_description,
                    transaction_type
                )
                
                # Знаходимо або створюємо категорію
                category, _ = Category.objects.get_or_create(name=category_name)
                
                # Формуємо детальний опис транзакції
                description = f"📝 {purpose}\n"
                if transaction_type == 'INCOME':
                    description += f"От: {payer}\n"
                else:
                    description += f"Кому: {recipient}\n"
                
                transactions_to_create.append({
                    'transaction_type': transaction_type,
                    'amount': amount,
                    'account': account,
                    'category': category,
                    'description': description.strip(),
                    'date': date
                })
                
            except Exception as e:
                print(f"Error parsing row: {e}")
                errors_count += 1
                continue
        
        # Сортуємо транзакції: спочатку доходи, потім витрати
        transactions_to_create.sort(
            key=lambda x: 0 if x['transaction_type'] == 'INCOME' else 1
        )
        
        # Створюємо транзакції в одній транзакції бази даних
        with transaction.atomic():
            for trans_data in transactions_to_create:
                try:
                    # Перевіряємо баланс для витрат
                    if (trans_data['transaction_type'] == 'EXPENSE' and 
                        account.balance < trans_data['amount']):
                        raise ValueError(
                            f"Недостатньо коштів для витрати {trans_data['amount']}"
                        )
                    
                    # Створюємо транзакцію
                    Transaction.objects.create(
                        transaction_type=trans_data['transaction_type'],
                        amount=trans_data['amount'],
                        account=trans_data['account'],
                        category=trans_data['category'],
                        comment=trans_data['description'],
                        currency=account.currency,
                        date=trans_data['date']
                    )
                    
                    # Оновлюємо баланс
                    if trans_data['transaction_type'] == 'INCOME':
                        account.balance += trans_data['amount']
                    else:
                        account.balance -= trans_data['amount']
                    account.save()
                    
                    imported_count += 1
                    
                except Exception as e:
                    print(f"Error creating transaction: {e}")
                    errors_count += 1
                    continue
        
        # Видаляємо тимчасовий файл
        if os.path.exists(file_path):
            os.remove(file_path)
        
        return imported_count, errors_count
        
    except Exception as e:
        print(f"Error importing CSV: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
        raise e
    finally:
        # Видаляємо тимчасовий файл
        if os.path.exists(file_path):
            os.remove(file_path)
