import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import random
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ReminderType(Enum):
    STRETCH = "stretch"
    WATER = "water"
    WALK = "walk"
    BREAK = "break"
    ALL = "all"

class ReminderMode(Enum):
    TIME_BASED = "time_based"
    INACTIVITY = "inactivity"

@dataclass
class UserSettings:
    user_id: int
    language: str = "en"
    mode: ReminderMode = ReminderMode.TIME_BASED
    frequency_minutes: int = 60
    active_hours: tuple = (9, 18)  # 9 AM to 6 PM
    reminder_types: List[ReminderType] = None
    is_active: bool = True
    timezone_offset: int = 0
    
    def __post_init__(self):
        if self.reminder_types is None:
            self.reminder_types = [ReminderType.ALL]

class Localization:
    """Handles multi-language support"""
    
    TEXTS = {
        "en": {
            "welcome": "👋 Welcome to Health Reminder Bot!\n\nI'll help you stay healthy by sending regular reminders to stretch, drink water, and take breaks.\n\nUse /settings to configure your preferences.",
            "settings_menu": "⚙️ Settings Menu",
            "mode_selection": "Choose reminder mode:",
            "time_based": "⏰ Time-based reminders",
            "inactivity_based": "💤 Inactivity-based reminders",
            "frequency_setting": "Set reminder frequency (minutes):",
            "active_hours": "Set active hours (format: 9-18):",
            "reminder_types": "Select reminder types:",
            "language_selection": "🌍 Select language:",
            "settings_saved": "✅ Settings saved successfully!",
            "stretch_reminder": "🧘‍♀️ Time to stretch!",
            "water_reminder": "💧 Don't forget to drink water!",
            "walk_reminder": "🚶‍♀️ Time for a short walk!",
            "break_reminder": "☕ Take a break from the screen!",
            "done": "✅ Done",
            "remind_later": "⏰ Remind later",
            "skip": "⏭️ Skip",
            "good_job": "Great job! Keep it up! 💪",
            "remind_in_10": "I'll remind you in 10 minutes.",
            "skipped": "Skipped. Next reminder as scheduled.",
            "bot_activated": "🟢 Bot activated! Reminders will start according to your schedule.",
            "bot_deactivated": "🔴 Bot deactivated. No more reminders will be sent.",
            "invalid_hours": "Invalid format. Please use format like: 9-18",
            "invalid_frequency": "Invalid frequency. Please enter a number between 5 and 480.",
        },
        "ru": {
            "welcome": "👋 Добро пожаловать в бот напоминаний о здоровье!\n\nЯ помогу вам оставаться здоровыми, отправляя регулярные напоминания о растяжке, питье воды и отдыхе.\n\nИспользуйте /settings для настройки предпочтений.",
            "settings_menu": "⚙️ Меню настроек",
            "mode_selection": "Выберите режим напоминаний:",
            "time_based": "⏰ Напоминания по времени",
            "inactivity_based": "💤 Напоминания при бездействии",
            "frequency_setting": "Установите частоту напоминаний (минуты):",
            "active_hours": "Установите активные часы (формат: 9-18):",
            "reminder_types": "Выберите типы напоминаний:",
            "language_selection": "🌍 Выберите язык:",
            "settings_saved": "✅ Настройки сохранены успешно!",
            "stretch_reminder": "🧘‍♀️ Время размяться!",
            "water_reminder": "💧 Не забудьте попить воды!",
            "walk_reminder": "🚶‍♀️ Время для короткой прогулки!",
            "break_reminder": "☕ Сделайте перерыв от экрана!",
            "done": "✅ Готово",
            "remind_later": "⏰ Напомнить позже",
            "skip": "⏭️ Пропустить",
            "good_job": "Отлично! Продолжайте в том же духе! 💪",
            "remind_in_10": "Напомню через 10 минут.",
            "skipped": "Пропущено. Следующее напоминание по расписанию.",
            "bot_activated": "🟢 Бот активирован! Напоминания начнутся согласно вашему расписанию.",
            "bot_deactivated": "🔴 Бот деактивирован. Больше напоминаний не будет.",
            "invalid_hours": "Неверный формат. Используйте формат: 9-18",
            "invalid_frequency": "Неверная частота. Введите число от 5 до 480.",
        }
    }
    
    @classmethod
    def get_text(cls, key: str, language: str = "en") -> str:
        return cls.TEXTS.get(language, cls.TEXTS["en"]).get(key, key)

