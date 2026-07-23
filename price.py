from fastapi import FastAPI, HTTPException, Query
import sqlite3
from fastapi.responses import StreamingResponse
import matplotlib
matplotlib.use("Agg")  # برای اجرا بدون رابط گرافیکی (لازم چون تو سرور هستیم)
import matplotlib.pyplot as plt
import io
from typing import Optional

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





@app.get("/prices/{symbol}")
def get_price_history(symbol: str, page: int = 1, page_size: int = 20):
    if page < 1:
        raise HTTPException(status_code=400, detail="شماره صفحه باید حداقل ۱ باشه")
    if page_size < 1 or page_size > 100:
        raise HTTPException(status_code=400, detail="page_size باید بین ۱ تا ۱۰۰ باشه")

    offset = (page - 1) * page_size

    conn = sqlite3.connect("prices.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM prices WHERE symbol = ?", (symbol,))
    total_count = cursor.fetchone()[0]

    if total_count == 0:
        conn.close()
        raise HTTPException(status_code=404, detail=f"ارزی با نماد '{symbol}' پیدا نشد")

    cursor.execute("""
        SELECT price, timestamp FROM prices
        WHERE symbol = ?
        ORDER BY id DESC
        LIMIT ? OFFSET ?
    """, (symbol, page_size, offset))
    rows = cursor.fetchall()
    conn.close()

    history = []
    for row in rows:
        history.append({
            "price": row[0],
            "timestamp": row[1],
        })

    total_pages = (total_count + page_size - 1) // page_size

    return {
        "symbol": symbol,
        "page": page,
        "page_size": page_size,
        "total_items": total_count,
        "total_pages": total_pages,
        "history": history,
    }






@app.get("/prices/{symbol}/chart")
def get_price_chart(
    symbol: str,
    start: Optional[str] = Query(None, description="تاریخ شروع، فرمت: YYYY-MM-DD HH:MM:SS"),
    end: Optional[str] = Query(None, description="تاریخ پایان، فرمت: YYYY-MM-DD HH:MM:SS"),
):
    conn = sqlite3.connect("prices.db")
    cursor = conn.cursor()

    query = "SELECT price, timestamp FROM prices WHERE symbol = ?"
    params = [symbol]

    if start:
        query += " AND timestamp >= ?"
        params.append(start)

    if end:
        query += " AND timestamp <= ?"
        params.append(end)

    query += " ORDER BY id ASC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    if len(rows) < 2:
        raise HTTPException(status_code=404, detail="داده‌ی کافی برای رسم نمودار این ارز (با این فیلتر) وجود نداره")

    prices = [row[0] for row in rows]
    timestamps = [row[1] for row in rows]

    plt.figure(figsize=(10, 5))
    plt.plot(timestamps, prices, marker="o", color="royalblue")
    plt.title(f"Price history: {symbol}")
    plt.xlabel("Time")
    plt.ylabel("Price")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.grid(True, alpha=0.3)

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    plt.close()
    buffer.seek(0)

    return StreamingResponse(buffer, media_type="image/png")