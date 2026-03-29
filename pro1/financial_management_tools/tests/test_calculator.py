"""
理财收益计算器 - 单元测试

测试 calculator.py 中的 calculate 函数

注意：
- days = (end_date - start_date).days，返回的是日期差，不是包含两端的"天数+1"
- 例如：1月1日到1月2日 = 1天，1月1日到1月10日 = 9天
"""

import pytest
from datetime import date
from app.services.calculator import calculate


class TestCalculate:
    """计算函数测试类"""

    def test_calculate_normal(self):
        """测试正常计算场景"""
        # 本金 10000，30天，收益从 10000 到 10050
        # 1月1日到1月31日 = 30天
        result = calculate(
            principal=10000,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            income_start=10000,
            income_end=10050
        )
        
        assert result["days"] == 30
        assert result["total_income"] == 50
        assert result["daily_income"] == pytest.approx(1.67, rel=0.01)
        assert result["daily_income_per_10k"] == pytest.approx(1.67, rel=0.01)
        # 年化收益 = (50/10000) / 30 * 365 * 100 = 6.08%
        assert result["annual_return"] == pytest.approx(6.08, rel=0.01)

    def test_calculate_one_day(self):
        """测试1天的情况"""
        # 1月1日到1月2日 = 1天
        result = calculate(
            principal=10000,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 2),
            income_start=10000,
            income_end=10010
        )
        
        assert result["days"] == 1
        assert result["total_income"] == 10
        assert result["daily_income"] == 10

    def test_calculate_negative_income(self):
        """测试负收益"""
        result = calculate(
            principal=10000,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            income_start=10000,
            income_end=9950
        )
        
        assert result["days"] == 30
        assert result["total_income"] == -50
        assert result["daily_income"] == pytest.approx(-1.67, rel=0.01)
        assert result["annual_return"] == pytest.approx(-6.08, rel=0.01)

    def test_calculate_large_principal(self):
        """测试大本金"""
        result = calculate(
            principal=1000000,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            income_start=1000000,
            income_end=1005000
        )
        
        assert result["days"] == 30
        assert result["total_income"] == 5000
        assert result["daily_income"] == pytest.approx(166.67, rel=0.01)
        assert result["annual_return"] == pytest.approx(6.08, rel=0.01)

    def test_calculate_zero_days(self):
        """测试天数为0的情况 - 应该抛出异常"""
        with pytest.raises(ValueError, match="结束日期必须大于开始日期"):
            calculate(
                principal=10000,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 1),
                income_start=10000,
                income_end=10050
            )

    def test_calculate_invalid_date_range(self):
        """测试结束日期早于开始日期 - 应该抛出异常"""
        with pytest.raises(ValueError, match="结束日期必须大于开始日期"):
            calculate(
                principal=10000,
                start_date=date(2026, 1, 31),
                end_date=date(2026, 1, 1),
                income_start=10000,
                income_end=10050
            )


class TestCalculateEdgeCases:
    """边界情况测试"""

    def test_calculate_fractional_income(self):
        """测试小数收益"""
        # 1月1日到1月7日 = 6天
        result = calculate(
            principal=10000,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 7),
            income_start=10000,
            income_end=10003.33
        )
        
        # 6天收益3.33
        assert result["days"] == 6
        assert result["total_income"] == 3.33
        assert result["daily_income"] == pytest.approx(0.555, rel=0.01)

    def test_calculate_exact_values(self):
        """测试精确值"""
        # 1月1日到1月10日 = 9天
        result = calculate(
            principal=10000,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 10),
            income_start=10000,
            income_end=10100
        )
        
        # 9天收益100
        assert result["days"] == 9
        assert result["total_income"] == 100
        assert result["daily_income"] == pytest.approx(11.11, rel=0.01)
        # 年化 = (100/10000) / 9 * 365 * 100 = 40.56%
        assert result["annual_return"] == pytest.approx(40.56, rel=0.01)

    def test_calculate_365_days(self):
        """测试365天（整年）"""
        # 2026年1月1日到2026年12月31日 = 364天（2026是平年）
        result = calculate(
            principal=10000,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            income_start=10000,
            income_end=12000
        )
        
        assert result["days"] == 364
        assert result["total_income"] == 2000
        assert result["daily_income"] == pytest.approx(5.49, rel=0.01)
        # 年化 = (2000/10000) / 364 * 365 * 100 = 20.05%
        assert result["annual_return"] == pytest.approx(20.05, rel=0.01)