class ReminderContent:
    """Manages reminder content including quotes and activities"""
    
    MOTIVATIONAL_QUOTES = {
        "en": [
            "Health is not about the weight you lose, but about the life you gain.",
            "Take care of your body. It's the only place you have to live.",
            "A healthy outside starts from the inside.",
            "Movement is medicine.",
            "Small steps lead to big changes.",
            "Your body can stand almost anything. It's your mind you have to convince.",
            "Progress, not perfection.",
            "Healthy habits are learned in the same way as unhealthy ones - through practice.",
        ],
        "ru": [
            "Здоровье - это не вес, который вы теряете, а жизнь, которую вы приобретаете.",
            "Заботьтесь о своем теле. Это единственное место, где вам предстоит жить.",
            "Здоровая внешность начинается изнутри.",
            "Движение - это лекарство.",
            "Маленькие шаги ведут к большим переменам.",
            "Ваше тело может выдержать почти все. Нужно убедить свой разум.",
            "Прогресс, а не совершенство.",
            "Здоровые привычки изучаются так же, как и нездоровые - через практику.",
        ]
    }
    
    ACTIVITIES = {
        "en": {
            ReminderType.STRETCH: [
                "Do 10 forward bends",
                "Stretch your arms above your head for 30 seconds",
                "Roll your shoulders backward 10 times",
                "Do 10 neck rotations (carefully)",
                "Stretch your wrists and fingers",
                "Do 10 torso twists",
                "Stand and reach for your toes",
                "Do 10 side bends",
            ],
            ReminderType.WATER: [
                "Drink a full glass of water",
                "Have a few sips of water",
                "Hydrate yourself with some water",
                "Time for your water break",
            ],
            ReminderType.WALK: [
                "Take a 3-minute walk",
                "Walk around your room for 2 minutes",
                "Go outside for a quick walk",
                "Walk up and down the stairs",
                "Take a stroll around your workspace",
            ],
            ReminderType.BREAK: [
                "Look away from the screen for 2 minutes",
                "Do some deep breathing exercises",
                "Close your eyes and relax for 1 minute",
                "Look out the window for a moment",
                "Take 5 deep breaths",
            ]
        },
        "ru": {
            ReminderType.STRETCH: [
                "Сделайте 10 наклонов вперед",
                "Потянитесь руками вверх на 30 секунд",
                "Сделайте 10 круговых движений плечами назад",
                "Сделайте 10 поворотов головы (аккуратно)",
                "Потяните запястья и пальцы",
                "Сделайте 10 поворотов туловища",
                "Встаньте и потянитесь к носкам",
                "Сделайте 10 наклонов в стороны",
            ],
            ReminderType.WATER: [
                "Выпейте полный стакан воды",
                "Сделайте несколько глотков воды",
                "Увлажнитесь водой",
                "Время для водного перерыва",
            ],
            ReminderType.WALK: [
                "Прогуляйтесь 3 минуты",
                "Походите по комнате 2 минуты",
                "Выйдите на улицу для быстрой прогулки",
                "Поднимитесь и спуститесь по лестнице",
                "Прогуляйтесь вокруг рабочего места",
            ],
            ReminderType.BREAK: [
                "Отвлекитесь от экрана на 2 минуты",
                "Сделайте дыхательные упражнения",
                "Закройте глаза и расслабьтесь на 1 минуту",
                "Посмотрите в окно",
                "Сделайте 5 глубоких вдохов",
            ]
        }
    }
    
    @classmethod
    def get_reminder_content(cls, reminder_type: ReminderType, language: str = "en") -> tuple:
        """Returns (activity, quote) for a reminder"""
        quote = random.choice(cls.MOTIVATIONAL_QUOTES.get(language, cls.MOTIVATIONAL_QUOTES["en"]))
        
        if reminder_type == ReminderType.ALL:
            # Choose random type
            available_types = [ReminderType.STRETCH, ReminderType.WATER, ReminderType.WALK, ReminderType.BREAK]
            reminder_type = random.choice(available_types)
        
        activities = cls.ACTIVITIES.get(language, cls.ACTIVITIES["en"])
        activity = random.choice(activities.get(reminder_type, activities[ReminderType.STRETCH]))
        
        return activity, quote, reminder_type

