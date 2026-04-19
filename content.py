import random
from typing import Tuple

from storage import ReminderType


class Localization:
    TEXTS = {
        "en": {
            "welcome": (
                "👋 *Welcome to Health Reminder Bot!*\n\n"
                "I help you stay healthy with reminders for stretching, water, walks, and screen breaks.\n\n"
                "Use /settings to customize everything."
            ),
            "help": (
                "*Available commands*\n"
                "/start — activate the bot\n"
                "/settings — open settings\n"
                "/status — show current settings\n"
                "/pause — pause reminders\n"
                "/resume — resume reminders\n"
                "/snooze 10 — snooze for N minutes\n"
                "/test — send a test reminder\n"
                "/stop — deactivate the bot"
            ),
            "settings_menu": "⚙️ *Settings*\nChoose what you want to change:",
            "status_title": "📊 *Current status*",
            "language": "Language",
            "mode": "Mode",
            "frequency": "Frequency",
            "inactivity": "Inactivity threshold",
            "active_hours": "Active hours",
            "reminder_types": "Reminder types",
            "timezone": "Timezone",
            "active": "Active",
            "yes": "Yes",
            "no": "No",
            "time_based": "⏰ Time-based",
            "inactivity_based": "💤 Inactivity-based",
            "settings_saved": "✅ Settings saved.",
            "choose_language": "🌍 Choose a language:",
            "choose_mode": "Choose reminder mode:",
            "choose_types": "Select reminder types. Tap again to toggle.",
            "ask_frequency": "Send the new reminder frequency in minutes. Example: `45`",
            "ask_inactivity": "Send the inactivity threshold in minutes. Example: `30`",
            "ask_active_hours": "Send active hours in 24h format like `9-18` or `09-18`.",
            "ask_timezone": "Send your UTC offset as a number from -12 to +14. Example: `3` or `-5`",
            "invalid_frequency": "❌ Please enter a whole number between 5 and 480.",
            "invalid_inactivity": "❌ Please enter a whole number between 5 and 480.",
            "invalid_hours": "❌ Invalid format. Use `9-18` and make sure start < end.",
            "invalid_timezone": "❌ Enter an integer from -12 to 14.",
            "bot_activated": "🟢 Bot activated. Reminders are now enabled.",
            "bot_deactivated": "🔴 Bot deactivated. No more reminders will be sent.",
            "bot_paused": "⏸️ Reminders paused.",
            "bot_resumed": "▶️ Reminders resumed.",
            "snoozed": "😴 Snoozed for {minutes} minutes.",
            "stretch_reminder": "🧘 Time to stretch!",
            "water_reminder": "💧 Time to drink water!",
            "walk_reminder": "🚶 Time for a short walk!",
            "break_reminder": "☕ Time for a screen break!",
            "done": "✅ Done",
            "remind_later": "⏰ 10 min",
            "skip": "⏭️ Skip",
            "good_job": "Great job. Keep going! 💪",
            "remind_in_10": "Okay — I'll remind you again in 10 minutes.",
            "skipped": "Skipped. The next reminder will follow your schedule.",
            "back": "⬅️ Back",
            "close": "✖️ Close",
            "test_sent": "🧪 Test reminder sent.",
            "menu_hint": "Tip: you can also use /status, /pause, /resume, /snooze 15, and /test.",
        },
        "ru": {
            "welcome": (
                "👋 *Добро пожаловать в Health Reminder Bot!*\n\n"
                "Я помогаю поддерживать здоровье напоминаниями о растяжке, воде, прогулках и перерывах.\n\n"
                "Используйте /settings, чтобы всё настроить."
            ),
            "help": (
                "*Доступные команды*\n"
                "/start — включить бота\n"
                "/settings — открыть настройки\n"
                "/status — показать текущие настройки\n"
                "/pause — поставить напоминания на паузу\n"
                "/resume — возобновить напоминания\n"
                "/snooze 10 — отложить на N минут\n"
                "/test — отправить тестовое напоминание\n"
                "/stop — отключить бота"
            ),
            "settings_menu": "⚙️ *Настройки*\nВыберите, что изменить:",
            "status_title": "📊 *Текущий статус*",
            "language": "Язык",
            "mode": "Режим",
            "frequency": "Частота",
            "inactivity": "Порог бездействия",
            "active_hours": "Активные часы",
            "reminder_types": "Типы напоминаний",
            "timezone": "Часовой пояс",
            "active": "Активен",
            "yes": "Да",
            "no": "Нет",
            "time_based": "⏰ По времени",
            "inactivity_based": "💤 По бездействию",
            "settings_saved": "✅ Настройки сохранены.",
            "choose_language": "🌍 Выберите язык:",
            "choose_mode": "Выберите режим напоминаний:",
            "choose_types": "Выберите типы напоминаний. Нажмите ещё раз, чтобы переключить.",
            "ask_frequency": "Отправьте новую частоту напоминаний в минутах. Пример: `45`",
            "ask_inactivity": "Отправьте порог бездействия в минутах. Пример: `30`",
            "ask_active_hours": "Отправьте активные часы в формате 24ч, например `9-18` или `09-18`.",
            "ask_timezone": "Отправьте ваш сдвиг UTC числом от -12 до +14. Пример: `3` или `-5`",
            "invalid_frequency": "❌ Введите целое число от 5 до 480.",
            "invalid_inactivity": "❌ Введите целое число от 5 до 480.",
            "invalid_hours": "❌ Неверный формат. Используйте `9-18`, при этом начало должно быть меньше конца.",
            "invalid_timezone": "❌ Введите целое число от -12 до 14.",
            "bot_activated": "🟢 Бот активирован. Напоминания включены.",
            "bot_deactivated": "🔴 Бот деактивирован. Напоминания больше не будут отправляться.",
            "bot_paused": "⏸️ Напоминания поставлены на паузу.",
            "bot_resumed": "▶️ Напоминания возобновлены.",
            "snoozed": "😴 Отложено на {minutes} минут.",
            "stretch_reminder": "🧘 Время размяться!",
            "water_reminder": "💧 Время попить воды!",
            "walk_reminder": "🚶 Время немного пройтись!",
            "break_reminder": "☕ Время сделать перерыв от экрана!",
            "done": "✅ Готово",
            "remind_later": "⏰ 10 мин",
            "skip": "⏭️ Пропустить",
            "good_job": "Отлично. Так держать! 💪",
            "remind_in_10": "Хорошо — напомню снова через 10 минут.",
            "skipped": "Пропущено. Следующее напоминание будет по вашему расписанию.",
            "back": "⬅️ Назад",
            "close": "✖️ Закрыть",
            "test_sent": "🧪 Тестовое напоминание отправлено.",
            "menu_hint": "Подсказка: также можно использовать /status, /pause, /resume, /snooze 15 и /test.",
        },
    }

    @classmethod
    def t(cls, key: str, language: str = "en", **kwargs) -> str:
        text = cls.TEXTS.get(language, cls.TEXTS["en"]).get(key, key)
        return text.format(**kwargs)


