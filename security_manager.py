from typing import Tuple
from datetime import datetime
from config_manager import ConfigManager
import os

class SecurityManager:
    def __init__(self):
        """
        מנהל האבטחה של הבוט
        """
        self.config_manager = ConfigManager()
        # רשימת משתמשים מורשים (Telegram user IDs)
        self.allowed_users = self.config_manager.get_users()
        self.admin_users = self.config_manager.get_admins()

        # הגבלות שימוש
        self.daily_limit = float(os.getenv("DAILY_COST_LIMIT", "1.0"))  # הגבלת עלות יומית בדולרים
        self.max_request_cost = float(os.getenv("MAX_REQUEST_COST", "0.1"))  # עלות מקסימלית לבקשה בודדת

        # מעקב שימוש
        self.usage_data = {}  # {user_id: {'daily_cost': 0.0, 'last_reset': datetime}}

    def is_user_allowed(self, user_id: str) -> bool:
        """
        בדיקה האם המשתמש מורשה להשתמש בבוט
        """
        return str(user_id) in self.allowed_users

    def is_user_admin(self, user_id: str) -> bool:
        """
        בדיקה האם המשתמש הוא מנהל
        """
        return str(user_id) in self.admin_users

    def reset_daily_usage_if_needed(self, user_id: str):
        """
        איפוס מונה יומי אם עבר יום
        """
        if user_id not in self.usage_data:
            self.usage_data[user_id] = {'daily_cost': 0.0, 'last_reset': datetime.now()}
            return

        last_reset = self.usage_data[user_id]['last_reset']
        if (datetime.now() - last_reset).days >= 1:
            self.usage_data[user_id] = {'daily_cost': 0.0, 'last_reset': datetime.now()}

    def can_make_request(self, user_id: str, estimated_cost: float) -> Tuple[bool, str]:
        """
        בדיקה האם המשתמש יכול לבצע את הבקשה
        """
        self.reset_daily_usage_if_needed(user_id)
        user_data = self.usage_data[user_id]

        if estimated_cost > self.max_request_cost:
            return False, f"העלות המשוערת (${estimated_cost:.2f}) חורגת מהמגבלה המקסימלית לבקשה (${self.max_request_cost:.2f})"

        if user_data['daily_cost'] + estimated_cost > self.daily_limit:
            remaining = self.daily_limit - user_data['daily_cost']
            return False, f"חריגה ממגבלת העלות היומית. נותרו: ${remaining:.2f}"

        return True, ""

    def update_usage(self, user_id: str, actual_cost: float):
        """
        עדכון השימוש של המשתמש
        """
        self.reset_daily_usage_if_needed(user_id)
        self.usage_data[user_id]['daily_cost'] += actual_cost

    def get_user_usage(self, user_id: str) -> dict:
        """
        קבלת נתוני השימוש של המשתמש
        """
        self.reset_daily_usage_if_needed(user_id)
        return {
            'daily_cost': self.usage_data[user_id]['daily_cost'],
            'remaining_budget': self.daily_limit - self.usage_data[user_id]['daily_cost']
        }

    def add_user(self, user_id: str, added_by: str = None) -> bool:
        """
        הוספת משתמש מורשה
        """
        if user_id not in self.allowed_users:
            self.allowed_users.append(user_id)
            self.config_manager.add_user(user_id, added_by)
            self.config_manager.save_config()
            return True
        return False

    def remove_user(self, user_id: str, removed_by: str = None) -> bool:
        """
        הסרת משתמש מורשה
        """
        if user_id in self.allowed_users:
            self.allowed_users.remove(user_id)
            self.config_manager.remove_user(user_id, removed_by)
            self.config_manager.save_config()
            return True
        return False
