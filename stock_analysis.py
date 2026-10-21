import time

import ta
import requests
import pandas as pd
from fastapi import FastAPI, HTTPException, Path
from fastapi.staticfiles import StaticFiles

from datetime import datetime, timedelta
from pydantic import BaseModel


app = FastAPI(
    title="台股技術分析 API",
    description="串接 TWSE 公開資料，計算個股技術指標（MA、RSI、MACD、KD）",
    version="1.0.0",
)


class StockAnalysisResponse(BaseModel):
    股票代號: str
    收盤價: float
    MA5: float
    MA20: float
    RSI: float
    MACD: float
    Signal: float
    K: float
    D: float
    成交量: int


@app.get(
    "/stock/analysis/{stock_no}",
    response_model=StockAnalysisResponse,
    summary="取得個股技術分析指標",
    description="輸入台股代號（如 2330），回傳近半年數據計算出的技術指標",
)
def analysis(
    stock_no: str = Path(pattern=r"^\d{4,6}$", description="台股代號，例如 2330"),
):
    headers = {"User-Agent": "Mozilla/5.0"}
    all_rows = []

    for i in range(6):
        date = datetime.now() - timedelta(days=30 * i)
        date_str = date.strftime("%Y%m%d")
        url = (
            f"https://www.twse.com.tw/exchangeReport/STOCK_DAY"
            f"?response=json&date={date_str}&stockNo={stock_no}"
        )
        res = requests.get(url, headers=headers, timeout=30)

        if res.status_code != 200:
            raise HTTPException(status_code=502, detail="TWSE API 無回應")

        data = res.json()
        if "data" in data:
            all_rows.extend(data["data"])

        time.sleep(0.3)

    if not all_rows:
        raise HTTPException(status_code=404, detail=f"查無股票 {stock_no} 的資料")

    df = pd.DataFrame({
        "high":   [float(r[4].replace(",", "")) for r in all_rows],
        "low":    [float(r[5].replace(",", "")) for r in all_rows],
        "close":  [float(r[6].replace(",", "")) for r in all_rows],
        "volume": [float(r[1].replace(",", "")) for r in all_rows],
    })

    df["MA5"]  = df["close"].rolling(5).mean()
    df["MA20"] = df["close"].rolling(20).mean()
    df["RSI"]  = ta.momentum.RSIIndicator(df["close"]).rsi()

    macd = ta.trend.MACD(df["close"])
    df["MACD"]   = macd.macd()
    df["Signal"] = macd.macd_signal()

    stoch = ta.momentum.StochasticOscillator(df["high"], df["low"], df["close"])
    df["K"] = stoch.stoch()
    df["D"] = stoch.stoch_signal()

    last = df.iloc[-1]

    return StockAnalysisResponse(
        股票代號=stock_no,
        收盤價=round(last["close"], 2),
        MA5=round(last["MA5"], 2),
        MA20=round(last["MA20"], 2),
        RSI=round(last["RSI"], 2),
        MACD=round(last["MACD"], 2),
        Signal=round(last["Signal"], 2),
        K=round(last["K"], 2),
        D=round(last["D"], 2),
        成交量=int(last["volume"]),
    )


app.mount("/", StaticFiles(directory="static", html=True), name="static")