class UserManager:
    """Manages user settings and data persistence"""
    
    def __init__(self, data_file: str = "user_data.json"):
        self.data_file = data_file
        self.users: Dict[int, UserSettings] = {}
        self.load_users()
    
    def load_users(self):
        """Load user data from file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    for user_id, user_data in data.items():
                        # Convert reminder_types back to enum
                        if 'reminder_types' in user_data:
                            user_data['reminder_types'] = [ReminderType(rt) for rt in user_data['reminder_types']]
                        if 'mode' in user_data:
                            user_data['mode'] = ReminderMode(user_data['mode'])
                        
                        self.users[int(user_id)] = UserSettings(**user_data)
        except Exception as e:
            logger.error(f"Error loading users: {e}")
    
    def save_users(self):
        """Save user data to file"""
        try:
            data = {}
            for user_id, settings in self.users.items():
                user_data = asdict(settings)
                # Convert enums to strings for JSON serialization
                user_data['reminder_types'] = [rt.value for rt in settings.reminder_types]
                user_data['mode'] = settings.mode.value
                data[str(user_id)] = user_data
            
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving users: {e}")
    
    def get_user(self, user_id: int) -> UserSettings:
        """Get user settings, create default if doesn't exist"""
        if user_id not in self.users:
            self.users[user_id] = UserSettings(user_id=user_id)
            self.save_users()
        return self.users[user_id]
    
    def update_user(self, user_id: int, **kwargs):
        """Update user settings"""
        user = self.get_user(user_id)
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        self.save_users()

