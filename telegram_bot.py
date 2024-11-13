from stock_analyzer import StockNewsAnalyzer
from security_manager import SecurityManager
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update
import os

class StockNewsTelegramBot:
    def __init__(self, telegram_token: str, azure_api_key: str, alpha_vantage_key: str):
        self.application = Application.builder().token(telegram_token).build()
        self.analyzer = StockNewsAnalyzer(azure_api_key, alpha_vantage_key)
        self.security = SecurityManager()

        # הוספת פקודות
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("usage", self.usage_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.security.is_user_allowed(str(update.effective_user.id)):
            await update.message.reply_text("מצטער, אין לך הרשאה להשתמש בבוט זה.")
            return

        await update.message.reply_text(
            "שלום! אני בוט שעוזר לנתח חדשות על מניות. 📈\n\n"
            "אתה יכול לשאול אותי שאלות כמו:\n"
            "• למה המניה של אפל יורדת?\n"
            "• מה קורה עם המניה של טסלה?\n"
            "• תסביר מה קורה עם abbvie\n\n"
            "פקודות זמינות:\n"
            "/usage - הצגת נתוני שימוש ותקציב\n"
            "/help - עזרה"
        )
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        טיפול בפקודת /help
        """
        await update.message.reply_text(
            "הנה כמה דברים שאני יכול לעשות:\n\n"
            "1️⃣ לנתח חדשות על מניות\n"
            "2️⃣ להסביר שינויים במחיר\n"
            "3️⃣ לתת מידע על מגמות אחרונות\n\n"
            "פשוט שאל אותי שאלה על מניה שמעניינת אותך!"
        )
    async def usage_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        הצגת נתוני שימוש למשתמש
        """
        if not self.security.is_user_allowed(str(update.effective_user.id)):
            await update.message.reply_text("מצטער, אין לך הרשאה להשתמש בבוט זה.")
            return

        usage = self.security.get_user_usage(str(update.effective_user.id))
        await update.message.reply_text(
            f"📊 נתוני שימוש:\n"
            f"• עלות יומית: ${usage['daily_cost']:.4f}\n"
            f"• תקציב נותר: ${usage['remaining_budget']:.4f}\n"
            f"• מגבלת עלות לבקשה: ${self.security.max_request_cost:.4f}\n"
            f"• מגבלת עלות יומית: ${self.security.daily_limit:.2f}"
        )
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)

        # בדיקת הרשאות
        if not self.security.is_user_allowed(user_id):
            await update.message.reply_text("מצטער, אין לך הרשאה להשתמש בבוט זה.")
            return

        user_text = update.message.text

        if context.user_data.get('awaiting_confirmation'):
            await self.process_confirmation(update, context)
            return

        ticker = self.analyzer.get_ticker_from_text(user_text)
        if not ticker:
            await update.message.reply_text("לא הצלחתי לזהות את שם החברה. אנא נסה שוב עם שם חברה ברור.")
            return

        try:
            await self.prepare_analysis(update, context, ticker, user_text)
        except Exception as e:
            await update.message.reply_text(f"מצטער, נתקלתי בשגיאה: {str(e)}")
    async def prepare_analysis(self, update: Update, context: ContextTypes.DEFAULT_TYPE, ticker: str, question: str):
        try:
            # הכנת הניתוח כרגיל...
            stock_info = self.analyzer.get_stock_info(ticker)
            news = self.analyzer.fetch_news(ticker)

            context_text = f"""
מידע על המניה {stock_info['name']} ({ticker}):
- מחיר נוכחי: ${stock_info['current_price']}
- שינוי באחוזים: {stock_info['percent_change']}%

חדשות אחרונות:
"""
            for item in news:
                context_text += f"""
- {item['title']}
  מקור: {item['source']}
  תקציר: {item['summary'][:200]}...
"""

            prompt = f"""בהתבסס על המידע הבא, אנא ענה על השאלה: "{question}"

{context_text}

אנא תן תשובה מקיפה בעברית שמסבירה את המצב בצורה ברורה."""

            # חישוב עלות משוערת
            input_tokens = self.analyzer.cost_calculator.estimate_tokens(prompt)
            cost_estimate = self.analyzer.cost_calculator.calculate_cost(input_tokens)

            # בדיקת מגבלות אבטחה
            can_request, message = self.security.can_make_request(
                str(update.effective_user.id),
                cost_estimate['total_cost']
            )

            if not can_request:
                await update.message.reply_text(f"❌ {message}")
                return

            # שמירת המידע בקונטקסט
            context.user_data['pending_analysis'] = {
                'prompt': prompt,
                'cost_estimate': cost_estimate
            }
            context.user_data['awaiting_confirmation'] = True

            # קבלת נתוני שימוש עדכניים
            usage = self.security.get_user_usage(str(update.effective_user.id))

            # שליחת בקשת אישור למשתמש
            confirmation_message = (
                f"📊 הערכת עלויות:\n"
                f"• טוקנים בשאילתה: {cost_estimate['input_tokens']:,}\n"
                f"• טוקנים משוערים בתשובה: {cost_estimate['output_tokens']:,}\n"
                f"• עלות משוערת: ${cost_estimate['total_cost']:.4f}\n"
                f"• תקציב יומי נותר: ${usage['remaining_budget']:.4f}\n\n"
                f"האם להמשיך עם הניתוח? (כן/לא)"
            )
            await update.message.reply_text(confirmation_message)

        except Exception as e:
            await update.message.reply_text(f"שגיאה בהכנת הניתוח: {str(e)}")
    async def process_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        response = update.message.text.lower()
        if response not in ['כן', 'yes', 'y', 'כ']:
            await update.message.reply_text("הניתוח בוטל.")
            context.user_data.clear()
            return

        processing_message = await update.message.reply_text("מעבד את הבקשה... ⏳")

        try:
            response = self.analyzer.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system",
                     "content": "אתה אנליסט פיננסי מומחה שמנתח מניות ומסביר מגמות בשוק ההון בעברית ברורה."},
                    {"role": "user", "content": context.user_data['pending_analysis']['prompt']}
                ]
            )

            actual_cost = self.analyzer.cost_calculator.calculate_cost(
                response.usage.prompt_tokens,
                response.usage.completion_tokens
            )

            # עדכון נתוני שימוש
            self.security.update_usage(str(update.effective_user.id), actual_cost['total_cost'])
            usage = self.security.get_user_usage(str(update.effective_user.id))

            answer = response.choices[0].message.content
            cost_summary = (
                f"\n\n💰 סיכום עלויות:\n"
                f"• טוקנים בשאילתה: {response.usage.prompt_tokens:,}\n"
                f"• טוקנים בתשובה: {response.usage.completion_tokens:,}\n"
                f"• עלות: ${actual_cost['total_cost']:.4f}\n"
                f"• תקציב יומי נותר: ${usage['remaining_budget']:.4f}"
            )

            await processing_message.edit_text(f"{answer}{cost_summary}")

        except Exception as e:
            await processing_message.edit_text(f"שגיאה בביצוע הניתוח: {str(e)}")
        finally:
            context.user_data.clear()
    def run(self):
        """
        הפעלת הבוט
        """
        self.application.run_polling()
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
