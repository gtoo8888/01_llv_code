# pro10 — 基金调研工具链（黄金 ETF）

给知识工作区做"结构化基金调研"的可复跑工具。当前覆盖：**Au99.99 实物黄金 ETF 及场外份额（7 只 ETF / 18 只份额）**。

上海金（不同的跟踪标的）见 `../pro11/`。

## 定位

不是"搜索总结"，是**脚本搬运 + 证据落盘 + 多源校验**。
每份 PDF、每个费率数字都能回溯到来源 URL 和 sha256。

## 流程

```
config/universe.json
      │
      ├─ 01_discover.py ──► data/html/*.html（基本概况/费率/阶段涨幅快照）
      │        │
      │        ▼
      │   04_extract.py  ──► data/extracted.json（费率、基准、规模、阶梯）
      │
      ├─ 06_survey.py   ──► data/survey.{json,md}（全市场扫描，定候选池）
      │
      ├─ 02_download.py ──► data/raw/*.pdf（招募书/合同/概要/定期报告/公告）
      │
      ├─ 05_verify.py   ──► data/coverage.md（缺件、损坏、费率多源对照）
      │
      └─ 07_clauses.py  ──► data/clauses.json（不重复收费 / 黄金租赁条款）
```

## 运行

```bash
python 06_survey.py     # 1. 全市场扫描，定候选
python 01_discover.py   # 2. 抓候选的详情页
python 04_extract.py    # 3. 抽字段
python 02_download.py   # 4. 下 PDF（最慢，可后台）
python 05_verify.py     # 5. 校验
python 07_clauses.py    # 6. 条款核查
```

依赖：`requests`、`pdfplumber`。建议独立 venv，**不要装进 conda base**。

## 数据源

| 用途 | 接口 | 备注 |
|---|---|---|
| 全量基金代码 | `fund.eastmoney.com/js/fundcode_search.js` | 2.8 万只，GBK 头但 UTF-8 内容 |
| 基本概况 | `fundf10.eastmoney.com/jbgk_{code}.html` | 管理费/托管费/业绩基准/规模 |
| 费率阶梯 | `fundf10.eastmoney.com/jjfl_{code}.html` | 申购/赎回阶梯 |
| 公告列表 | `api.fund.eastmoney.com/f10/JJGG` | 需 `Referer` 头 |
| 公告 PDF | `pdf.dfcfw.com/pdf/H2_{公告ID}_1.pdf` | 公告镜像 |

> 天天基金是**线索层**。严格官方原件应回基金公司官网或证监会基金电子披露网站核验，这一步尚未实现。

## 已踩的坑（改代码前先读）

1. **编码**：不能信 HTTP 头的 charset。按"解码后汉字数量"选 UTF-8 / GB18030。`fundcode_search.js` 带 BOM。
2. **费率阶梯正则**：单位有 `元 / 天 / 年` 三种，漏一种就丢行（如「大于等于7天，小于1年」）。
3. **不重复收费条款有至少三种措辞**：
   - 「不收取管理费」
   - 「为避免重复收费……不对……计提」
   - 「按扣除目标ETF后的剩余部分计提」
   正则写窄了会误判成双重收费。
4. **份额类别**：A/C/E/I/D 都要扫。E/I 常排在搜索接口后面，但赎回费往往最优。
5. **低销售服务费不等于便宜**：博时 E、华安 I 的销售服务费只有 0.01%，但管理费 0.50% 才是大头。
6. **定期报告筛选**：标题里「2026年中期报告的**提示性公告**」会抢在正文前面，需要额外排除。
7. **限购额度**：公告滞后，实时状态只能在下单渠道确认。

## 产出同步到知识库

```powershell
# 跑完后同步
Copy-Item data\raw\*.pdf  <gold目录>\<日期>_gold_etf_sources\ -Force
Copy-Item data\{manifest.json,coverage.md,clauses.json,survey.json} <目标>\ -Force
```
