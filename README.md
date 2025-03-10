# Фінансовий менеджер з Telegram ботом

## Вимоги
- Python 3.8 або новіше
- pip (менеджер пакетів Python)
- SQLite3
- Токен Telegram бота (отримати можна у [@BotFather](https://t.me/BotFather))

## Налаштування проекту

1. Клонуйте репозиторій:
```bash
git clone https://github.com/irynazaiets/beetroot3_django_with_bootstrap_and_forms.git
cd beetroot3_django
```

2. Створіть віртуальне середовище та активуйте його:
```bash
python3 -m venv venv
source venv/bin/activate  # для Linux/Mac
# або
.\venv\Scripts\activate  # для Windows
```

3. Встановіть залежності:
```bash
pip install -r requirements.txt
```

4. Створіть файл `.env` в корені проекту:
```bash
touch .env
```

5. Додайте в `.env` наступні змінні:
```
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
```

6. Застосуйте міграції бази даних:
```bash
python3 manage.py migrate
```

7. Створіть суперкористувача Django:
```bash
python3 manage.py createsuperuser
```

## Запуск додатку

### Запуск веб-інтерфейсу (Django)
1. Активуйте віртуальне середовище (якщо ще не активоване):
```bash
source venv/bin/activate  # для Linux/Mac
# або
.\venv\Scripts\activate  # для Windows
```

2. Запустіть Django сервер:
```bash
python3 manage.py runserver
```

3. Відкрийте браузер і перейдіть за адресою:
- Головна сторінка: http://127.0.0.1:8000/
- Адмін-панель: http://127.0.0.1:8000/admin/

### Запуск Telegram бота
1. Активуйте віртуальне середовище (якщо ще не активоване):
```bash
source venv/bin/activate  # для Linux/Mac
# або
.\venv\Scripts\activate  # для Windows
```

2. Запустіть бота:
```bash
python3 manage.py runbot
```

## Основні функції Telegram бота

1. 💰 Додати транзакцію
   - Створення нових доходів та витрат
   - Вибір категорії та рахунку
   - Додавання коментарів

2. 📊 Статистика
   - Перегляд статистики за тиждень/місяць/рік/весь час
   - Аналіз витрат та доходів по категоріях
   - Відображення балансу

3. 📥 Імпорт CSV
   - Імпорт банківських виписок у форматі DKB CSV
   - Автоматичне створення транзакцій
   - Сортування за типом (доходи/витрати)

4. 🗑️ Очистити транзакції
   - Видалення всіх транзакцій
   - Скидання балансів рахунків

## Додаткова інформація

- Всі дані зберігаються в локальній базі даних SQLite
- Для керування категоріями та рахунками використовуйте адмін-панель Django
- Бот підтримує роботу з євро (€) як основною валютою
