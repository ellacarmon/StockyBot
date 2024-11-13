import os
from telegram_bot import StockNewsTelegramBot
def main():
    # קבלת הגדרות מהסביבה
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    AZURE_API_KEY = os.getenv("AZURE_API_KEY")
    ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY")

    if not all([TELEGRAM_TOKEN, AZURE_API_KEY, ALPHA_VANTAGE_KEY]):
        raise ValueError("חסרים טוקנים! אנא הגדר את כל הטוקנים הנדרשים")

    bot = StockNewsTelegramBot(TELEGRAM_TOKEN, AZURE_API_KEY, ALPHA_VANTAGE_KEY)
    print("הבוט מופעל! 🚀")
    bot.run()