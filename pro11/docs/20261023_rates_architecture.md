# 02_rates 架构

整理日期：2026-10-23｜对应代码：`02_rates/`

把保险公司的费率表 PDF 转成可核对的 CSV。**只做事实，不做判断**：不排序、不评分、不比较产品优劣。

## 1. 目录

```
02_rates/
├── core.py               # 与公司无关的解析、校验、输出
├── parse_rates.py        # CLI：按公司选择 adapter
└── companies/
    ├── index.json        # 公司名 → 默认 PDF 文件名
    ├── chinalife.py
    ├── cpic.py
    ├── picclife.py
    ├── pingan.py
    ├── sunshine.py
    ├── taikang.py
    └── xinhua.py
```

## 2. 三层职责

| 层 | 负责 | 不负责 |
|---|---|---|
| **CLI**（`parse_rates.py`） | 读 `index.json`、校验配置与 adapter 一一对应、调用 core | 任何解析逻辑 |
| **core**（`core.py`） | 读词、聚列、聚行、映射性别/交费期、校验、写 CSV | 认得任何公司名或公司措辞 |
| **adapter**（`companies/*.py`） | 声明这家公司的差异：单位、页范围、维度、切块、阈值、抽样答案 | 读 PDF、写文件、算单位 |

一句话：**core 只回答“怎么切”，adapter 只回答“这家长什么样”。**

## 3. 数据流

```
PDF
 └─ read_pages()          每页取出 words（文字 + 坐标 + 字号）
     └─ split_blocks()    可选：一页有多张表时先切块（默认整页一块）
         └─ find_terms() / find_genders()   定位表头
             └─ build_rows()                按 x 聚列、按 y 聚行、映射到 (性别, 交费期)
                 └─ validate()              重复、年龄连续、正数、抽样断言
                     └─ write_outputs()     long / wide / meta / validation
```

### 3.1 聚列

数字词的左边缘 x0 是稳定的，但位数不同会带来几点的偏移，所以按 x0 聚类、容差由 `Spec.column_tolerance` 控制（默认 8.0）。列内再按 y 排序——插入顺序未必等于阅读顺序。

### 3.2 年龄列

不写死“第 0 列是年龄”，而是找**整数、跨度足够、相邻差基本为 1–2** 的列。双年龄列（阳光）也能处理，费率列会取它左边最近的年龄列。

### 3.3 表头

`10年交` 在 PDF 里常被切成 `10` + `年交`，而且 `年交` 的基线可能更高。所以 `find_terms` 是**双向就近合并**，不是按阅读顺序找下一个词。

### 3.4 缺格

行内允许缺值，按坐标落到最近的表头列；空缺不补 0、不猜。

## 4. Spec 字段

| 字段 | 默认 | 作用 | 谁覆盖 |
|---|---|---|---|
| `company` / `product` | 必填 | 写进 meta 与 validation | 全部 |
| `unit_amount` | `0`（自动识别） | 每千元 / 每万元；与 PDF 冲突会直接失败 | 全部显式写 |
| `pages` | `None`（全部） | 只解析这些页；用于排除加费表 | 太保、新华 |
| `sample` | `None` | 抽样断言，`{age, gender, term, premium}` | 全部 |
| `expected_rows` | `None` | 行数与预期不符时给警告 | 暂无 adapter 使用 |
| `min_column_rows` | `5` | 一列至少几个数字才算数 | 太保（2） |
| `column_tolerance` | `8.0` | 聚列容差（pt） | 无 |
| `row_tolerance` | `4.0` | 聚行容差（pt） | 无 |
| `thresholds` | 见下 | 判页门限 | 人保 |
| `dims` | `None` | `text → {plan, coverage, rate_class}` | 阳光、人保、新华 |
| `split_blocks` | `None` | `page → [block]`，一页多表时使用 | 人保 |
| `notes` | `""` | 写进 meta 与 validation | 全部 |

构造 `Spec` 时会立刻校验（`__post_init__`）：容差必须为正、`pages` 从 1 起、`sample` 字段齐全。配置错误在现场暴露，不留到解析中途。

## 5. Thresholds

| 字段 | 默认 | 含义 |
|---|---:|---|
| `min_age_values` | 10 | 年龄列至少几个值 |
| `min_age_span` | 20 | 年龄跨度至少多少岁 |
| `max_age_gap` | 2 | 相邻年龄最多隔几岁 |
| `min_consecutive_ratio` | 0.85 | 满足上述间隔的比例 |
| `min_columns` | 5 | 聚列后至少剩几列 |
| `min_rate_columns` | 4 | 其中至少几列是费率 |
| `max_terms_ratio` | 3.0 | 表头交费期数 ÷ 费率列数 的上限 |
| `min_rows` | 10 | 一页至少几行才算网格 |

