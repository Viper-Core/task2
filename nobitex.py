import sqlite3
import requests
import re
from datetime import datetime
import matplotlib.pyplot as plt

LOG_FILE = "price_alerts.log"


def get_price(src, dst):
    url = "https://apiv2.nobitex.ir/market/stats"
    payload = {"srcCurrency": src, "dstCurrency": dst}
    response = requests.post(url, json=payload)
    raw_text = response.text

    symbol = f"{src}-{dst}"
    pattern = fr'"{symbol}":{{.*?"latest":\s*"([^"]+)"'
    match = re.search(pattern, raw_text)
    return match.group(1) if match else None


def init_db():
    conn = sqlite3.connect("prices.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            currency_name TEXT,
            symbol TEXT,
            price REAL,
            unit TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    return conn


def save_price(conn, currency_name, symbol, price, unit):
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO prices (currency_name, symbol, price, unit, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (currency_name, symbol, price, unit, now_str))
    conn.commit()


def get_max_price(conn, symbol):
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(price) FROM prices WHERE symbol = ?", (symbol,))
    result = cursor.fetchone()
    return result[0] if result else None


def get_min_price(conn, symbol):
    cursor = conn.cursor()
    cursor.execute("SELECT MIN(price) FROM prices WHERE symbol = ?", (symbol,))
    result = cursor.fetchone()
    return result[0] if result else None


def get_avg_price(conn, symbol):
    cursor = conn.cursor()
    cursor.execute("SELECT AVG(price) FROM prices WHERE symbol = ?", (symbol,))
    result = cursor.fetchone()
    return result[0] if result else None


def get_percent_change(conn, symbol):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT price FROM prices
        WHERE symbol = ?
        ORDER BY id DESC
        LIMIT 2
    """, (symbol,))
    rows = cursor.fetchall()

    if len(rows) < 2:
        return None

    current_price = rows[0][0]
    previous_price = rows[1][0]

    if previous_price == 0:
        return None

    change = ((current_price - previous_price) / previous_price) * 100
    return change


def print_stats(conn, currency_name, symbol, unit):
    max_p = get_max_price(conn, symbol)
    min_p = get_min_price(conn, symbol)
    avg_p = get_avg_price(conn, symbol)
    change = get_percent_change(conn, symbol)

    print(f"\n📊 آمار {currency_name} ({symbol}):")
    print(f"   بیشترین: {max_p:,.2f} {unit}")
    print(f"   کمترین: {min_p:,.2f} {unit}")
    print(f"   میانگین: {avg_p:,.2f} {unit}")

    if change is not None:
        arrow = "🔺" if change > 0 else "🔻" if change < 0 else "➖"
        print(f"   تغییر نسبت به قیمت قبلی: {arrow} {change:.2f}٪")
    else:
        print("   تغییر: هنوز داده‌ی قبلی کافی نیست (حداقل دوبار باید اجرا بشه)")

    return change


def log_big_change(currency_name, symbol, change, unit):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    direction = "افزایش" if change > 0 else "کاهش"

    message = (
        f"[{now_str}] هشدار: قیمت {currency_name} ({symbol}) "
        f"{direction} {abs(change):.2f}٪ داشت (بیش از حد آستانه‌ی ۱٪)\n"
    )

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(message)

    print(f"⚠️  {message.strip()}")


def plot_price_history(conn, currency_name, symbol, unit):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT price, timestamp FROM prices
        WHERE symbol = ?
        ORDER BY id ASC
    """, (symbol,))
    rows = cursor.fetchall()

    if len(rows) < 2:
        print(f"⚠️ داده‌ی کافی برای رسم نمودار {currency_name} نیست")
        return

    prices = [row[0] for row in rows]
    timestamps = [row[1] for row in rows]

    plt.figure(figsize=(10, 5))
    plt.plot(timestamps, prices, marker="o", color="royalblue")
    plt.title(f"Price history: {currency_name} ({symbol})")
    plt.xlabel("Time")
    plt.ylabel(f"Price ({unit})")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.grid(True, alpha=0.3)
    plt.show()


def get_prices_and_save():
    conn = init_db()
    try:
        usdt_rls = get_price("usdt", "rls")
        btc_usdt = get_price("btc", "usdt")
        eth_usdt = get_price("eth", "usdt")

        usdt_toman = int(int(usdt_rls) / 10)
        btc_usdt_f = float(btc_usdt)
        eth_usdt_f = float(eth_usdt)

        print(f"💵 دلار: {usdt_toman:,} تومان")
        print(f"₿ بیت‌کوین: {btc_usdt_f:,} دلار")
        print(f"Ξ اتریوم: {eth_usdt_f:,} دلار")

        save_price(conn, "دلار", "usdt-rls", usdt_toman, "تومان")
        save_price(conn, "بیت‌کوین", "btc-usdt", btc_usdt_f, "دلار")
        save_price(conn, "اتریوم", "eth-usdt", eth_usdt_f, "دلار")

        print("✅ ذخیره شد در دیتابیس")

        currencies = [
            ("دلار", "usdt-rls", "تومان"),
            ("بیت‌کوین", "btc-usdt", "دلار"),
            ("اتریوم", "eth-usdt", "دلار"),
        ]

        for name, symbol, unit in currencies:
            change = print_stats(conn, name, symbol, unit)
            if change is not None and abs(change) > 1:
                log_big_change(name, symbol, change, unit)

        # for name, symbol, unit in currencies:
        #     plot_price_history(conn, name, symbol, unit)

    except Exception as e:
        print(f"❌ خطا: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    get_prices_and_save()