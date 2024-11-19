import yfinance as yf
import pandas as pd

class InstitutionalHoldingsAnalyzer:
    def __init__(self):
        """
        אנלייזר למחזיקים מוסדיים
        """
        self.last_update_cache = {}

    async def get_institutional_holdings(self, ticker: str) -> str:
        """
        קבלת מידע על מחזיקים מוסדיים
        """
        try:
            stock = yf.Ticker(ticker)
            
            # קבלת מידע בסיסי על המניה
            info = stock.info
            company_name = info.get('longName', ticker)
            if info.get('quoteType') != 'EQUITY':
                response = [f"📊 Top 10 holdings for {company_name}:"]
                for i, row in stock.funds_data.top_holdings.head(10).iterrows():
                    response.append(
                        f"• {row['Name']}\n"
                        f"  ├ אחוז מהתיק: {round(row['Holding Percent'] * 100, 2)}%\n"
                        f"  ├ סימבול: {i}")
            else:
                institutional_holders = stock.institutional_holders
                major_holders = stock.major_holders

                if institutional_holders is None or institutional_holders.empty:
                    return f"לא נמצא מידע על מחזיקים מוסדיים עבור {company_name}"

                total_institutional = None
                if major_holders is not None and not major_holders.empty:
                    for index, row in major_holders.iterrows():
                        if 'institution' in index.lower():
                            total_institutional = row[0]
                            break

                response = [f"🏢 מחזיקים מוסדיים ב{company_name}:"]

                if total_institutional:
                    response.append(f"\nסך החזקות מוסדיות: {major_holders.Value[1]}")

                institutional_holders = institutional_holders.sort_values(
                    by='Value',
                    ascending=False
                ).head(10)

                response.append("\nעשרת המחזיקים הגדולים:")

                for _, holder in institutional_holders.iterrows():
                    shares = "{:,}".format(int(holder['Shares']))
                    value = "${:,.2f}M".format(holder['Value'] / 1_000_000)
                    date = pd.to_datetime(holder['Date Reported']).strftime('%d/%m/%Y')

                    change = ""
                    if 'Change' in holder and not pd.isna(holder['Change']):
                        change_val = float(holder['Change'])
                        if change_val > 0:
                            change = f"📈 +{change_val:.1f}%"
                        elif change_val < 0:
                            change = f"📉 {change_val:.1f}%"

                    response.append(
                        f"\n• {holder['Holder']}\n"
                        f"  ├ מניות: {shares}\n"
                        f"  ├ שווי: {value}\n"
                        f"  ├ עדכון אחרון: {date}\n"
                        f"  └ {change if change else '♦️ ללא שינוי'}"
                    )

                total_shares = institutional_holders['Shares'].sum()
                total_value = institutional_holders['Value'].sum()

                response.append(
                    f"\n📊 סיכום עשרת המחזיקים הגדולים:"
                    f"\nסך מניות: {'{:,}'.format(int(total_shares))}"
                    f"\nשווי כולל: ${'{:,.2f}B'.format(total_value / 1_000_000_000)}"
                )

            return "\n".join(response)

        except Exception as e:
            print(f"Error getting institutional holdings: {e}")
            return f"שגיאה בקבלת מידע על מחזיקים מוסדיים: {str(e)}"

