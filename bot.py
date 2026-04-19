import asyncio
import logging
import os
from datetime import timedelta
from typing import Optional, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest, Forbidden
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from content import Localization, ReminderContent
from storage import ReminderMode, ReminderType, UserManager, UserSettings, parse_iso, utc_now


logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

ASK_FREQUENCY, ASK_ACTIVE_HOURS, ASK_TIMEZONE, ASK_INACTIVITY = range(4)
CHECKER_JOB_NAME = "global_reminder_checker"


def parse_hours(text: str) -> Optional[Tuple[int, int]]:
    text = text.strip().replace(" ", "")
    if "-" not in text:
        return None
    parts = text.split("-", 1)
    if len(parts) != 2:
        return None
    try:
        start, end = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    if not (0 <= start <= 23 and 1 <= end <= 24 and start < end):
        return None
    return start, end


def parse_int_in_range(text: str, minimum: int, maximum: int) -> Optional[int]:
    try:
        value = int(text.strip())
    except ValueError:
        return None
    if minimum <= value <= maximum:
        return value
    return None


def user_now(user: UserSettings):
    return utc_now() + timedelta(hours=user.timezone_offset)


def in_active_hours(user: UserSettings) -> bool:
    local = user_now(user)
    hour = local.hour
    start, end = user.active_hours
    return start <= hour < end


def reminder_type_label(rtype: ReminderType, lang: str) -> str:
    labels = {
        "en": {
            ReminderType.STRETCH: "🧘 Stretch",
            ReminderType.WATER: "💧 Water",
            ReminderType.WALK: "🚶 Walk",
            ReminderType.BREAK: "☕ Break",
            ReminderType.ALL: "🎯 All types",
        },
        "ru": {
            ReminderType.STRETCH: "🧘 Растяжка",
            ReminderType.WATER: "💧 Вода",
            ReminderType.WALK: "🚶 Прогулка",
            ReminderType.BREAK: "☕ Перерыв",
            ReminderType.ALL: "🎯 Все типы",
        },
    }
    return labels.get(lang, labels["en"])[rtype]


