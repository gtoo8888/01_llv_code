from datetime import date

def calculate(principal: float, start_date: date, end_date: date, income_start: float, income_end: float):
    """计算理财收益"""
    days = (end_date - start_date).days
    if days <= 0:
        raise ValueError("结束日期必须大于开始日期")
    
    total_income = income_end - income_start
    daily_income = total_income / days
    daily_income_per_10k = (total_income / principal) / days * 10000
    annual_return = (total_income / principal) / days * 365 * 100
    
    return {
        "days": days,
        "total_income": round(total_income, 2),
        "daily_income": round(daily_income, 2),
        "daily_income_per_10k": round(daily_income_per_10k, 2),
        "annual_return": round(annual_return, 2)
    }
