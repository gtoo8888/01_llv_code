from pydantic import BaseModel
from typing import List, Optional
from datetime import date

# 理财计算请求
class CalculateRequest(BaseModel):
    principal: float
    start_date: str
    end_date: str
    income_start: float
    income_end: float

# 理财记录响应
class RecordResponse(BaseModel):
    id: int
    principal: float
    start_date: str
    end_date: str
    income_start: float
    income_end: float
    days: int
    total_income: float
    daily_income: float
    daily_income_per_10k: float
    annual_return: float

    class Config:
        from_attributes = True

# 指数行情数据项
class IndexQuoteItem(BaseModel):
    order: int
    code: str
    name: str
    current: Optional[float] = None
    change: Optional[float] = None
    changeAmt: Optional[float] = None
    volume: Optional[float] = None

# 指数行情响应
class IndexQuoteResponse(BaseModel):
    data: List[IndexQuoteItem]
    updateTime: str

# 指数行情列表（带缓存）
class IndexQuoteCachedResponse(BaseModel):
    data: List[IndexQuoteItem]
    updateTime: Optional[str] = None
    message: Optional[str] = None

# 进度响应
class ProgressResponse(BaseModel):
    total: int
    current: int
    status: str
    message: str
    percent: int
