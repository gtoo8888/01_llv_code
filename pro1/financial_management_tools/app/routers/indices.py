from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime, date
import os
import time

from ..database import SessionLocal
from ..models import IndexQuote
from ..schemas import IndexQuoteItem, IndexQuoteCachedResponse, ProgressResponse
from ..services.akshare_helper import (
    get_indices_list, 
    get_index_data_by_date, 
    fetch_progress, 
    fetch_lock
)

router = APIRouter()

STATIC_DIR = "static"

def read_html(filename: str) -> str:
    """读取 HTML 文件"""
    path = os.path.join(STATIC_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return f"<h1>Page not found: {filename}</h1>"

@router.get("/indices.html", response_class=HTMLResponse)
async def read_indices():
    """返回指数行情页面"""
    return read_html("indices.html")

@router.get("/api/indices")
async def get_indices(date: str = None):
    """返回指数行情数据（从 akshare 获取）并保存到数据库
    - date: 查询日期，格式 YYYY-MM-DD，默认为今天
    """
    global fetch_progress
    
    data = []
    now = datetime.now()
    INDICES_LIST = get_indices_list()
    
    # 重置进度
    with fetch_lock:
        fetch_progress = {
            'total': len(INDICES_LIST),
            'current': 0,
            'status': 'fetching',
            'message': '开始获取数据...'
        }
    
    # 解析日期参数
    if date:
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            target_date = date.today()
    else:
        target_date = date.today()
    
    for idx, index in enumerate(INDICES_LIST):
        # 更新进度
        with fetch_lock:
            fetch_progress['current'] = idx
            fetch_progress['message'] = f'正在获取 {index["name"]}...'
        
        # 检查是否禁用
        if index.get('disabled', False):
            data.append({
                'order': idx + 1,
                'code': index['code'],
                'name': index['name'],
                'current': None,
                'change': None,
                'changeAmt': None,
                'volume': None
            })
            time.sleep(1)
            continue
        
        # 获取指定日期的数据
        result = get_index_data_by_date(index['symbol'], target_date)
        
        if result:
            # 保存到数据库
            db = SessionLocal()
            try:
                db.query(IndexQuote).filter(
                    IndexQuote.code == index['code'],
                    IndexQuote.quote_date == target_date
                ).delete()
                
                quote = IndexQuote(
                    code=index['code'],
                    name=index['name'],
                    current=result['current'],
                    change=result['change'],
                    change_amt=result['changeAmt'],
                    volume=result['volume'],
                    quote_date=target_date,
                    update_time=now
                )
                db.add(quote)
                db.commit()
            finally:
                db.close()
            
            data.append({
                'order': idx + 1,
                'code': index['code'],
                'name': index['name'],
                'current': result['current'],
                'change': result['change'],
                'changeAmt': result['changeAmt'],
                'volume': result['volume']
            })
        else:
            data.append({
                'order': idx + 1,
                'code': index['code'],
                'name': index['name'],
                'current': None,
                'change': None,
                'changeAmt': None,
                'volume': None
            })
        
        time.sleep(1)
    
    # 更新进度为完成
    with fetch_lock:
        fetch_progress['current'] = len(INDICES_LIST)
        fetch_progress['status'] = 'completed'
        fetch_progress['message'] = '数据获取完成'
    
    return {
        'data': data,
        'updateTime': now.strftime('%Y-%m-%d %H:%M:%S')
    }

@router.get("/api/indices/progress", response_model=ProgressResponse)
async def get_indices_progress():
    """返回当前数据获取进度"""
    with fetch_lock:
        return {
            'total': fetch_progress['total'],
            'current': fetch_progress['current'],
            'status': fetch_progress['status'],
            'message': fetch_progress['message'],
            'percent': int(fetch_progress['current'] / fetch_progress['total'] * 100) if fetch_progress['total'] > 0 else 0
        }

@router.get("/api/indices/cached", response_model=IndexQuoteCachedResponse)
async def get_indices_cached():
    """从数据库获取缓存的指数行情数据"""
    INDICES_LIST = get_indices_list()
    
    db = SessionLocal()
    try:
        latest_date = db.query(IndexQuote.quote_date).order_by(IndexQuote.quote_date.desc()).first()
        
        if not latest_date:
            return {'data': [], 'updateTime': None, 'message': '暂无缓存数据'}
        
        quotes = db.query(IndexQuote).filter(
            IndexQuote.quote_date == latest_date[0]
        ).order_by(IndexQuote.id).all()
        
        code_to_quote = {q.code: q for q in quotes}
        
        data = []
        for idx, index in enumerate(INDICES_LIST):
            quote = code_to_quote.get(index['code'])
            
            if quote:
                data.append({
                    'order': idx + 1,
                    'code': quote.code,
                    'name': quote.name,
                    'current': quote.current,
                    'change': quote.change,
                    'changeAmt': quote.change_amt,
                    'volume': quote.volume
                })
            else:
                data.append({
                    'order': idx + 1,
                    'code': index['code'],
                    'name': index['name'],
                    'current': None,
                    'change': None,
                    'changeAmt': None,
                    'volume': None
                })
        
        update_time = latest_date[0].strftime('%Y-%m-%d') if latest_date else None
        
        return {
            'data': data,
            'updateTime': update_time,
            'message': '从缓存获取'
        }
    finally:
        db.close()
