from typing import Dict, Optional, Tuple
import os
import json
import yfinance as yf

class StockListManager:
    def __init__(self, config_file: str = "settings/stocks_config.json"):
        self.config_file = config_file
        self.stocks = self._load_stocks()

    def _load_stocks(self) -> Dict[str, str]:
        """
        טעינת רשימת המניות מהקובץ
        """
        default_stocks = {
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
            "פרוקטר אנד גמבל": "PG",
            "פרוקטר & גמבל": "PG",
            "וולגרינס": "WBA",
            "וול-גרינס": "WBA",
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
            "דיסני": "DIS",
            "טראמפ": "DJT"
        }

        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return default_stocks
        except Exception as e:
            print(f"שגיאה בטעינת רשימת המניות: {e}")
            return default_stocks

    def save_stocks(self):
        """
        שמירת רשימת המניות לקובץ
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.stocks, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"שגיאה בשמירת רשימת המניות: {e}")

    def add_stock(self, name: str, symbol: str) ->  Tuple[bool, str]:
        """
        הוספת מניה חדשה
        """
        name = name.strip()
        symbol = symbol.strip().upper()

        # בדיקת תקינות הסימול באמצעות yfinance
        try:
            stock = yf.Ticker(symbol)
            # בדיקה בסיסית שהמניה קיימת
            if stock.info.get('regularMarketPrice') is None:
                return False, "סימול המניה לא נמצא"
        except Exception:
            return False, "סימול המניה לא תקין"

        self.stocks[name] = symbol
        self.save_stocks()
        return True, f"המניה {name} ({symbol}) נוספה בהצלחה"

    def remove_stock(self, name: str) -> Tuple[bool, str]:
        """
        הסרת מניה מהרשימה
        """
        if name in self.stocks:
            symbol = self.stocks.pop(name)
            self.save_stocks()
            return True, f"המניה {name} ({symbol}) הוסרה בהצלחה"
        return False, "המניה לא נמצאה ברשימה"

    def get_all_stocks(self) -> str:
        """
        קבלת רשימת כל המניות המוכרות
        """
        if not self.stocks:
            return "אין מניות ברשימה"

        stocks_list = ["רשימת המניות המוכרות:"]
        for name, symbol in sorted(self.stocks.items()):
            stocks_list.append(f"• {name}: {symbol}")
        return "\n".join(stocks_list)

    def get_ticker(self, text: str) -> Optional[str]:
        """
        חיפוש סימול מניה בטקסט
        """
        text = text.lower()
        for name, symbol in self.stocks.items():
            if name.lower() in text or symbol.lower() in text:
                return symbol
        return None


