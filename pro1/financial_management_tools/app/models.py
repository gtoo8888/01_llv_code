from sqlalchemy import Column, Integer, Float, String, Date, DateTime
from sqlalchemy.ext.declarative import declarative_base
from .database import engine

Base = declarative_base()

# 理财收益记录模型
class Record(Base):
    __tablename__ = "records"
    id = Column(Integer, primary_key=True, index=True)
    principal = Column(Float)      # 持仓/本金
    start_date = Column(Date)       # 开始日期
    end_date = Column(Date)         # 结束日期
    income_start = Column(Float)    # 收益开始
    income_end = Column(Float)      # 收益结束
    days = Column(Integer)          # 天数
    total_income = Column(Float)    # 总收益
    daily_income = Column(Float)    # 每天收益
    daily_income_per_10k = Column(Float)  # 每天万份收益
    annual_return = Column(Float)    # 年化收益

# 指数行情模型
class IndexQuote(Base):
    __tablename__ = "index_quotes"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, index=True)      # 指数代码
    name = Column(String)                  # 指数名称
    current = Column(Float)                 # 当前点位
    change = Column(Float)                 # 涨跌幅(%)
    change_amt = Column(Float)              # 涨跌额
    volume = Column(Float)                 # 成交额(亿)
    quote_date = Column(Date, index=True)  # 行情日期
    update_time = Column(DateTime)         # 更新时间

# 创建表
Base.metadata.create_all(bind=engine)
