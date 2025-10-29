from typing import List

from pydantic import BaseModel, Field, validator
from datetime import datetime


# pydantic model to represent stock analysis data
class StockAnalysisData(BaseModel):
    stock_name: str
    stock_code: str
    market: str
    buy_price: float
    target_price_daily: float
    target_price_weekly: float
    stop_loss: float
    analysis_date_time: datetime
    analysis: str

    @validator("analysis_date_time", pre=True, always=True)
    def parse_analysis_date_time(cls, value):
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return value

class StockAnalysisDataList(BaseModel):
    stocks: List[StockAnalysisData] = Field(description="List of stock analysis data")

# pydantic model to represent stock market analysis data in the database
class StockClosingPrice(BaseModel):
    stock_name: str
    stock_code: str
    day_end_price: float
    analysis_date: datetime

class StockClosingPriceList(BaseModel):
    closing_prices: List[StockClosingPrice] = Field(description="List of stock closing prices")