class HealthReminderBot:
    def __init__(self, token: str, data_file: str = "user_data.json"):
        self.token = token
        self.user_manager = UserManager(data_file=data_file)
        self.application = Application.builder().token(token).build()
        self.application.post_init = self.post_init
        self._register_handlers()

    async def post_init(self, application: Application) -> None:
        jobs = application.job_queue.get_jobs_by_name(CHECKER_JOB_NAME)
        for job in jobs:
            job.schedule_removal()
        application.job_queue.run_repeating(
            self.global_checker,
            interval=timedelta(seconds=60),
            first=10,
            name=CHECKER_JOB_NAME,
        )
        logger.info("Global checker started")

    def _register_handlers(self) -> None:
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("pause", self.pause_command))
        self.application.add_handler(CommandHandler("resume", self.resume_command))
        self.application.add_handler(CommandHandler("stop", self.stop_command))
        self.application.add_handler(CommandHandler("test", self.test_command))
        self.application.add_handler(CommandHandler("snooze", self.snooze_command))

        settings_conv = ConversationHandler(
            entry_points=[CommandHandler("settings", self.settings_command)],
            states={
                ASK_FREQUENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_frequency)],
                ASK_ACTIVE_HOURS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_active_hours)],
                ASK_TIMEZONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_timezone)],
                ASK_INACTIVITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_inactivity)],
            },
            fallbacks=[CommandHandler("settings", self.settings_command)],
            allow_reentry=True,
        )
        self.application.add_handler(settings_conv)
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.track_text_interaction))

    def touch_user(self, user_id: int) -> UserSettings:
        user = self.user_manager.get_user(user_id)
        user.last_interaction_at = utc_now().isoformat()
        if user.mode == ReminderMode.TIME_BASED and not parse_iso(user.next_reminder_at):
            user.next_reminder_at = (utc_now() + timedelta(minutes=user.frequency_minutes)).isoformat()
        self.user_manager.save_users()
        return user

    def reset_next_reminder(self, user: UserSettings, from_now: bool = True) -> None:
        base = utc_now() if from_now else parse_iso(user.next_reminder_at) or utc_now()
        user.next_reminder_at = (base + timedelta(minutes=user.frequency_minutes)).isoformat()
        self.user_manager.save_users()

    def build_main_menu(self, user: UserSettings) -> InlineKeyboardMarkup:
        lang = user.language
        on_off_label = "🔴 Deactivate" if lang == "en" else "🔴 Выключить"
        if not user.is_active:
            on_off_label = "🟢 Activate" if lang == "en" else "🟢 Включить"

        keyboard = [
            [InlineKeyboardButton(f"🌍 {Localization.t('language', lang)}", callback_data="settings:language")],
            [InlineKeyboardButton(f"🧠 {Localization.t('mode', lang)}", callback_data="settings:mode")],
            [InlineKeyboardButton(f"⏱️ {Localization.t('frequency', lang)}", callback_data="settings:frequency")],
            [InlineKeyboardButton(f"💤 {Localization.t('inactivity', lang)}", callback_data="settings:inactivity")],
            [InlineKeyboardButton(f"🕒 {Localization.t('active_hours', lang)}", callback_data="settings:hours")],
            [InlineKeyboardButton(f"🎯 {Localization.t('reminder_types', lang)}", callback_data="settings:types")],
            [InlineKeyboardButton(f"🌐 {Localization.t('timezone', lang)}", callback_data="settings:timezone")],
            [InlineKeyboardButton(on_off_label, callback_data="settings:toggle_active")],
            [InlineKeyboardButton(Localization.t("close", lang), callback_data="settings:close")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def build_language_menu(self, user: UserSettings) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🇺🇸 English", callback_data="lang:en")],
                [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang:ru")],
                [InlineKeyboardButton(Localization.t("back", user.language), callback_data="settings:back")],
            ]
        )

    def build_mode_menu(self, user: UserSettings) -> InlineKeyboardMarkup:
        lang = user.language
        keyboard = [
            [InlineKeyboardButton(Localization.t("time_based", lang), callback_data="mode:time_based")],
            [InlineKeyboardButton(Localization.t("inactivity_based", lang), callback_data="mode:inactivity")],
            [InlineKeyboardButton(Localization.t("back", lang), callback_data="settings:back")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def build_types_menu(self, user: UserSettings) -> InlineKeyboardMarkup:
        lang = user.language
        rows = []
        for rtype in [
            ReminderType.STRETCH,
            ReminderType.WATER,
            ReminderType.WALK,
            ReminderType.BREAK,
            ReminderType.ALL,
        ]:
            enabled = rtype in user.reminder_types
            prefix = "✅" if enabled else "▫️"
            rows.append([
                InlineKeyboardButton(
                    f"{prefix} {reminder_type_label(rtype, lang)}",
                    callback_data=f"type:{rtype.value}",
                )
            ])
        rows.append([InlineKeyboardButton(Localization.t("back", lang), callback_data="settings:back")])
        return InlineKeyboardMarkup(rows)

    def build_reminder_keyboard(self, user: UserSettings) -> InlineKeyboardMarkup:
        lang = user.language
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(Localization.t("done", lang), callback_data="reminder:done"),
                    InlineKeyboardButton(Localization.t("remind_later", lang), callback_data="reminder:later"),
                ],
                [InlineKeyboardButton(Localization.t("skip", lang), callback_data="reminder:skip")],
            ]
        )

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = self.touch_user(update.effective_user.id)
        user.is_active = True
        if not parse_iso(user.next_reminder_at):
            self.reset_next_reminder(user)
        self.user_manager.save_users()

        await update.message.reply_text(
            Localization.t("welcome", user.language),
            parse_mode="Markdown",
            reply_markup=self.build_main_menu(user),
        )
        await update.message.reply_text(Localization.t("help", user.language), parse_mode="Markdown")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = self.touch_user(update.effective_user.id)
        await update.message.reply_text(Localization.t("help", user.language), parse_mode="Markdown")

    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = self.touch_user(update.effective_user.id)
        await update.message.reply_text(
            f"{Localization.t('settings_menu', user.language)}\n\n{Localization.t('menu_hint', user.language)}",
            reply_markup=self.build_main_menu(user),
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = self.touch_user(update.effective_user.id)
        lang = user.language
        types = ", ".join(reminder_type_label(t, lang) for t in user.reminder_types)
        mode_label = Localization.t("time_based", lang) if user.mode == ReminderMode.TIME_BASED else Localization.t("inactivity_based", lang)
        text = (
            f"{Localization.t('status_title', lang)}\n\n"
            f"• *{Localization.t('active', lang)}:* {Localization.t('yes', lang) if user.is_active else Localization.t('no', lang)}\n"
            f"• *{Localization.t('language', lang)}:* {user.language}\n"
            f"• *{Localization.t('mode', lang)}:* {mode_label}\n"
            f"• *{Localization.t('frequency', lang)}:* {user.frequency_minutes} min\n"
            f"• *{Localization.t('inactivity', lang)}:* {user.inactivity_minutes} min\n"
            f"• *{Localization.t('active_hours', lang)}:* {user.active_hours[0]:02d}:00–{user.active_hours[1]:02d}:00\n"
            f"• *{Localization.t('timezone', lang)}:* UTC{user.timezone_offset:+d}\n"
            f"• *{Localization.t('reminder_types', lang)}:* {types}"
        )
        await update.message.reply_text(text, parse_mode="Markdown")

    async def pause_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = self.touch_user(update.effective_user.id)
        user.is_active = False
        self.user_manager.save_users()
        await update.message.reply_text(Localization.t("bot_paused", user.language))

    async def resume_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = self.touch_user(update.effective_user.id)
        user.is_active = True
        self.reset_next_reminder(user)
        await update.message.reply_text(Localization.t("bot_resumed", user.language))

    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = self.touch_user(update.effective_user.id)
        user.is_active = False
        self.user_manager.save_users()
        await update.message.reply_text(Localization.t("bot_deactivated", user.language))

    async def test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = self.touch_user(update.effective_user.id)
        await self.send_reminder(user.user_id, context, force=True)
        await update.message.reply_text(Localization.t("test_sent", user.language))

    async def snooze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = self.touch_user(update.effective_user.id)
        minutes = 10
        if context.args:
            parsed = parse_int_in_range(context.args[0], 1, 720)
            if parsed is not None:
                minutes = parsed
        user.snoozed_until = (utc_now() + timedelta(minutes=minutes)).isoformat()
        if user.mode == ReminderMode.TIME_BASED:
            user.next_reminder_at = user.snoozed_until
        self.user_manager.save_users()
        await update.message.reply_text(Localization.t("snoozed", user.language, minutes=minutes))

    async def track_text_interaction(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_user:
            return
        self.touch_user(update.effective_user.id)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user = self.touch_user(query.from_user.id)
        data = query.data or ""

        if data == "settings:back":
            await query.edit_message_text(
                text=f"{Localization.t('settings_menu', user.language)}\n\n{Localization.t('menu_hint', user.language)}",
                reply_markup=self.build_main_menu(user),
                parse_mode="Markdown",
            )
            return ConversationHandler.END

        if data == "settings:close":
            await query.edit_message_text(Localization.t("settings_saved", user.language))
            return ConversationHandler.END

        if data == "settings:language":
            await query.edit_message_text(
                Localization.t("choose_language", user.language),
                reply_markup=self.build_language_menu(user),
            )
            return ConversationHandler.END

        if data.startswith("lang:"):
            lang = data.split(":", 1)[1]
            user.language = lang if lang in Localization.TEXTS else "en"
            self.user_manager.save_users()
            await query.edit_message_text(
                Localization.t("settings_saved", user.language),
                reply_markup=self.build_main_menu(user),
            )
            return ConversationHandler.END

        if data == "settings:mode":
            await query.edit_message_text(
                Localization.t("choose_mode", user.language),
                reply_markup=self.build_mode_menu(user),
            )
            return ConversationHandler.END

        if data.startswith("mode:"):
            user.mode = ReminderMode(data.split(":", 1)[1])
            if user.mode == ReminderMode.TIME_BASED:
                self.reset_next_reminder(user)
            self.user_manager.save_users()
            await query.edit_message_text(
                Localization.t("settings_saved", user.language),
                reply_markup=self.build_main_menu(user),
            )
            return ConversationHandler.END

        if data == "settings:types":
            await query.edit_message_text(
                Localization.t("choose_types", user.language),
                reply_markup=self.build_types_menu(user),
            )
            return ConversationHandler.END

        if data.startswith("type:"):
            selected = ReminderType(data.split(":", 1)[1])
            if selected == ReminderType.ALL:
                user.reminder_types = [ReminderType.ALL]
            else:
                if ReminderType.ALL in user.reminder_types:
                    user.reminder_types = [x for x in user.reminder_types if x != ReminderType.ALL]
                if selected in user.reminder_types:
                    user.reminder_types.remove(selected)
                else:
                    user.reminder_types.append(selected)
                if not user.reminder_types:
                    user.reminder_types = [ReminderType.ALL]
            self.user_manager.save_users()
            await query.edit_message_text(
                Localization.t("choose_types", user.language),
                reply_markup=self.build_types_menu(user),
            )
            return ConversationHandler.END

        if data == "settings:toggle_active":
            user.is_active = not user.is_active
            if user.is_active:
                self.reset_next_reminder(user)
                text = Localization.t("bot_activated", user.language)
            else:
                self.user_manager.save_users()
                text = Localization.t("bot_deactivated", user.language)
            await query.edit_message_text(text, reply_markup=self.build_main_menu(user))
            return ConversationHandler.END

        if data == "settings:frequency":
            await query.message.reply_text(Localization.t("ask_frequency", user.language), parse_mode="Markdown")
            return ASK_FREQUENCY

        if data == "settings:inactivity":
            await query.message.reply_text(Localization.t("ask_inactivity", user.language), parse_mode="Markdown")
            return ASK_INACTIVITY

        if data == "settings:hours":
            await query.message.reply_text(Localization.t("ask_active_hours", user.language), parse_mode="Markdown")
            return ASK_ACTIVE_HOURS

        if data == "settings:timezone":
            await query.message.reply_text(Localization.t("ask_timezone", user.language), parse_mode="Markdown")
            return ASK_TIMEZONE

        if data.startswith("reminder:"):
            action = data.split(":", 1)[1]
            await self.handle_reminder_response(update, context, user, action)
            return ConversationHandler.END

        return ConversationHandler.END

    async def receive_frequency(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = self.touch_user(update.effective_user.id)
        value = parse_int_in_range(update.message.text, 5, 480)
        if value is None:
            await update.message.reply_text(Localization.t("invalid_frequency", user.language), parse_mode="Markdown")
            return ASK_FREQUENCY
        user.frequency_minutes = value
        self.reset_next_reminder(user)
        await update.message.reply_text(Localization.t("settings_saved", user.language))
        return ConversationHandler.END

    async def receive_inactivity(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = self.touch_user(update.effective_user.id)
        value = parse_int_in_range(update.message.text, 5, 480)
        if value is None:
            await update.message.reply_text(Localization.t("invalid_inactivity", user.language), parse_mode="Markdown")
            return ASK_INACTIVITY
        user.inactivity_minutes = value
        self.user_manager.save_users()
        await update.message.reply_text(Localization.t("settings_saved", user.language))
        return ConversationHandler.END

    async def receive_active_hours(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = self.touch_user(update.effective_user.id)
        hours = parse_hours(update.message.text)
        if hours is None:
            await update.message.reply_text(Localization.t("invalid_hours", user.language), parse_mode="Markdown")
            return ASK_ACTIVE_HOURS
        user.active_hours = hours
        self.user_manager.save_users()
        await update.message.reply_text(Localization.t("settings_saved", user.language))
        return ConversationHandler.END

    async def receive_timezone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = self.touch_user(update.effective_user.id)
        value = parse_int_in_range(update.message.text, -12, 14)
        if value is None:
            await update.message.reply_text(Localization.t("invalid_timezone", user.language), parse_mode="Markdown")
            return ASK_TIMEZONE
        user.timezone_offset = value
        self.user_manager.save_users()
        await update.message.reply_text(Localization.t("settings_saved", user.language))
        return ConversationHandler.END

    async def global_checker(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        for user_id in list(self.user_manager.users.keys()):
            try:
                user = self.user_manager.get_user(user_id)
                if await self.should_send_reminder(user):
                    await self.send_reminder(user_id, context)
            except Exception:
                logger.exception("Error while checking reminders for user %s", user_id)

    async def should_send_reminder(self, user: UserSettings) -> bool:
        now = utc_now()
        if not user.is_active:
            return False

        snoozed_until = parse_iso(user.snoozed_until)
        if snoozed_until and now < snoozed_until:
            return False

        if not in_active_hours(user):
            return False

        last_sent = parse_iso(user.last_reminder_sent_at)
        if last_sent and now - last_sent < timedelta(minutes=1):
            return False

        if user.mode == ReminderMode.TIME_BASED:
            next_due = parse_iso(user.next_reminder_at)
            if next_due is None:
                user.next_reminder_at = (now + timedelta(minutes=user.frequency_minutes)).isoformat()
                self.user_manager.save_users()
                return False
            return now >= next_due

        last_interaction = parse_iso(user.last_interaction_at) or now
        if now - last_interaction < timedelta(minutes=user.inactivity_minutes):
            return False
        if last_sent and now - last_sent < timedelta(minutes=user.inactivity_minutes):
            return False
        return True

    async def send_reminder(self, user_id: int, context: ContextTypes.DEFAULT_TYPE, force: bool = False) -> None:
        user = self.user_manager.get_user(user_id)
        if not force and not await self.should_send_reminder(user):
            return
        if not force and not in_active_hours(user):
            return

        selected = user.reminder_types[0] if len(user.reminder_types) == 1 else __import__("random").choice(user.reminder_types)
        activity, quote, actual_type = ReminderContent.pick(selected, user.language)
        title = Localization.t(f"{actual_type.value}_reminder", user.language)
        text = f"{title}\n\n💪 {activity}\n\n💬 _{quote}_"

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=self.build_reminder_keyboard(user),
            )
            user.last_reminder_sent_at = utc_now().isoformat()
            user.snoozed_until = None
            if user.mode == ReminderMode.TIME_BASED:
                self.reset_next_reminder(user)
            else:
                self.user_manager.save_users()
        except Forbidden:
            logger.warning("Bot blocked by user %s. Deactivating reminders.", user_id)
            user.is_active = False
            self.user_manager.save_users()
        except Exception:
            logger.exception("Failed to send reminder to user %s", user_id)

    async def handle_reminder_response(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user: UserSettings,
        action: str,
    ) -> None:
        query = update.callback_query
        self.touch_user(user.user_id)

        if action == "done":
            text = Localization.t("good_job", user.language)
        elif action == "later":
            text = Localization.t("remind_in_10", user.language)
            user.snoozed_until = (utc_now() + timedelta(minutes=10)).isoformat()
            if user.mode == ReminderMode.TIME_BASED:
                user.next_reminder_at = user.snoozed_until
            self.user_manager.save_users()
        else:
            text = Localization.t("skipped", user.language)
            if user.mode == ReminderMode.INACTIVITY:
                user.last_interaction_at = utc_now().isoformat()
                self.user_manager.save_users()

        try:
            await query.edit_message_text(text)
        except BadRequest:
            await query.message.reply_text(text)

    def run(self) -> None:
        logger.info("Starting Health Reminder Bot")
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())
        self.application.run_polling(drop_pending_updates=True)


def main() -> None:
    token = os.getenv("BOT_TOKEN", "7610586295:AAGmqczl3NA3hLEI2oslKcZdqykTN6nbAk8")
    if token == "YOUR_BOT_TOKEN_HERE":
        raise SystemExit(
            "Set your Telegram bot token first. Example:\n"
            "Linux/macOS: export BOT_TOKEN='123:abc'\n"
            "Windows PowerShell: $env:BOT_TOKEN='123:abc'"
        )

    bot = HealthReminderBot(token=token, data_file="user_data.json")
    bot.run()


if __name__ == "__main__":
    main()
