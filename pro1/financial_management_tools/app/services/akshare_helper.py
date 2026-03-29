import akshare as ak
import pandas as pd
from datetime import date, timedelta
from typing import Dict, Optional
import time
import threading

# 指数列表（按指定顺序，symbol 用于 akshare 获取数据）
# 注意：中证红利(000922) 数据异常，暂返回空
INDICES_LIST = [
    { 'code': '000001', 'name': '上证指数', 'symbol': 'sh000001' },
    { 'code': '000016', 'name': '上证50', 'symbol': 'sh000016' },
    { 'code': '000300', 'name': '沪深300', 'symbol': 'sh000300' },
    { 'code': '000510', 'name': '中证A500', 'symbol': 'sh000510' },
    { 'code': '000688', 'name': '科创50', 'symbol': 'sh000688' },
    { 'code': '000905', 'name': '中证500', 'symbol': 'sh000905' },
    { 'code': '000922', 'name': '中证红利', 'symbol': 'sh000922', 'disabled': True },  # 数据异常
    { 'code': '399006', 'name': '创业板指', 'symbol': 'sz399006' },
    { 'code': '399673', 'name': '创业板50', 'symbol': 'sz399673' },
    { 'code': '930955', 'name': '红利低波100', 'symbol': 'sh000955', 'disabled': True },  # 暂不支持
]

# 进度跟踪
fetch_progress = {
    'total': len(INDICES_LIST),
    'current': 0,
    'status': 'idle',  # idle, fetching, completed, error
    'message': ''
}
fetch_lock = threading.Lock()

def get_index_data(symbol: str) -> Optional[Dict]:
    """获取单个指数数据（当天+前一天，用于计算涨跌幅）"""
    try:
        df = ak.stock_zh_index_daily(symbol=symbol)
        if df is None or len(df) < 2:
            return None
        
        # 取最后2条数据
        today = df.iloc[-1]
        yesterday = df.iloc[-2]
        
        close_today = today['close']
        close_yesterday = yesterday['close']
        
        # 计算涨跌幅
        change_amt = close_today - close_yesterday
        change_pct = (change_amt / close_yesterday) * 100
        
        # 成交量转换为亿（原始单位是股）
        volume = today['volume'] / 1e8
        
        return {
            'current': round(close_today, 2),
            'change': round(change_pct, 2),
            'changeAmt': round(change_amt, 2),
            'volume': round(volume, 0),
            'date': today['date'].strftime('%Y-%m-%d') if isinstance(today['date'], date) else str(today['date'])
        }
    except Exception as e:
        print(f"获取 {symbol} 失败: {e}")
        return None

def get_index_data_by_date(symbol: str, target_date: date) -> Optional[Dict]:
    """获取指定日期的指数数据（需要目标日期和前一天来计算涨跌幅）"""
    try:
        df = ak.stock_zh_index_daily(symbol=symbol)
        if df is None or len(df) < 2:
            return None
        
        # 将 date 列转换为日期类型进行匹配
        df['date'] = pd.to_datetime(df['date']).dt.date
        
        # 查找目标日期的数据
        target_rows = df[df['date'] == target_date]
        
        if len(target_rows) == 0:
            print(f"未找到 {symbol} 在 {target_date} 的数据")
            return None
        
        today = target_rows.iloc[-1]
        
        # 获取前一天的数据
        yesterday_date = target_date - timedelta(days=1)
        yesterday_rows = df[df['date'] == yesterday_date]
        
        if len(yesterday_rows) == 0:
            # 如果没有精确的前一天，尝试找前一个交易日
            available_dates = df[df['date'] < target_date]['date'].unique()
            if len(available_dates) > 0:
                yesterday_date = max(available_dates)
                yesterday_rows = df[df['date'] == yesterday_date]
            else:
                print(f"未找到 {symbol} 的前一天数据")
                return None
        
        yesterday = yesterday_rows.iloc[-1]
        
        close_today = today['close']
        close_yesterday = yesterday['close']
        
        # 计算涨跌幅
        change_amt = close_today - close_yesterday
        change_pct = (change_amt / close_yesterday) * 100
        
        # 成交量转换为亿（原始单位是股）
        volume = today['volume'] / 1e8
        
        return {
            'current': round(close_today, 2),
            'change': round(change_pct, 2),
            'changeAmt': round(change_amt, 2),
            'volume': round(volume, 0),
            'date': target_date.strftime('%Y-%m-%d')
        }
    except Exception as e:
        print(f"获取 {symbol} 在 {target_date} 的数据失败: {e}")
        return None

def get_indices_list():
    """获取指数列表"""
    return INDICES_LIST
