from app.stock_analyzer import StockNewsAnalyzer
from utils.security_manager import SecurityManager
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update
import os
from dotenv import load_dotenv
from pathlib import Path

class StockNewsTelegramBot:
    def __init__(self, telegram_token: str, azure_api_key: str, alpha_vantage_key: str):
        self.application = Application.builder().token(telegram_token).build()
        self.analyzer = StockNewsAnalyzer(azure_api_key, alpha_vantage_key)
        self.security = SecurityManager()

        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("usage", self.usage_command))
        self.application.add_handler(CommandHandler("admin", self.admin_command))
        self.application.add_handler(CommandHandler("stocks", self.stocks_command))
        self.application.add_handler(CommandHandler("addstock", self.add_stock_command))
        self.application.add_handler(CommandHandler("removestock", self.remove_stock_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.security.is_user_allowed(str(update.effective_user.id)):
            await update.message.reply_text("מצטערת, אין לך הרשאה להשתמש בבוט זה.")
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
        if not self.security.is_user_allowed(str(update.effective_user.id)):
            await update.message.reply_text("מצטערתת, אין לך הרשאה להשתמש בבוט זה.")
            return

        is_admin = self.security.is_user_admin(str(update.effective_user.id))

        help_text = (
            "הנה רשימת הפקודות הזמינות:\n\n"
            "📊 פקודות כלליות:\n"
            "/stocks - הצגת רשימת המניות המוכרות\n"
            "/usage - הצגת נתוני שימוש ועלויות\n"
            "/help - הצגת עזרה זו\n"
        )

        if is_admin:
            help_text += (
                "\n👑 פקודות מנהל:\n"
                "/addstock שם-המניה SYMBOL - הוספת מניה חדשה\n"
                "/removestock שם-המניה - הסרת מניה מהרשימה\n"
                "/admin - ניהול משתמשים\n"
            )

        await update.message.reply_text(help_text)
    async def usage_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        הצגת נתוני שימוש למשתמש
        """
        if not self.security.is_user_allowed(str(update.effective_user.id)):
            await update.message.reply_text("מצטערת, אין לך הרשאה להשתמש בבוט זה.")
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

        if not self.security.is_user_allowed(user_id):
            await update.message.reply_text("מצטערת, אין לך הרשאה להשתמש בבוט זה.")
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
            await update.message.reply_text(f"מצטערת, נתקלתי בשגיאה: {str(e)}")
    async def prepare_analysis(self, update: Update, context: ContextTypes.DEFAULT_TYPE, ticker: str, question: str):
        try:
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

            input_tokens = self.analyzer.cost_calculator.estimate_tokens(prompt)
            cost_estimate = self.analyzer.cost_calculator.calculate_cost(input_tokens)

            can_request, message = self.security.can_make_request(
                str(update.effective_user.id),
                cost_estimate['total_cost']
            )

            if not can_request:
                await update.message.reply_text(f"❌ {message}")
                return

            context.user_data['pending_analysis'] = {
                'prompt': prompt,
                'cost_estimate': cost_estimate
            }
            context.user_data['awaiting_confirmation'] = True

            usage = self.security.get_user_usage(str(update.effective_user.id))

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
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.security.is_user_admin(str(update.effective_user.id)):
            await update.message.reply_text("מצטערתת, אין לך הרשאה לבצע פעולה זו.")
            return
        if not context.args:
            await update.message.reply_text("אנא ציין פעולה לביצוע.")
            return
        command = context.args[0]
        if command == 'add':
            if len(context.args) < 2:
                await update.message.reply_text("אנא ציין את המשתמש שברצונך להוסיף.")
                return
            user_id = context.args[1]
            if self.security.add_user(user_id, str(update.effective_user.id)):
                await update.message.reply_text(f"המשתמש {user_id} הוסף בהצלחה.")
            else:
                await update.message.reply_text(f"המשתמש {user_id} כבר קיים ברשימת המשתמשים.")
        elif command == 'remove':
            if len(context.args) < 2:
                await update.message.reply_text("אנא ציין את המשתמש שברצונך להסיר.")
                return
            user_id = context.args[1]
            if self.security.remove_user(user_id, str(update.effective_user.id)):
                await update.message.reply_text(f"המשתמש {user_id} הוסר בהצלחה.")
            else:
                await update.message.reply_text(f"המשתמש {user_id} לא נמצא ברשימת המשתמשים.")
        else:
            await update.message.reply_text(f" הפקודה {command}עדיין לא נתמכת.")
    async def stocks_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        הצגת רשימת המניות המוכרות
        """
        if not self.security.is_user_allowed(str(update.effective_user.id)):
            await update.message.reply_text("מצטערת, אין לך הרשאה להשתמש בבוט זה.")
            return

        stocks_list = self.analyzer.stock_manager.get_all_stocks()
        await update.message.reply_text(stocks_list)

    async def add_stock_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        הוספת מניה חדשה
        """
        if not self.security.is_user_admin(str(update.effective_user.id)):
            await update.message.reply_text("רק מנהלים יכולים להוסיף מניות חדשות.")
            return

        try:
            # הפורמט צריך להיות: /addstock שם מניה SYMBOL
            # לדוגמה: /addstock גוגל GOOGL
            name = " ".join(context.args[:-1])
            symbol = context.args[-1]

            if not name or not symbol:
                raise IndexError

            success, message = self.analyzer.stock_manager.add_stock(name, symbol)
            await update.message.reply_text(message)

        except IndexError:
            await update.message.reply_text(
                "שימוש שגוי. הפורמט הנכון הוא:\n"
                "/addstock שם-המניה SYMBOL\n"
                "לדוגמה: /addstock גוגל GOOGL"
            )

    async def remove_stock_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        הסרת מניה מהרשימה
        """
        if not self.security.is_admin(str(update.effective_user.id)):
            await update.message.reply_text("רק מנהלים יכולים להסיר מניות.")
            return

        try:
            name = " ".join(context.args)
            if not name:
                raise IndexError

            success, message = self.analyzer.stock_manager.remove_stock(name)
            await update.message.reply_text(message)

        except IndexError:
            await update.message.reply_text(
                "שימוש שגוי. הפורמט הנכון הוא:\n"
                "/removestock שם-המניה\n"
                "לדוגמה: /removestock גוגל"
            )
    
    def run(self):
        """
        הפעלת הבוט
        """
        self.application.run_polling()
def load_environment():
    """
    טעינת משתני הסביבה מקובץ .env
    """
    env_path = Path('.') / '.env'
    load_dotenv(dotenv_path=env_path)

    required_vars = [
        'TELEGRAM_TOKEN',
        'AZURE_API_KEY',
        'ALPHA_VANTAGE_KEY'
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}\n"
            f"Please check your .env file"
        )

    return {
        'telegram_token': os.getenv('TELEGRAM_TOKEN'),
        'azure_api_key': os.getenv('AZURE_API_KEY'),
        'alpha_vantage_key': os.getenv('ALPHA_VANTAGE_KEY'),
        'allowed_users': os.getenv('ALLOWED_USERS', '').split(','),
        'daily_cost_limit': float(os.getenv('DAILY_COST_LIMIT', '1.0')),
        'max_request_cost': float(os.getenv('MAX_REQUEST_COST', '0.1'))
    }

def main():
    try:
        env = load_environment()
        
        bot = StockNewsTelegramBot(
            telegram_token=env['telegram_token'],
            azure_api_key=env['azure_api_key'],
            alpha_vantage_key=env['alpha_vantage_key']
        )
        
        print("הבוט מופעל! 🚀")
        bot.run()
        
    except Exception as e:
        print(f"שגיאה בהפעלת הבוט: {e}")
        raise
