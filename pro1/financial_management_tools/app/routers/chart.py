from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import os
import random

router = APIRouter()

STATIC_DIR = "static"

def read_html(filename: str) -> str:
    """读取 HTML 文件"""
    path = os.path.join(STATIC_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return f"<h1>Page not found: {filename}</h1>"

@router.get("/calculator.html", response_class=HTMLResponse)
async def read_calculator():
    """返回收益率计算器页面"""
    return read_html("calculator.html")

@router.get("/chart.html", response_class=HTMLResponse)
async def read_chart():
    """返回收益走势图表页面"""
    return read_html("chart.html")

@router.get("/api/chart-data")
async def get_chart_data():
    """返回随机生成的图表数据"""
    data = []
    base_principal = 10000
    
    for i in range(30):
        days = random.randint(7, 186)
        principal = base_principal + random.uniform(0, 100)
        rate = random.uniform(0.01, 0.06)
        total_income = principal * rate * days
        
        data.append({
            "days": days,
            "principal": round(principal, 2),
            "total_income": round(total_income, 2),
            "annual_return": round(rate * 365 * 100, 2)
        })
        
        base_principal = principal
    
    data.sort(key=lambda x: x["days"])
    return data
