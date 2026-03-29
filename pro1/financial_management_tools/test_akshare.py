#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Akshare 测试 Demo
测试获取各指数当天数据
"""

import akshare as ak
import pandas as pd
import time

# 指数列表（与 main.py 保持一致）
INDICES_LIST = [
    { 'code': 'sh000001', 'name': '上证指数', 'symbol': 'sh000001' },
    { 'code': 'sh000016', 'name': '上证50', 'symbol': 'sh000016' },
    { 'code': 'sh000300', 'name': '沪深300', 'symbol': 'sh000300' },
    { 'code': 'sh000510', 'name': '中证A500', 'symbol': 'sh000510' },
    { 'code': 'sh000688', 'name': '科创50', 'symbol': 'sh000688' },
    { 'code': 'sh000905', 'name': '中证500', 'symbol': 'sh000905' },
    { 'code': 'sh000922', 'name': '中证红利', 'symbol': 'sh000922' },
    { 'code': 'sz399006', 'name': '创业板指', 'symbol': 'sz399006' },
    { 'code': 'sz399673', 'name': '创业板50', 'symbol': 'sz399673' },
    # 红利低波100 需要特殊处理
]

def get_index_daily(symbol):
    """获取指数日线数据（只取最新一条）"""
    try:
        df = ak.stock_zh_index_daily(symbol=symbol)
        if df is not None and len(df) > 0:
            # 取最后一条（最新一天）
            latest = df.iloc[-1]
            return {
                'date': latest['date'],
                'open': latest['open'],
                'high': latest['high'],
                'low': latest['low'],
                'close': latest['close'],
                'volume': latest['volume']
            }
    except Exception as e:
        print(f"获取 {symbol} 失败: {e}")
    return None

def calculate_change(row):
    """计算涨跌幅和涨跌额（需要昨日收盘价）"""
    # 这里暂时无法计算，因为只取了一条数据
    # 需要获取前一天的数据来计算
    pass

def test_all_indices():
    """测试获取所有指数数据"""
    print("=" * 60)
    print("测试获取各指数当天数据")
    print("=" * 60)
    
    results = []
    
    for idx, index in enumerate(INDICES_LIST):
        print(f"\n[{idx+1}/{len(INDICES_LIST)}] 获取 {index['name']} ({index['symbol']})...")
        
        data = get_index_daily(index['symbol'])
        
        if data:
            print(f"  日期: {data['date']}")
            print(f"  开盘: {data['open']}")
            print(f"  最高: {data['high']}")
            print(f"  最低: {data['low']}")
            print(f"  收盘: {data['close']}")
            print(f"  成交量: {data['volume']}")
            
            results.append({
                'code': index['code'],
                'name': index['name'],
                **data
            })
        else:
            print(f"  获取失败!")
        
        # 间隔1秒，防止反爬
        time.sleep(1)
    
    print("\n" + "=" * 60)
    print("获取结果汇总")
    print("=" * 60)
    for r in results:
        print(f"{r['name']}: 收盘 {r['close']}")

def test_get_change_with_yesterday():
    """测试获取当天和前一天，计算涨跌幅"""
    print("\n" + "=" * 60)
    print("测试获取当天和前一天，计算涨跌幅")
    print("=" * 60)
    
    symbol = "sh000001"
    df = ak.stock_zh_index_daily(symbol=symbol)
    
    # 取最后2条数据
    latest = df.iloc[-1]
    yesterday = df.iloc[-2]
    
    print(f"\n昨天 ({yesterday['date']}): 收盘 {yesterday['close']}")
    print(f"今天 ({latest['date']}): 收盘 {latest['close']}")
    
    # 计算涨跌幅
    change = latest['close'] - yesterday['close']
    change_pct = (change / yesterday['close']) * 100
    
    print(f"涨跌额: {change:.2f}")
    print(f"涨跌幅: {change_pct:.2f}%")

if __name__ == "__main__":
    test_all_indices()
    test_get_change_with_yesterday()
