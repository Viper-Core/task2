import sqlite3

conn = sqlite3.connect("prices.db")
cursor = conn.cursor()
cursor.execute("SELECT * FROM prices ORDER BY id DESC LIMIT 10")
for row in cursor.fetchall():
    id_, name, symbol, price, unit, ts = row
    print(f"{name} ({symbol}): {price:,} {unit} — {ts}")
conn.close()