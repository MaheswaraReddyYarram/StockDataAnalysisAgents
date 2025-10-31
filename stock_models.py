from typing import List

from pydantic import BaseModel, Field, validator
from datetime import date


# pydantic model to represent stock analysis data
class StockAnalysisData(BaseModel):
    stock_name: str
    stock_code: str
    market: str
    buy_price: float
    target_price_daily: float
    target_price_weekly: float
    stop_loss: float
    analysis_date: date
    analysis: str
    day_end_price: float


class StockAnalysisDataList(BaseModel):
    stocks: List[StockAnalysisData] = Field(description="List of stock analysis data")

# pydantic model to represent stock market analysis data in the database
class StockClosingPrice(BaseModel):
    stock_name: str
    stock_code: str
    day_end_price: float
    analysis_date: date

class StockClosingPriceList(BaseModel):
    closing_prices: List[StockClosingPrice] = Field(description="List of stock closing prices")