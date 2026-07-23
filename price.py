from fastapi import FastAPI
import sqlite3

app = FastAPI()


@app.get("/prices")
def get_all_prices():
    conn = sqlite3.connect("prices.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT currency_name, symbol, price, unit, timestamp
        FROM prices
        WHERE id IN (
            SELECT MAX(id) FROM prices GROUP BY symbol
        )
    """)
    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        result.append({
            "currency_name": row[0],
            "symbol": row[1],
            "price": row[2],
            "unit": row[3],
            "timestamp": row[4],
        })

    return {"prices": result}