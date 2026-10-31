# pro11 — 上海金 ETF 调研

**与 pro10 分开**：本目录只处理跟踪「上海金集中定价合约」（SHAU）的 ETF，不混入 Au99.99 产品。

## 为什么分开

| | Au99.99（pro10） | 上海金（pro11） |
|---|---|---|
| 跟踪对象 | 现货实盘合约连续报价 | 集中定价合约，每日 10:15 / 14:15 两次定盘 |
| 估值 | 连续 | 两次定盘 |
| 文档位置 | `gold/` | `shanghai_gold/` |

场外联接本来就是日频净值，所以两者的差异在场外场景下被大幅抹平——但仍分开管理，便于对比。

## 结构

```
pro11/
├── survey.py          # 扫描上海金全市场，产出 data/shanghai_gold.{json,md}
├── data/
│   ├── shanghai_gold.json
│   └── shanghai_gold.md
└── logs/
```

抓取与解析能力复用 `../pro10/lib/common.py`，不复制代码，避免两套实现漂移。

## 运行

```bash
python survey.py
```

## 和 pro10 的关系

- pro10 是完整的四阶段链路（discover → extract → download → verify → clauses）
- pro11 目前只做到"扫描 + 费率"这一层
- 下一轮若上海金进入候选，把 pro10 的脚本按本目录的 `config` 复制改造即可

## 当前状态

23 只上海金产品已扫描（7 ETF + 16 份额），结论见
`01_data/07_wealth/02_investment/02_asset_classes/01_equity/shanghai_gold/20261023_shanghai_gold_universe.md`。
