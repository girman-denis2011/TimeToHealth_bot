import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ReminderType(str, Enum):
    STRETCH = "stretch"
    WATER = "water"
    WALK = "walk"
    BREAK = "break"
    ALL = "all"


class ReminderMode(str, Enum):
    TIME_BASED = "time_based"
    INACTIVITY = "inactivity"


@dataclass
class UserSettings:
    user_id: int
    language: str = "en"
    mode: ReminderMode = ReminderMode.TIME_BASED
    frequency_minutes: int = 60
    inactivity_minutes: int = 45
    active_hours: Tuple[int, int] = (9, 18)
    reminder_types: List[ReminderType] = field(default_factory=lambda: [ReminderType.ALL])
    is_active: bool = True
    timezone_offset: int = 0
    last_interaction_at: Optional[str] = None
    next_reminder_at: Optional[str] = None
    snoozed_until: Optional[str] = None
    last_reminder_sent_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "language": self.language,
            "mode": self.mode.value,
            "frequency_minutes": self.frequency_minutes,
            "inactivity_minutes": self.inactivity_minutes,
            "active_hours": list(self.active_hours),
            "reminder_types": [t.value for t in self.reminder_types],
            "is_active": self.is_active,
            "timezone_offset": self.timezone_offset,
            "last_interaction_at": self.last_interaction_at,
            "next_reminder_at": self.next_reminder_at,
            "snoozed_until": self.snoozed_until,
            "last_reminder_sent_at": self.last_reminder_sent_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserSettings":
        return cls(
            user_id=int(data["user_id"]),
            language=data.get("language", "en"),
            mode=ReminderMode(data.get("mode", ReminderMode.TIME_BASED.value)),
            frequency_minutes=int(data.get("frequency_minutes", 60)),
            inactivity_minutes=int(data.get("inactivity_minutes", 45)),
            active_hours=tuple(data.get("active_hours", [9, 18])),
            reminder_types=[ReminderType(x) for x in data.get("reminder_types", [ReminderType.ALL.value])],
            is_active=bool(data.get("is_active", True)),
            timezone_offset=int(data.get("timezone_offset", 0)),
            last_interaction_at=data.get("last_interaction_at"),
            next_reminder_at=data.get("next_reminder_at"),
            snoozed_until=data.get("snoozed_until"),
            last_reminder_sent_at=data.get("last_reminder_sent_at"),
        )


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


class UserManager:
    def __init__(self, data_file: str = "user_data.json"):
        self.data_file = data_file
        self.users: Dict[int, UserSettings] = {}
        self.load_users()

    def load_users(self) -> None:
        if not os.path.exists(self.data_file):
            return
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            self.users = {int(uid): UserSettings.from_dict(data) for uid, data in raw.items()}
            logger.info("Loaded %s users", len(self.users))
        except Exception:
            logger.exception("Failed to load users from %s", self.data_file)
            self.users = {}

    def save_users(self) -> None:
        try:
            data = {str(uid): user.to_dict() for uid, user in self.users.items()}
            directory = os.path.dirname(os.path.abspath(self.data_file)) or "."
            os.makedirs(directory, exist_ok=True)
            with tempfile.NamedTemporaryFile("w", delete=False, dir=directory, encoding="utf-8") as tmp:
                json.dump(data, tmp, ensure_ascii=False, indent=2)
                temp_name = tmp.name
            os.replace(temp_name, self.data_file)
        except Exception:
            logger.exception("Failed to save users to %s", self.data_file)

    def get_user(self, user_id: int) -> UserSettings:
        if user_id not in self.users:
            user = UserSettings(user_id=user_id)
            now = utc_now()
            user.last_interaction_at = now.isoformat()
            user.next_reminder_at = now.isoformat()
            self.users[user_id] = user
            self.save_users()
        return self.users[user_id]

    def update_user(self, user_id: int, **kwargs) -> UserSettings:
        user = self.get_user(user_id)
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        self.save_users()
        return user
