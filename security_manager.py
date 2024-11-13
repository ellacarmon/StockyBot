from config_manager import ConfigManager
from typing import List, Dict, Any
import os

class SecurityManager:
    def __init__(self):
        self.config = ConfigManager()
        # קריאה למגבלות מהקונפיגורציה
        self.daily_limit = float(os.getenv("DAILY_COST_LIMIT", self.config.config["daily_cost_limit"]))
        self.max_request_cost = float(os.getenv("MAX_REQUEST_COST", self.config.config["max_request_cost"]))
        self.usage_data = {}

    def is_user_allowed(self, user_id: str) -> bool:
        return self.config.is_user_allowed(user_id)

    def is_admin(self, user_id: str) -> bool:
        return self.config.is_admin(user_id)



