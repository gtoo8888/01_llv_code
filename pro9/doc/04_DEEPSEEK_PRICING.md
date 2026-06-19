# DeepSeek 官方定价（2026-06-19）

来源：DeepSeek 官方定价页面

## 核心模型

| 项目 | DeepSeek-V4-Flash | DeepSeek-V4-Pro |
|------|-------------------|-----------------|
| 上下文长度 | 1M | 1M |
| 最大输出长度 | 384K | 384K |
| 并发限制 | 2500 | 500 |
| 百万 tokens 输入（缓存命中） | ¥0.02 | ¥0.025 |
| 百万 tokens 输入（缓存未命中） | ¥1.00 | ¥3.00 |
| 百万 tokens 输出 | ¥2.00 | ¥6.00 |

## 计费公式

```
cost_cny = (input_cache_miss × cache_miss_price
          + input_cache_hit  × cache_hit_price
          + output           × output_price) / 1_000_000
```

## 模型名称映射

| 旧名称 | 对应新模型 | 弃用时间 |
|--------|-----------|---------|
| `deepseek-chat` → `deepseek-v4-flash`（非思考模式） | v4-flash | 2026-07-24 23:59 |
| `deepseek-reasoner` → `deepseek-v4-flash`（思考模式） | v4-flash | 2026-07-24 23:59 |

两个模型均支持非思考与思考模式（默认思考模式）。

## 扣费说明

- 扣减费用 = token 消耗量 × 模型单价
- 充值余额与赠送余额同时存在时，优先扣减赠送余额
- 价格可能变动，以官方页面为准