**调参原则**：默认值服务多数公司；某家不满足时在它自己的 adapter 里覆盖，**不要改全局默认**。人保因为一份表被拆到多页、单页只有 5 个年龄，在 `picclife.py` 里覆盖为 `min_age_values=5, min_age_span=3, min_rows=5`。

另外三个是**守卫常量**，放在 `core.py` 顶部，不进 Spec，因为它们是“这页根本不是表”的底线：

```python
MIN_TEXT_CHARS = 50        # 全文少于 50 字符 = 没有文字层
MIN_NUMBERS_PER_PAGE = 20  # 一页少于 20 个数字 = 不是表
MAX_AGE = 120              # 年龄上限
```

## 6. 输出契约

每份 PDF 一个目录：`data_ouput/rates/<PDF 文件名>/`

| 文件 | 内容 |
|---|---|
| `rates_long.csv` | 一行一个单元格：`plan, coverage, rate_class, gender, age, pay_term, pay_term_years, premium, unit_amount, premium_per_10000, page` |
| `rates_wide.csv` | 一行一个年龄，列是 `性别_交费期` |
| `meta.json` | 源哈希、单位与依据、页统计、Spec、逐页结果 |
| `validation.md` | 逐页状态、错误、警告 |

**单位要注意**：`premium` 是 PDF 原值，按 `unit_amount` 计价；`premium_per_10000` 统一折算成“每万元保额”。跨产品比较只看后者。阳光是每千元，所以宽表里的数字是原值的 10 倍（88.1 → 881）。

## 7. 加一家公司

1. 把 PDF 放进 `data/rate_tables/`；
2. 在 `companies/index.json` 加一行 `"名字": "文件名.pdf"`；
3. 新建 `companies/名字.py`，至少写：

```python
from core import Spec

SAMPLE = {"age": 18, "gender": "男", "term": "5年交", "premium": 88.1}

def build_spec(pdf_path) -> Spec:
    return Spec(company="某公司", product="某产品", unit_amount=10000, sample=SAMPLE)
```

4. 先跑一次，看 `validation.md`：哪些页被跳过、原因是什么；
5. 只有确实需要时才加 `pages` / `dims` / `thresholds` / `split_blocks`。

CLI 启动时会校验 `index.json` 与 `companies/*.py` 一一对应，缺哪边都会直接报错。

## 8. 设计原则

1. **core 不认识公司**。出现公司名、“保险责任”、“方案一”这类词就是放错了层。
2. **专有知识放 adapter**：维度措辞、切块方式、页范围、阈值例外。
3. **默认值服务多数**，例外在 adapter 覆盖；不要用一家公司的特例改全局默认。
4. **守卫不进 Spec**：会改变“能不能解析”的底线，应该写死并报错，而不是让 adapter 关掉。
5. **失败要可诊断**：跳过原因带实测值和阈值，例如 `过滤后只剩 3 列 < 5`。
6. **抽样断言**：每个 adapter 配一个“已知答案”，算法一坏立刻发现。
7. **不做结果缓存**：每次都重新解析，产物只由本次输入决定。缓存键要覆盖 PDF、adapter 规则、core 算法，漏掉任何一项都会静默返回旧结果；这个项目规则改动远多于 PDF 改动，缓存是负收益。`meta.json` 里的 sha256 只作溯源证据，不参与跳过判断。

## 9. 已知取舍

| 现象 | 原因 | 处理 |
|---|---|---|
| 新华缺 0 岁 | 年龄格写作 `0（须出生满30日）`，不是纯数字 | 接受，范围 1–65 岁 |
| 阳光高龄段部分交费期为空 | PDF 本身空值 | 接受，不补 |
| 太保/新华大量跳页 | 3 页起是次标准体加费表 | `pages` 白名单排除 |
| 人保单页可能只有 5 行 | 一份表拆到多页 | adapter 覆盖 `thresholds` |

## 10. 排障

| 跳过原因 | 含义 | 先看什么 |
|---|---|---|
| `没有表头` | 没识别到交费期或性别 | 表头是不是图片、`年交` 是否被拆得更碎 |
| `没有识别到年龄列` | 年龄不连续、值太少、或双表叠在一页 | 是否要 `split_blocks`、是否要调 `thresholds` |
| `过滤后只剩 N 列 < 5` | 聚列失败或这页不是网格 | `column_tolerance`、页面是否旋转 |
| `数字词 N < 20` | 这页几乎没有数字 | 加费表、封面、说明页 |
| `表头交费期 N 个，与 M 个费率列不匹配` | 表头误识别 | 是否把数据里的数字当成了交费期 |
| 单位冲突 | `unit_amount` 与 PDF 不一致 | 先看 PDF 的单位说明，再改 spec |

## 11. 当前状态

7 家公司、47 个解析页、13,552 行、0 错误。

```powershell
python 02_rates/parse_rates.py --list
python 02_rates/parse_rates.py --company sunshine
```

文本 IO 统一走 `01_pdf/parse_utils.py`（显式 UTF-8、`newline="\n"`），规则见 `README.md`。
