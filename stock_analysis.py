import ta 
import requests
from fastapi import FastAPI
from datetime import datetime, timedelta
import pandas as pd

app = FastAPI()

@app.get("/stock/analysis/{stockNo}")
def analysis(stockNo: str):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        all_rows = []
        for i in range(6):
            date = datetime.now() - timedelta(days=30 * i)
            date_str = date.strftime("%Y%m%d")
            url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date_str}&stockNo={stockNo}"
            res = requests.get(url, headers=headers, timeout=30)
            data = res.json()
            if "data" in data:
                all_rows.extend(data["data"])

        # 整理成 DataFrame
        df = pd.DataFrame({
            "high":   [float(r[4].replace(",", "")) for r in all_rows],
            "low":    [float(r[5].replace(",", "")) for r in all_rows],
            "close":  [float(r[6].replace(",", "")) for r in all_rows],
            "volume": [float(r[1].replace(",", "")) for r in all_rows],
        })
        
        # 3. 用 ta 算指標
        df["MA5"]  = df["close"].rolling(5).mean()
        df["MA20"] = df["close"].rolling(20).mean()
        df["RSI"]  = ta.momentum.RSIIndicator(df["close"]).rsi()

        macd = ta.trend.MACD(df["close"])
        df["MACD"]   = macd.macd()
        df["Signal"] = macd.macd_signal()

        stoch = ta.momentum.StochasticOscillator(df["high"], df["low"], df["close"])
        df["K"] = stoch.stoch()
        df["D"] = stoch.stoch_signal()

        # 4. 取最後一天
        last = df.iloc[-1]

        return {
            "股票代號": stockNo,
            "MA5": round(last["MA5"], 2),
            "MA20": round(last["MA20"], 2),
            "RSI": round(last["RSI"], 2),
            "MACD": round(last["MACD"], 2),
            "Signal": round(last["Signal"], 2),
            "K": round(last["K"], 2),
            "D": round(last["D"], 2),
            "成交量": int(last["volume"]),
        }

    except Exception as e:
        return {"error": f"查無資料：{str(e)}"}