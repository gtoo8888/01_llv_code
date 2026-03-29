from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime
import os

from ..database import SessionLocal
from ..models import Record
from ..schemas import CalculateRequest, RecordResponse
from ..services.calculator import calculate

router = APIRouter()

STATIC_DIR = "static"

def read_html(filename: str) -> str:
    """读取 HTML 文件"""
    path = os.path.join(STATIC_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return f"<h1>Page not found: {filename}</h1>"

@router.get("/", response_class=HTMLResponse)
async def read_root():
    """返回欢迎页面"""
    return read_html("welcome.html")

@router.get("/wealth.html", response_class=HTMLResponse)
async def read_wealth():
    """返回理财收益计算器页面"""
    return read_html("wealth.html")

@router.post("/calculate", response_model=RecordResponse)
async def calculate_and_save(data: CalculateRequest):
    """计算收益并保存"""
    # 解析日期
    try:
        start = datetime.strptime(data.start_date, "%Y-%m-%d").date()
        end = datetime.strptime(data.end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式应为 YYYY-MM-DD")
    
    # 计算
    result = calculate(data.principal, start, end, data.income_start, data.income_end)
    
    # 保存到数据库
    db = SessionLocal()
    try:
        record = Record(
            principal=data.principal,
            start_date=start,
            end_date=end,
            income_start=data.income_start,
            income_end=data.income_end,
            **result
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        
        # 转换日期为字符串
        record_response = RecordResponse(
            id=record.id,
            principal=record.principal,
            start_date=record.start_date.strftime("%Y-%m-%d"),
            end_date=record.end_date.strftime("%Y-%m-%d"),
            income_start=record.income_start,
            income_end=record.income_end,
            days=record.days,
            total_income=record.total_income,
            daily_income=record.daily_income,
            daily_income_per_10k=record.daily_income_per_10k,
            annual_return=record.annual_return
        )
        return record_response
    finally:
        db.close()

@router.get("/records", response_model=list[RecordResponse])
async def get_records():
    """获取所有记录"""
    db = SessionLocal()
    try:
        records = db.query(Record).order_by(Record.id.desc()).all()
        return [
            RecordResponse(
                id=r.id,
                principal=r.principal,
                start_date=r.start_date.strftime("%Y-%m-%d"),
                end_date=r.end_date.strftime("%Y-%m-%d"),
                income_start=r.income_start,
                income_end=r.income_end,
                days=r.days,
                total_income=r.total_income,
                daily_income=r.daily_income,
                daily_income_per_10k=r.daily_income_per_10k,
                annual_return=r.annual_return
            )
            for r in records
        ]
    finally:
        db.close()

@router.delete("/records/{record_id}")
async def delete_record(record_id: int):
    """删除记录"""
    db = SessionLocal()
    try:
        record = db.query(Record).filter(Record.id == record_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="记录不存在")
        db.delete(record)
        db.commit()
        return {"message": "删除成功"}
    finally:
        db.close()
