from openai import AzureOpenAI
from telegram import Update
from cost_calculator import CostCalculator
from typing import List, Dict, Union
import requests
import yfinance as yf
from telegram.ext import ContextTypes

class StockNewsAnalyzer:
    def __init__(self, azure_api_key: str, alpha_vantage_key: str, azure_endpoint: str = "https://stockybot.openai.azure.com/"):
        self.client = AzureOpenAI(
            api_key=azure_api_key,
            api_version="2024-02-15-preview",
            azure_endpoint=azure_endpoint
        )
        self.alpha_vantage_key = alpha_vantage_key
        self.cost_calculator = CostCalculator()

    def get_stock_info(self, ticker: str) -> Dict:
        """
        קבלת מידע בסיסי על המניה באמצעות yfinance
        """
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            "name": info.get("longName", ticker),
            "current_price": info.get("currentPrice"),
            "previous_close": info.get("previousClose"),
            "percent_change": info.get("regularMarketChangePercent")
        }

    def fetch_news(self, ticker: str) -> List[Dict]:
        """
        הבאת חדשות באמצעות Alpha Vantage API
        """
        try:
            # קבלת חדשות מ-Alpha Vantage
            url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&apikey={self.alpha_vantage_key}"
            response = requests.get(url)
            data = response.json()

            news_items = []
            if "feed" in data:
                for item in data["feed"][:5]:  # לוקח את 5 החדשות האחרונות
                    news_items.append({
                        "title": item.get("title", ""),
                        "summary": item.get("summary", ""),
                        "source": item.get("source", ""),
                        "url": item.get("url", ""),
                        "sentiment": item.get("overall_sentiment_score", 0),
                        "time": item.get("time_published", "")
                    })

            return news_items
        except Exception as e:
            print(f"שגיאה בהבאת חדשות: {e}")
            return []

    async def analyze_stock_movement(self, ticker: str, question: str, update: Update) -> Dict[
        str, Dict[str, Union[str, dict]]]:
        """
        ניתוח תנועת המניה והחדשות הרלוונטיות עם חישוב עלויות
        """
        try:
            # קבלת מידע על המניה
            stock_info = self.get_stock_info(ticker)
            news = self.fetch_news(ticker)

            # הכנת הטקסט לשליחה
            context = f"""
מידע על המניה {stock_info['name']} ({ticker}):
- מחיר נוכחי: ${stock_info['current_price']}
- שינוי באחוזים: {stock_info['percent_change']}%

חדשות אחרונות:
"""
            for item in news:
                context += f"""
- {item['title']}
  מקור: {item['source']}
  תקציר: {item['summary'][:200]}...
"""

            prompt = f"""בהתבסס על המידע הבא, אנא ענה על השאלה: "{question}"

{context}

אנא תן תשובה מקיפה בעברית שמסבירה את המצב בצורה ברורה."""

            # חישוב עלות משוערת
            input_tokens = self.cost_calculator.estimate_tokens(prompt)
            cost_estimate = self.cost_calculator.calculate_cost(input_tokens)

            # בקשת אישור מהמשתמש
            confirmation_message = (
                f"📊 הערכת עלויות:\n"
                f"• טוקנים בשאילתה: {cost_estimate['input_tokens']:,}\n"
                f"• טוקנים משוערים בתשובה: {cost_estimate['output_tokens']:,}\n"
                f"• עלות משוערת: ${cost_estimate['total_cost']:.4f}\n\n"
                f"האם להמשיך עם הניתוח? (כן/לא)"
            )

            # שליחת הודעת אישור למשתמש
            await update.message.reply_text(confirmation_message)
        finally:
            return {'pending_analysis': {'prompt': prompt,'cost_estimate': cost_estimate}}
    async def process_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        עיבוד תשובת המשתמש וביצוע הניתוח אם אושר
        """
        if not hasattr(context.user_data, 'pending_analysis'):
            await update.message.reply_text("אין ניתוח ממתין. אנא שאל שאלה חדשה.")
            return

        response_text = update.message.text.lower()
        if response_text in ['כן', 'yes', 'y', 'כ']:
            try:
                # שליחת הודעת "מעבד..."
                processing_message = await update.message.reply_text("מעבד את הבקשה... ⏳")

                # שליחה ל-Azure OpenAI
                response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "אתה אנליסט פיננסי מומחה שמנתח מניות ומסביר מגמות בשוק ההון בעברית ברורה."},
                        {"role": "user", "content": context.user_data['pending_analysis']['prompt']}
                    ]
                )

                # חישוב העלות בפועל
                actual_tokens = {
                    'input': response.usage.prompt_tokens,
                    'output': response.usage.completion_tokens
                }
                actual_cost = self.cost_calculator.calculate_cost(
                    actual_tokens['input'],
                    actual_tokens['output']
                )

                # הכנת התשובה עם פירוט העלויות
                answer = response.choices[0].message.content
                cost_summary = (
                    f"\n\n💰 סיכום עלויות בפועל:\n"
                    f"• טוקנים בשאילתה: {actual_tokens['input']:,}\n"
                    f"• טוקנים בתשובה: {actual_tokens['output']:,}\n"
                    f"• עלות כוללת: ${actual_cost['total_cost']:.4f}"
                )

                # עדכון ההודעה עם התשובה והעלויות
                await processing_message.edit_text(f"{answer}{cost_summary}")

            except Exception as e:
                await processing_message.edit_text(f"התרחשה שגיאה בניתוח: {str(e)}")

        else:
            await update.message.reply_text("הניתוח בוטל.")

        # ניקוי המידע השמור
        del context.user_data['pending_analysis']

    def get_ticker_from_text(self, text: str) -> str:
        common_tickers = {
            "abbvie": "ABBV",
            "אפל": "AAPL",
            "מיקרוסופט": "MSFT",
            "טסלה": "TSLA",
            "מטא": "META",
            "אמזון": "AMZN",
            "נפטון": "NEPT",
            "ניורון": "NUR",
            "פייזר": "PFE",
            "גוגל": "GOOGL",
            "אלפאבט": "GOOGL",
            "אלפאביט": "GOOGL",
            "פייסבוק": "META",
            "מטה": "META",
            "טוויטר": "TWTR",
            "טיקטוק": "TICK",
            "נייק": "NKE",
            "נייקי": "NKE",
            "קוקה קולה": "KO",
            "קוקה-קולה": "KO",
            "וולמארט": "WMT",
            "וול-מארט": "WMT",
            "נטפליקס": "NFLX",
            "בנק אוף אמריקה": "BAC",
            "בנק אוף אמריקה": "BAC",
            "פרוקטר אנד גמבל": "PG",
            "פרוקטר & גמבל": "PG",
            "וולגרינס": "WBA",
            "וול-גרינס": "WBA",
            "יונייטד הלת'קר": "UNH",
            "יונייטד הלת'קר": "UNH",
            "נבידיה": "NVDA",
            "אנבידיה": "NVDA",
            "אינטל": "INTC",
            "קוואלקום": "QCOM",
            "מודרנה": "MRNA",
            "ביונטק": "BNTX",
            "אסטרהזניקה": "AZN",
            "ג'ונסון & ג'ונסון": "JNJ",
            "יוניון פסיפיק": "UNP",
            "מקדונלדס": "MCD",
            "סטארבקס": "SBUX",
            "לוקהיד מרטין": "LMT",
            "רייטיאון": "RTX",
            "טארגט": "TGT",
            "סוני": "SONY",
            "ריביאן": "RIVN",
            "פייזר": "PFE",
            "בואינג": "BA",
            "שברון": "CVX",
            "ברקשייר האת'ווי": "BRK.A",
            "ברקשייר": "BRK.B",
            "ביונדו": "BIDU",
            "זום": "ZM",
            "אובר": "UBER",
            "ליפט": "LYFT",
            "שופיפיי": "SHOP",
            "סיילספורס": "CRM",
            "בלאק רוק": "BLK",
            "מודי'ס": "MCO",
            "ג'י פי מורגן": "JPM",
            "מורגן סטנלי": "MS",
            "ג'נרל אלקטריק": "GE",
            "פורד": "F",
            "טויוטה": "TM",
            "ניסאן": "NSANY",
            "פולקסווגן": "VWAGY",
            "הונדה": "HMC",
            "פיוטשר": "FUTR",
        }

        for company, symbol in common_tickers.items():
            if company.lower() in text.lower():
                return symbol
        return None