class HealthReminderBot:
    """Main bot class"""
    
    def __init__(self, token: str):
        self.token = token
        self.user_manager = UserManager()
        self.application = Application.builder().token(token).build()
        self.reminder_jobs = {}  # Track active reminder jobs
        
        # Register handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("settings", self.settings_command))
        self.application.add_handler(CommandHandler("stop", self.stop_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        user = self.user_manager.get_user(user_id)
        
        welcome_text = Localization.get_text("welcome", user.language)
        await update.message.reply_text(welcome_text)
        
        # Start reminder job
        await self.start_reminder_job(user_id, context)
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /settings command"""
        user_id = update.effective_user.id
        user = self.user_manager.get_user(user_id)
        
        keyboard = [
            [InlineKeyboardButton(Localization.get_text("language_selection", user.language), callback_data="lang_menu")],
            [InlineKeyboardButton(Localization.get_text("mode_selection", user.language), callback_data="mode_menu")],
            [InlineKeyboardButton(Localization.get_text("frequency_setting", user.language), callback_data="freq_menu")],
            [InlineKeyboardButton(Localization.get_text("reminder_types", user.language), callback_data="types_menu")],
            [InlineKeyboardButton("🟢 Activate" if not user.is_active else "🔴 Deactivate", 
                                callback_data="toggle_active")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = Localization.get_text("settings_menu", user.language)
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command"""
        user_id = update.effective_user.id
        self.user_manager.update_user(user_id, is_active=False)
        
        # Cancel reminder job
        if user_id in self.reminder_jobs:
            self.reminder_jobs[user_id].schedule_removal()
            del self.reminder_jobs[user_id]
        
        user = self.user_manager.get_user(user_id)
        text = Localization.get_text("bot_deactivated", user.language)
        await update.message.reply_text(text)
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards"""
        query = update.callback_query
        user_id = query.from_user.id
        user = self.user_manager.get_user(user_id)
        
        await query.answer()
        
        if query.data == "lang_menu":
            await self.show_language_menu(query, user)
        elif query.data.startswith("lang_"):
            await self.set_language(query, user)
        elif query.data == "mode_menu":
            await self.show_mode_menu(query, user)
        elif query.data.startswith("mode_"):
            await self.set_mode(query, user)
        elif query.data == "types_menu":
            await self.show_types_menu(query, user)
        elif query.data.startswith("type_"):
            await self.toggle_reminder_type(query, user)
        elif query.data == "toggle_active":
            await self.toggle_active(query, user, context)
        elif query.data in ["done", "remind_later", "skip"]:
            await self.handle_reminder_response(query, user, context)
    
    async def show_language_menu(self, query, user):
        """Show language selection menu"""
        keyboard = [
            [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")],
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = Localization.get_text("language_selection", user.language)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def set_language(self, query, user):
        """Set user language"""
        lang = query.data.split("_")[1]
        self.user_manager.update_user(user.user_id, language=lang)
        
        text = Localization.get_text("settings_saved", lang)
        await query.edit_message_text(text)
    
    async def show_mode_menu(self, query, user):
        """Show mode selection menu"""
        keyboard = [
            [InlineKeyboardButton(Localization.get_text("time_based", user.language), 
                                callback_data="mode_time")],
            [InlineKeyboardButton(Localization.get_text("inactivity_based", user.language), 
                                callback_data="mode_inactivity")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = Localization.get_text("mode_selection", user.language)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def set_mode(self, query, user):
        """Set reminder mode"""
        mode = ReminderMode.TIME_BASED if query.data == "mode_time" else ReminderMode.INACTIVITY
        self.user_manager.update_user(user.user_id, mode=mode)
        
        text = Localization.get_text("settings_saved", user.language)
        await query.edit_message_text(text)
    
    async def show_types_menu(self, query, user):
        """Show reminder types menu"""
        keyboard = [
            [InlineKeyboardButton("🧘‍♀️ Stretch", callback_data="type_stretch")],
            [InlineKeyboardButton("💧 Water", callback_data="type_water")],
            [InlineKeyboardButton("🚶‍♀️ Walk", callback_data="type_walk")],
            [InlineKeyboardButton("☕ Break", callback_data="type_break")],
            [InlineKeyboardButton("🎯 All Types", callback_data="type_all")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = Localization.get_text("reminder_types", user.language)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def toggle_reminder_type(self, query, user):
        """Toggle reminder type"""
        type_name = query.data.split("_")[1]
        reminder_type = ReminderType(type_name)
        
        if reminder_type in user.reminder_types:
            user.reminder_types.remove(reminder_type)
        else:
            user.reminder_types.append(reminder_type)
        
        if not user.reminder_types:
            user.reminder_types = [ReminderType.ALL]
        
        self.user_manager.update_user(user.user_id, reminder_types=user.reminder_types)
        
        text = Localization.get_text("settings_saved", user.language)
        await query.edit_message_text(text)
    
    async def toggle_active(self, query, user, context):
        """Toggle bot active/inactive"""
        new_status = not user.is_active
        self.user_manager.update_user(user.user_id, is_active=new_status)
        
        if new_status:
            await self.start_reminder_job(user.user_id, context)
            text = Localization.get_text("bot_activated", user.language)
        else:
            if user.user_id in self.reminder_jobs:
                self.reminder_jobs[user.user_id].schedule_removal()
                del self.reminder_jobs[user.user_id]
            text = Localization.get_text("bot_deactivated", user.language)
        
        await query.edit_message_text(text)
    
    async def handle_reminder_response(self, query, user, context):
        """Handle user response to reminder"""
        if query.data == "done":
            text = Localization.get_text("good_job", user.language)
        elif query.data == "remind_later":
            text = Localization.get_text("remind_in_10", user.language)
            # Schedule reminder in 10 minutes
            context.job_queue.run_once(
                self.send_reminder_callback,
                when=timedelta(minutes=10),
                data=user.user_id
            )
        else:  # skip
            text = Localization.get_text("skipped", user.language)
        
        await query.edit_message_text(text)
    
    async def start_reminder_job(self, user_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Start reminder job for user"""
        user = self.user_manager.get_user(user_id)
        
        if not user.is_active:
            return
        
        # Cancel existing job if any
        if user_id in self.reminder_jobs:
            self.reminder_jobs[user_id].schedule_removal()
        
        # Create new job
        job = context.job_queue.run_repeating(
            self.send_reminder_callback,
            interval=timedelta(minutes=user.frequency_minutes),
            first=timedelta(minutes=user.frequency_minutes),
            data=user_id
        )
        
        self.reminder_jobs[user_id] = job
    
    async def send_reminder_callback(self, context: ContextTypes.DEFAULT_TYPE):
        """Callback for sending reminders"""
        user_id = context.job.data
        await self.send_reminder(user_id, context)
    
    async def send_reminder(self, user_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Send reminder to user"""
        user = self.user_manager.get_user(user_id)
        
        if not user.is_active:
            return
        
        # Check if within active hours
        current_hour = datetime.now().hour
        if not (user.active_hours[0] <= current_hour <= user.active_hours[1]):
            return
        
        # Get reminder content
        reminder_type = random.choice(user.reminder_types)
        activity, quote, actual_type = ReminderContent.get_reminder_content(reminder_type, user.language)
        
        # Create reminder message
        reminder_key = f"{actual_type.value}_reminder"
        reminder_text = Localization.get_text(reminder_key, user.language)
        
        message = f"{reminder_text}\n\n💪 {activity}\n\n💬 {quote}"
        
        # Create inline keyboard
        keyboard = [
            [
                InlineKeyboardButton(Localization.get_text("done", user.language), callback_data="done"),
                InlineKeyboardButton(Localization.get_text("remind_later", user.language), callback_data="remind_later"),
            ],
            [
                InlineKeyboardButton(Localization.get_text("skip", user.language), callback_data="skip"),
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=message,
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error sending reminder to {user_id}: {e}")
    
    def run(self):
        """Run the bot"""
        print("Starting Health Reminder Bot...")
        self.application.run_polling()

# Main execution
if __name__ == "__main__":
    # Replace with your bot token
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
    
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("Please set your bot token in the BOT_TOKEN variable")
        print("Get your token from @BotFather on Telegram")
        exit(1)
    
    bot = HealthReminderBot(BOT_TOKEN)
    bot.run()