class ReminderContent:
    QUOTES = {
        "en": [
            "Small healthy actions repeated daily create big results.",
            "Movement is medicine.",
            "Take care of your body — it carries you through life.",
            "Progress beats perfection.",
            "A short break now can save your energy later.",
        ],
        "ru": [
            "Небольшие полезные действия каждый день дают большой результат.",
            "Движение — это лекарство.",
            "Заботьтесь о своём теле — оно несёт вас через всю жизнь.",
            "Прогресс важнее совершенства.",
            "Короткий перерыв сейчас сохранит силы потом.",
        ],
    }

    ACTIVITIES = {
        "en": {
            ReminderType.STRETCH: [
                "Do 10 shoulder rolls.",
                "Stand up and reach toward the ceiling for 30 seconds.",
                "Stretch your wrists and fingers.",
                "Do 8 gentle neck turns.",
                "Do 10 side bends.",
            ],
            ReminderType.WATER: [
                "Drink one full glass of water.",
                "Take several good sips of water.",
                "Refill your water bottle.",
            ],
            ReminderType.WALK: [
                "Take a 3-minute walk.",
                "Walk around the room for 2 minutes.",
                "Go outside for a quick lap if you can.",
            ],
            ReminderType.BREAK: [
                "Look away from the screen for 20 seconds.",
                "Close your eyes and breathe deeply 5 times.",
                "Relax your jaw and shoulders for 1 minute.",
            ],
        },
        "ru": {
            ReminderType.STRETCH: [
                "Сделайте 10 вращений плечами.",
                "Встаньте и потянитесь вверх 30 секунд.",
                "Разомните запястья и пальцы.",
                "Сделайте 8 мягких поворотов шеи.",
                "Сделайте 10 наклонов в стороны.",
            ],
            ReminderType.WATER: [
                "Выпейте один полный стакан воды.",
                "Сделайте несколько хороших глотков воды.",
                "Наполните бутылку водой.",
            ],
            ReminderType.WALK: [
                "Пройдитесь 3 минуты.",
                "Походите по комнате 2 минуты.",
                "Если можете, выйдите на короткую прогулку.",
            ],
            ReminderType.BREAK: [
                "Отведите взгляд от экрана на 20 секунд.",
                "Закройте глаза и глубоко вдохните 5 раз.",
                "Расслабьте челюсть и плечи на 1 минуту.",
            ],
        },
    }

    @classmethod
    def pick(cls, selected_type: ReminderType, language: str) -> Tuple[str, str, ReminderType]:
        lang = language if language in cls.QUOTES else "en"
        actual_type = selected_type
        if selected_type == ReminderType.ALL:
            actual_type = random.choice(
                [ReminderType.STRETCH, ReminderType.WATER, ReminderType.WALK, ReminderType.BREAK]
            )
        activity = random.choice(cls.ACTIVITIES[lang][actual_type])
        quote = random.choice(cls.QUOTES[lang])
        return activity, quote, actual_type
