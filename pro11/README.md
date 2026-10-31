# 保险研究

## 硬规则：文本编码

> 适用于所有在本目录工作的 agent 与人。**任何文本读写，必须显式指定编码，禁止依赖默认值。**

Python 的默认编码来自 `locale.getpreferredencoding()`：Linux/macOS 是 UTF-8，中文 Windows 是 `cp936`（GBK）。同一行代码在别人机器上没事，在这台机器上会炸，或者更糟——静默写成 GBK，等下游工具读的时候才变成乱码。

### 必须遵守

1. **写文件一律 `encoding="utf-8"`。**
   ```python
   path.write_text(text, encoding="utf-8")
   open(path, "w", encoding="utf-8")
   ```

2. **读自己产出的文件用 `encoding="utf-8"`；读外部或来源不明的 CSV / Markdown / TXT 用 `encoding="utf-8-sig"`**，顺手兜掉 BOM。
   ```python
   path.read_text(encoding="utf-8-sig")
   ```
   BOM 不会报错，只会让首字符变成 `\ufeff`，然后在字符串比较、做 key、生成哈希时莫名其妙对不上。

3. **需要逐字节稳定产出时，显式写 `newline="\n"`。**
   ```python
   open(path, "w", encoding="utf-8", newline="\n")
   ```
   Windows 上默认会把 `\n` 翻译成 `\r\n`。做哈希校验、逐字节比对（比如 `verify_research.py`）时，这一条会让结果对不上，而且报错完全看不出原因。

4. **禁止裸调用。** 以下写法一律视为 bug：
   ```python
   path.read_text()          # ✗
   path.write_text(s)        # ✗
   open(p)                   # ✗
   open(p, "w")              # ✗
   ```

5. **`json` / `csv` 也走同一条规则。**
   ```python
   json.loads(path.read_text(encoding="utf-8"))
   csv.reader(open(path, encoding="utf-8-sig", newline=""))
   ```

### 为什么写成规则，而不是靠自觉

模型能正确回答“`Path.read_text()` 默认编码是什么”，但生成代码时仍然会漏掉 `encoding`。这不是知识问题，是生成分布问题：训练语料大多是 Linux + UTF-8，所以“不写 encoding”在语料里通常是对的。靠提醒没有用，只能靠规则和工具拦截。

### 检查方式

```powershell
# 静态检查：unspecified-encoding
ruff check --select PLW1514 01_pdf
```

或在提交前全局搜一遍：

```powershell
rg "read_text\(\)|write_text\([^,)]*\)|open\([^)]*\)" -g "*.py"
```

命中的每一处，都要么补上 `encoding`，要么确认它只处理纯 ASCII。
