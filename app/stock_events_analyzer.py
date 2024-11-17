from datetime import timedelta
from typing import Optional

import pandas as pd
import yfinance as yf

class StockEventsAnalyzer:
    def __init__(self):
        """
        מנהל אירועי מניות - earnings ודיבידנדים
        """
        self.cache = {}  # Cache for storing recent queries
        self.cache_duration = timedelta(hours=1)  # Cache duration

    def _format_date(self, date) -> str:
        """
        פורמט תאריך לתצוגה נוחה בעברית
        """
        if pd.isnull(date):
            return "לא ידוע"

        try:
            if isinstance(date, str):
                date = pd.to_datetime(date)

            months_he = {
                1: 'ינואר', 2: 'פברואר', 3: 'מרץ', 4: 'אפריל',
                5: 'מאי', 6: 'יוני', 7: 'יולי', 8: 'אוגוסט',
                9: 'ספטמבר', 10: 'אוקטובר', 11: 'נובמבר', 12: 'דצמבר'
            }

            return f"{date.day} ב{months_he[date.month]} {date.year}"
        except:
            return "תאריך לא תקין"

    async def get_earnings_info(self, ticker: str) -> str:
        """
        קבלת מידע על earnings
        """
        try:
            stock = yf.Ticker(ticker)

            # קבלת מידע על earnings
            calendar = stock.calendar
            earnings_history = stock.earnings_dates.sort_index(ascending=False)[:4]  # 4 תקופות אחרונות

            # בניית התשובה
            response = [f"📊 מידע על Earnings עבור {stock.info.get('longName', ticker)}:"]
            calendar = pd.DataFrame.from_dict(calendar)
            # תאריך ה-earnings הבא
            if calendar is not None and not calendar.empty:
                next_earnings = calendar.iloc[0]['Earnings Date']
                response.append(f"\n📅 Earnings הבא: {self._format_date(next_earnings)}")

            # היסטוריית earnings
            if not earnings_history.empty:
                response.append("\n📈 היסטוריית Earnings אחרונה:")
                for date, row in earnings_history.iterrows():
                    actual = row.get('Reported EPS', 'N/A')
                    estimate = row.get('EPS Estimate', 'N/A')
                    surprise = row.get('Surprise(%)', 'N/A')

                    surprise = round(surprise,3)

                    response.append(
                        f"• {self._format_date(date)}:\n"
                        f"  ▫️ EPS בפועל: ${actual}\n"
                        f"  ▫️ EPS צפי: ${estimate}\n"
                        f"  ▫️ הפתעה: {surprise}\n"
                    )

            return "\n".join(response)

        except Exception as e:
            print(f"שגיאה בקבלת מידע על earnings: {e}")
            return f"לא הצלחתי למצוא מידע על earnings עבור {ticker}"

    async def get_dividend_info(self, ticker: str) -> str:
        """
        קבלת מידע על דיבידנדים
        """
        try:
            stock = yf.Ticker(ticker)

            dividends = stock.dividends.sort_index(ascending=False)
            dividend_info = stock.info

            response = [f"💰 מידע על דיבידנדים עבור {stock.info.get('longName', ticker)}:"]

            dividend_rate = dividend_info.get('dividendRate', None)
            dividend_yield = dividend_info.get('dividendYield', None)
            ex_dividend_date = dividend_info.get('exDividendDate', None)

            if dividend_rate:
                response.append(f"\nדיבידנד שנתי: ${dividend_rate:.2f}")

            if dividend_yield:
                response.append(f"תשואת דיבידנד: {dividend_yield * 100:.2f}%")

            if ex_dividend_date:
                response.append(f"תאריך האקס האחרון: {self._format_date(ex_dividend_date)}")

            if not dividends.empty:
                response.append("\n📅 היסטוריית דיבידנדים אחרונה:")
                for date, amount in dividends.head(5).items():
                    response.append(f"• {self._format_date(date)}: ${amount:.3f}")

                yearly_growth = self._calculate_dividend_growth(dividends)
                if yearly_growth:
                    response.append(f"\n📈 צמיחה שנתית ממוצעת: {yearly_growth:.1f}%")
            else:
                response.append("\nהחברה לא מחלקת דיבידנדים כרגע.")

            return "\n".join(response)

        except Exception as e:
            print(f"שגיאה בקבלת מידע על דיבידנדים: {e}")
            return f"לא הצלחתי למצוא מידע על דיבידנדים עבור {ticker}"

    def _calculate_dividend_growth(self, dividends) -> Optional[float]:
        """
        חישוב צמיחת הדיבידנד השנתית הממוצעת
        """
        try:
            # מקבץ לפי שנים
            yearly_dividends = dividends.groupby(pd.Grouper(freq='Y')).sum()

            if len(yearly_dividends) < 2:
                return None

            # לוקח את השנים האחרונות בהן היו דיבידנדים
            start_value = yearly_dividends[-2]  # שנה קודמת
            end_value = yearly_dividends[-1]  # שנה נוכחית

            if start_value <= 0:
                return None

            growth = ((end_value / start_value) - 1) * 100
            return growth

        except Exception:
            return None
