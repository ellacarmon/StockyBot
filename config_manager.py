import json
from pathlib import Path
from typing import List, Dict, Any


class ConfigManager:
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """
        טעינת קונפיגורציה מקובץ JSON
        """
        default_config = {
            "allowed_users": [],
            "daily_cost_limit": 1.0,
            "max_request_cost": 0.1,
            "admin_users": []  # משתמשים שיכולים להוסיף משתמשים נוספים
        }

        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return {**default_config, **json.load(f)}
            return default_config
        except Exception as e:
            print(f"שגיאה בטעינת קונפיגורציה: {e}")
            return default_config

    def save_config(self) -> None:
        """
        שמירת הקונפיגורציה לקובץ
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"שגיאה בשמירת קונפיגורציה: {e}")

    def add_user(self, user_id: str, added_by: str = None) -> bool:
        """
        הוספת משתמש מורשה
        """
        if user_id not in self.config["allowed_users"]:
            self.config["allowed_users"].append(user_id)
            self.save_config()
            return True
        return False

    def remove_user(self, user_id: str, removed_by: str = None) -> bool:
        """
        הסרת משתמש מורשה
        """
        if user_id in self.config["allowed_users"]:
            self.config["allowed_users"].remove(user_id)
            self.save_config()
            return True
        return False

    def is_user_allowed(self, user_id: str) -> bool:
        """
        בדיקה האם המשתמש מורשה
        """
        return str(user_id) in self.config["allowed_users"]

    def is_admin(self, user_id: str) -> bool:
        """
        בדיקה האם המשתמש הוא מנהל
        """
        return str(user_id) in self.config["admin_users"]