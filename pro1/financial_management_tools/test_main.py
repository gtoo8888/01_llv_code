"""
理财收益计算器 - 单元测试
"""
import sys
sys.path.insert(0, '/date_sdb/soft/openclaw/code')

from datetime import date
from fastapi.testclient import TestClient
from main import app, calculate

client = TestClient(app)


class TestCalculate:
    """测试计算逻辑"""
    
    def test_basic_calculation(self):
        """基础计算测试"""
        result = calculate(
            principal=5000,
            start_date=date(2026, 1, 27),
            end_date=date(2026, 2, 9),
            income_start=0,
            income_end=9.05
        )
        
        assert result["days"] == 13
        assert result["total_income"] == 9.05
        assert result["daily_income"] == 0.7
        assert result["daily_income_per_10k"] == 1.39
        assert result["annual_return"] == 5.08
    
    def test_zero_days(self):
        """相同日期测试（0天）"""
        try:
            calculate(
                principal=5000,
                start_date=date(2026, 1, 27),
                end_date=date(2026, 1, 27),
                income_start=0,
                income_end=9.05
            )
            assert False, "应该抛出异常"
        except Exception as e:
            assert "结束日期必须大于开始日期" in str(e)
    
    def test_negative_income(self):
        """负收益测试"""
        result = calculate(
            principal=10000,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 10),
            income_start=10,
            income_end=5
        )
        
        assert result["days"] == 9
        assert result["total_income"] == -5
        # -5/10000/9*365*100 = -2.027...
        assert abs(result["annual_return"] - (-2.03)) < 0.1


class TestAPI:
    """测试 API 接口"""
    
    def test_calculate_endpoint(self):
        """测试计算接口"""
        response = client.post("/calculate", json={
            "principal": 5000,
            "start_date": "2026-01-27",
            "end_date": "2026-02-09",
            "income_start": 0,
            "income_end": 9.05
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["days"] == 13
        assert data["total_income"] == 9.05
    
    def test_calculate_invalid_date(self):
        """测试无效日期格式"""
        response = client.post("/calculate", json={
            "principal": 5000,
            "start_date": "2026/01/27",  # 错误格式
            "end_date": "2026-02-09",
            "income_start": 0,
            "income_end": 9.05
        })
        
        assert response.status_code == 400
    
    def test_get_records(self):
        """测试获取记录"""
        response = client.get("/records")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_delete_record(self):
        """测试删除记录"""
        # 先创建一条记录
        create_response = client.post("/calculate", json={
            "principal": 1000,
            "start_date": "2026-01-01",
            "end_date": "2026-01-02",
            "income_start": 0,
            "income_end": 1
        })
        record_id = create_response.json()["id"]
        
        # 删除它
        delete_response = client.delete(f"/records/{record_id}")
        assert delete_response.status_code == 200
        
        # 确认删除
        get_response = client.get("/records")
        ids = [r["id"] for r in get_response.json()]
        assert record_id not in ids
    
    def test_delete_nonexistent(self):
        """测试删除不存在的记录"""
        response = client.delete("/records/99999")
        assert response.status_code == 404


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
