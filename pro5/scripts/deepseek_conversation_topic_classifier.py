#!/usr/bin/env python3
"""
DeepSeek 对话批量分类器

对 DeepSeek 全量对话按主题分类，生成主题索引、得分明细、待分类高频词报告。
支持全量跑和按月份/文件数限制的测试跑。

用法:
    # 全量分类
    python scripts/deepseek_conversation_topic_classifier.py

    # 测试：仅处理指定月份
    python scripts/deepseek_conversation_topic_classifier.py --months 2026/05

    # 测试：处理多个月份
    python scripts/deepseek_conversation_topic_classifier.py --months 2025/01 2025/02 2026/05

    # 测试：限制总文件数（快速验证）
    python scripts/deepseek_conversation_topic_classifier.py --max-files 20
"""
import csv
import json
import re
import time
from collections import defaultdict
from pathlib import Path

from flashtext import KeywordProcessor
import jieba

# ─── 配置 ────────────────────────────────────────────────────────────────────

ARCHIVE_ROOT = Path(__file__).parent.parent / "llm_conversation_archives" / "deepseek_data-merged"
KEYWORD_MAP_PATH = Path(__file__).parent / "keyword_map.json"
OUTPUT_DIR = Path(__file__).parent / "output"

# 同步输出到归档根目录（供主程序使用）
SYNC_ARCHIVE_ROOT = Path("/data_sdb/openclaw/KnowledgeWorkspace/02_llv_generated/01_llv_code/pro5/llm_conversation_archives/deepseek_data-merged")

# 月份目录名映射：数字 → 英文全名
MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}

# 停用词表（用于 jieba 分词后的过滤）
STOP_WORDS = set("""
的 了 是 在 我 有 和 就 不 人 都 一 一个 上 也 很 到 说 要 去 你
会 着 没有 看 好 自己 这 他 她 它 们 什么 怎么 如何 为什么 哪个
哪里 谁 时候 时间 觉得 应该 可以 能 让 把 被 从 对 与 为 以 及
等 或 但 而 如果 因为 所以 但是 而且 虽然 只是 不过 还是 就是
这个 那个 这些 那些 已经 还是 没有 不是 非常 比较 一定 可能
需要 关于 对于 通过 进行 使用 利用 采用 提出 提供 实现 请 帮
我 它 做 给 用 写 看 想 问 知道 告诉 说明 解释 介绍 描述 分析
比较 选择 推荐 建议 方法 方式 问题 情况 内容 信息 数据 结果
效果 影响 原因 区别 差异 变化 发展 趋势 特点 功能 作用 意义
价值 例子 示例 案例 步骤 过程 流程 方案 计划 设计 结构 系统
版本 类型 格式 形式 方式 情况 其实 主要 基本 简单 复杂 常见
""".split())

# 计分阈值
SCORE_THRESHOLD = 3.0       # 低于此分的类别丢弃
LOW_CONFIDENCE_WEIGHT_MAX = 0.5  # 权重 ≤ 此值为低确信度词
LOW_CONFIDENCE_MIN_HITS = 3      # 低确信度词正文需至少命中这么多次才计分
MAX_TAGS = 2                     # 每条对话最多打几个标签

# 标题匹配的权重倍增系数
TITLE_MULTIPLIER = 10
BODY_MULTIPLIER = 1


# ─── 工具函数 ────────────────────────────────────────────────────────────────

def load_keyword_map(path: Path) -> tuple:
    """加载关键词映射表，将嵌套结构拍平成 父类/子类 扁平格式。
    返回 (flat_dict, parent_order)，parent_order 保持 JSON 中的父类顺序。
    """
    with open(path, "r", encoding="utf-8") as f:
        nested = json.load(f)

    flat = {}
    parent_order = []
    seen_parents = set()
    for parent, children in nested.items():
        # 按 JSON 顺序记录父类
        if parent not in seen_parents:
            parent_order.append(parent)
            seen_parents.add(parent)
        for child, keywords in children.items():
            tag = f"{parent}/{child}"
            flat[tag] = {"keywords": keywords}
    return flat, parent_order


def parse_month_param(month_str: str) -> tuple:
    """解析 --months 参数，返回 (year_dir, month_dir)。
    例如 "2026/05" → ("2026", "05_May")
    """
    parts = month_str.strip().split("/")
    if len(parts) != 2:
        raise ValueError(f"月份参数格式应为 YYYY/MM，收到: {month_str}")
    year, month_num = parts[0], int(parts[1])
    month_name = MONTH_NAMES.get(month_num)
    if month_name is None:
        raise ValueError(f"无效月份: {month_num}")
    return year, f"{month_num:02d}_{month_name}"


def extract_title_from_filename(filename: str) -> str:
    name = filename.replace(".md", "")
    match = re.match(r"\d{4}-\d{2}-\d{2}_(.+)", name)
    if match:
        return match.group(1)
    return name


def read_file_content(file_path: Path) -> str:
    """读取 .md 文件正文"""
    try:
        return file_path.read_text(encoding="utf-8")
    except Exception:
        return ""


def normalize_text(text: str) -> str:
    return text.lower()


def split_text_into_words(text: str) -> list:
    """将文本切分为候选词，用于新词发现。
    英文按空格/符号分词，中文用 jieba 精确模式分词。
    """
    words = []
    # 英文部分
    for eng in re.findall(r"[a-zA-Z][a-zA-Z0-9._+#-]{1,}", text):
        words.append(eng.lower())
    # 中文部分：jieba 精确模式
    for w in jieba.cut(text):
        w = w.strip()
        if len(w) >= 2 and "\u4e00" <= w[0] <= "\u9fff":
            words.append(w)
    return words

class TopicClassifier:
    """对话主题分类器"""
    def __init__(self, keyword_map: dict):
        self.keyword_map = keyword_map
        # 构建 flashtext 多模式匹配器
        self.kp = KeywordProcessor(case_sensitive=False)
        self.kw_info = {}  # keyword_lower -> [(category, weight, original_keyword), ...]

        for category, info in keyword_map.items():
            for kw, weight in info["keywords"].items():
                kw_lower = kw.lower()
                self.kw_info.setdefault(kw_lower, []).append((category, weight, kw))
                self.kp.add_keyword(kw_lower)

    def _scan_text(self, text: str) -> dict:
        """扫描文本，返回 {keyword_lower: count}。

        先用 flashtext 快速筛选出文本中出现了哪些关键词，
        再用 str.count() 精确统计每个词的实际出现次数（支持重叠匹配）。
        """
        text_lower = text.lower()
        # flashtext 做非重叠快速筛选，找出文本中出现了哪些关键词
        present_kw = set(self.kp.extract_keywords(text))
        # 用 count() 精确统计每个关键词的实际出现次数（与原代码行为一致）
        return {kw: text_lower.count(kw) for kw in present_kw}

    def _aggregate_scores(self, title_hits: dict, body_hits: dict) -> dict:
        """合并标题/正文命中，应用权重、低确信度规则，产出每个类别的得分"""
        all_kw = set(title_hits.keys()) | set(body_hits.keys())
        temp = defaultdict(lambda: {"total": 0.0, "title_score": 0.0, "body_score": 0.0, "detail_parts": []})

        for kw_lower in all_kw:
            entries = self.kw_info.get(kw_lower)
            if not entries:
                continue

            t_count = title_hits.get(kw_lower, 0)
            b_count = body_hits.get(kw_lower, 0)

            for category, weight, kw_orig in entries:
                # 低确信度规则：正文中权重低且次数不足时忽略正文命中
                effective_b_count = b_count
                if weight <= LOW_CONFIDENCE_WEIGHT_MAX and b_count < LOW_CONFIDENCE_MIN_HITS:
                    effective_b_count = 0

                t_score = t_count * TITLE_MULTIPLIER * weight
                b_score = effective_b_count * BODY_MULTIPLIER * weight

                if t_score > 0 or b_score > 0:
                    detail = f"{kw_orig}(标题×{t_count},正文×{effective_b_count})"
                    temp[category]["title_score"] += t_score
                    temp[category]["body_score"] += b_score
                    temp[category]["total"] += t_score + b_score
                    temp[category]["detail_parts"].append(detail)

        # 转换为标准输出格式
        category_scores = {}
        for cat, d in temp.items():
            category_scores[cat] = {
                "total": round(d["total"], 1),
                "title_score": round(d["title_score"], 1),
                "body_score": round(d["body_score"], 1),
                "details": "; ".join(d["detail_parts"]),
            }
        return category_scores

    def classify_file(self, file_path: Path) -> dict:
        """分类单个文件，返回分类结果"""
        title = extract_title_from_filename(file_path.name)
        body = read_file_content(file_path)

        title_lower = normalize_text(title)
        body_lower = normalize_text(body)

        # 一次性扫描标题和正文，获取所有关键词命中次数
        title_hits = self._scan_text(title)
        body_hits = self._scan_text(body)

        # 按类别汇总得分
        category_scores = self._aggregate_scores(title_hits, body_hits)

        # 决策标签
        result = self._decide_tags(category_scores, title, file_path)

        # 附加小写文本，供后续步骤复用（避免重复 I/O 和小写化）
        result["title_lower"] = title_lower
        result["body_lower"] = body_lower
        return result

    def _decide_tags(self, category_scores: dict, title: str, file_path: Path) -> dict:
        """根据得分决策最终标签"""
        # 过滤低于阈值的
        filtered = [(cat, info) for cat, info in category_scores.items()
                     if info["total"] >= SCORE_THRESHOLD]

        # 按总分降序排列
        filtered.sort(key=lambda x: x[1]["total"], reverse=True)

        # 取前 MAX_TAGS 个
        top = filtered[:MAX_TAGS]
        assigned_tags = [cat for cat, _ in top]

        # 得分最高的类别
        top_category = top[0] if top else None

        return {
            "file_path": str(file_path.relative_to(ARCHIVE_ROOT)
                         if ARCHIVE_ROOT in file_path.parents
                         else file_path),
            "title": title,
            "assigned_tags": assigned_tags,
            "is_unmatched": len(top) == 0,
            "top_category": {
                "name": top_category[0],
                "score": top_category[1]["total"],
                "title_score": top_category[1]["title_score"],
                "body_score": top_category[1]["body_score"],
                "details": top_category[1]["details"],
            } if top_category else None,
            "all_scores": category_scores,
        }

    def extract_unmatched_words(self, results: list) -> list:
        """从待分类对话的正文中提取高频词，用于新词发现"""
        word_freq = defaultdict(int)
        file_count = defaultdict(set)

        for r in results:
            if not r["is_unmatched"]:
                continue

            # 优先使用缓存的小写文本（避免重复 I/O 和小写化）
            title_lower = r.get("title_lower", "")
            body_lower = r.get("body_lower", "")

            # 缓存不存在时才回退到读取文件
            if not body_lower:
                try:
                    full_path = ARCHIVE_ROOT / r["file_path"]
                    if full_path.exists():
                        body = read_file_content(full_path)
                        body_lower = normalize_text(body)
                    else:
                        body_lower = ""
                except Exception:
                    body_lower = ""

            # 合并标题和正文进行分析
            combined = title_lower + " " + body_lower
            words = split_text_into_words(combined)
            for w in words:
                if len(w) >= 2 and w not in STOP_WORDS:
                    word_freq[w] += 1
                    file_count[w].add(r["file_path"])

        # 排序输出
        result = []
        for word, freq in sorted(word_freq.items(), key=lambda x: -x[1]):
            result.append({
                "word": word,
                "total_frequency": freq,
                "file_count": len(file_count[word]),
            })

        return result

def collect_md_files(archive_root: Path, months: list = None, max_files: int = None) -> list:
    files = []

    if months:
        for month_param in months:
            year, month_dir = parse_month_param(month_param)
            month_path = archive_root / year / month_dir
            if not month_path.exists():
                print(f"  [!] 目录不存在，跳过: {month_path}")
                continue
            for f in sorted(month_path.glob("*.md")):
                if f.name != "_index.md":
                    files.append(f)
    else:
        # 全量扫描
        for year_dir in sorted(archive_root.iterdir()):
            if not year_dir.is_dir() or not year_dir.name.isdigit():
                continue
            for month_dir in sorted(year_dir.iterdir()):
                if not month_dir.is_dir():
                    continue
                for f in sorted(month_dir.glob("*.md")):
                    if f.name != "_index.md":
                        files.append(f)

    if max_files and len(files) > max_files:
        files = files[:max_files]

    return files

def generate_topic_index(results: list, run_info: dict, parent_order: list = None) -> str:
    """生成按主题分组的 Markdown 索引（支持 父类/子类 层级 + 编号）
    parent_order 指定父类输出顺序，不传则按字典序。
    """
    lines = []
    lines.append("# DeepSeek 对话主题索引")
    lines.append("")
    lines.append(f"> **总对话数**: {run_info['total']} | "
                 f"**已分类**: {run_info['classified']} | "
                 f"**待分类**: {run_info['unmatched']} | "
                 f"**覆盖率**: {run_info['coverage']:.1f}%")
    lines.append("")

    # 按父类/子类重新组织
    # parent -> {child_full_name: [items]}
    parent_groups = defaultdict(lambda: defaultdict(list))
    unmatched = []

    for r in results:
        if r["is_unmatched"]:
            unmatched.append(r)
        else:
            for tag in r["assigned_tags"]:
                if "/" in tag:
                    parent, child = tag.rsplit("/", 1)
                else:
                    parent, child = tag, ""
                parent_groups[parent][tag].append(r)

    # 确定父类输出顺序
    if parent_order:
        # 按 JSON 顺序，只保留实际有数据的父类
        ordered_parents = [p for p in parent_order if p in parent_groups]
    else:
        ordered_parents = sorted(parent_groups.keys())

    parent_num = 0
    for parent in ordered_parents:
        parent_num += 1
        children = parent_groups[parent]

        # 统计父类总条目数（各子类去重计数）
        all_parent_items = []
        for child_tag, items in children.items():
            all_parent_items.extend(items)
        # 按 file_path 去重（避免一条对话被多个子类重复计入父类总数）
        seen = set()
        parent_total = 0
        for item in all_parent_items:
            if item["file_path"] not in seen:
                seen.add(item["file_path"])
                parent_total += 1

        lines.append(f"## {parent_num}. {parent}（{parent_total}条）")

        child_num = 0
        for child_tag in sorted(children.keys()):
            child_num += 1
            child_name = child_tag.rsplit("/", 1)[1] if "/" in child_tag else child_tag
            items = children[child_tag]
            lines.append(f"### {parent_num}.{child_num} {child_name}（{len(items)}条）")
            for item in items:
                lines.append(f"- {item['title']}")
            lines.append("")

    # 待分类
    lines.append(f"## 待分类（{len(unmatched)}条）")
    for item in unmatched:
        lines.append(f"- {item['title']}")
    lines.append("")

    return "\n".join(lines)


def generate_score_csv(results: list, output_path: Path):
    """生成得分明细 CSV"""
    fieldnames = [
        "file_path", "category", "keyword_hits",
        "title_score", "body_score", "total_score", "assigned_tags",
    ]
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            for cat, info in r["all_scores"].items():
                if info["total"] > 0:
                    writer.writerow({
                        "file_path": r["file_path"],
                        "category": cat,
                        "keyword_hits": info["details"],
                        "title_score": info["title_score"],
                        "body_score": info["body_score"],
                        "total_score": info["total"],
                        "assigned_tags": ", ".join(r["assigned_tags"]),
                    })


def generate_summary_csv(results: list, output_path: Path, parent_order: list = None):
    """生成分类概要 CSV：父类,子类,条数"""
    # 按父类/子类分组
    parent_groups = defaultdict(lambda: defaultdict(list))
    for r in results:
        if r["is_unmatched"]:
            continue
        for tag in r["assigned_tags"]:
            if "/" in tag:
                parent, child = tag.rsplit("/", 1)
            else:
                parent, child = tag, ""
            parent_groups[parent][tag].append(r)

    ordered_parents = [p for p in parent_order if p in parent_groups] if parent_order else sorted(parent_groups.keys())

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["parent", "child", "count"])
        for parent in ordered_parents:
            for child_tag in sorted(parent_groups[parent].keys()):
                child_name = child_tag.rsplit("/", 1)[1] if "/" in child_tag else child_tag
                count = len(parent_groups[parent][child_tag])
                writer.writerow([parent, child_name, count])


def generate_unmatched_csv(words: list, output_path: Path):
    """生成待分类高频词报告 CSV"""
    fieldnames = ["word", "total_frequency", "file_count"]
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for w in words:
            writer.writerow(w)


def load_manual_tags(path: Path) -> dict:
    """加载手工修正标签文件"""
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_manual_tags(tags: dict, path: Path):
    """保存手工修正标签文件"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tags, f, ensure_ascii=False, indent=2)

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="DeepSeek 对话批量分类器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/deepseek_conversation_topic_classifier.py
  python scripts/deepseek_conversation_topic_classifier.py --months 2026/05
  python scripts/deepseek_conversation_topic_classifier.py --months 2025/01 2025/02
  python scripts/deepseek_conversation_topic_classifier.py --max-files 20
        """,
    )
    parser.add_argument("--months", nargs="+", help="指定月份，格式 YYYY/MM，例如 2026/05")
    parser.add_argument("--max-files", type=int, help="限制最大处理文件数（用于快速测试）")
    parser.add_argument("--output", default=str(OUTPUT_DIR), help="输出目录（默认 scripts/output/）")

    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  DeepSeek 对话批量分类器")
    print("=" * 60)
    print()

    t_start = time.perf_counter()

    # 1. 加载映射表
    print("[1/5] 加载关键词映射表...")
    t1 = time.perf_counter()
    keyword_map, parent_order = load_keyword_map(KEYWORD_MAP_PATH)
    category_count = len(keyword_map)
    total_keywords = sum(len(info["keywords"]) for info in keyword_map.values())
    print(f"      {category_count} 个分类, {total_keywords} 个关键词  ({time.perf_counter() - t1:.2f}s)")
    print()

    # 2. 收集文件
    print("[2/5] 收集对话文件...")
    t2 = time.perf_counter()
    if args.months:
        print(f"      模式: 测试跑 (指定 {len(args.months)} 个月份)")
    else:
        print(f"      模式: 全量跑")
    files = collect_md_files(ARCHIVE_ROOT, months=args.months, max_files=args.max_files)
    print(f"      找到 {len(files)} 个对话文件  ({time.perf_counter() - t2:.2f}s)")
    if args.max_files and len(files) > args.max_files:
        files = files[:args.max_files]
        print(f"      限制处理: {len(files)} 个文件")
    print()

    # 3. 分类
    print("[3/5] 执行分类...")
    t3 = time.perf_counter()
    classifier = TopicClassifier(keyword_map)
    results = []

    for i, f in enumerate(files):
        if (i + 1) % 50 == 0:
            print(f"      进度: {i + 1}/{len(files)}")
        result = classifier.classify_file(f)
        results.append(result)

    t_classify = time.perf_counter() - t3
    avg_per_file = t_classify / len(files) if files else 0
    print(f"      完成: 分类 {len(results)} 个对话  ({t_classify:.2f}s, 平均 {avg_per_file*1000:.1f}ms/个)")
    print()

    # 4. 生成输出
    print("[4/5] 生成输出文件...")
    t4 = time.perf_counter()

    # 统计
    classified = sum(1 for r in results if not r["is_unmatched"])
    unmatched = sum(1 for r in results if r["is_unmatched"])
    coverage = (classified / len(results) * 100) if results else 0

    run_info = {
        "total": len(results),
        "classified": classified,
        "unmatched": unmatched,
        "coverage": coverage,
    }

    # 4a. 主题索引
    index_content = generate_topic_index(results, run_info, parent_order)
    index_path = output_dir / "topic_index.md"
    index_path.write_text(index_content, encoding="utf-8")
    print(f"      📄 topic_index.md   — 主题索引 ({classified} 已分类 / {unmatched} 待分类, {coverage:.1f}%)")

    # 4b. 得分明细 CSV
    score_path = output_dir / "score_log.csv"
    generate_score_csv(results, score_path)
    print(f"      📊 score_log.csv     — 得分明细")

    # 4c. 分类概要
    summary_path = output_dir / "category_summary.csv"
    generate_summary_csv(results, summary_path, parent_order)
    print(f"      📊 category_summary.csv — 分类概要 ({len(results)} 条)")

    # 同步到归档根目录（供主程序 stats 使用）
    if SYNC_ARCHIVE_ROOT.exists():
        sync_path = SYNC_ARCHIVE_ROOT / "category_summary.csv"
        generate_summary_csv(results, sync_path, parent_order)
        print(f"      📎 同步到: {sync_path}")

    # 4d. 待分类高频词
    if unmatched > 0:
        print(f"      [jieba 分词进行中...]")
        words = classifier.extract_unmatched_words(results)
        unmatched_path = output_dir / "unmatched_words.csv"
        generate_unmatched_csv(words, unmatched_path)
        print(f"      🔍 unmatched_words.csv — 待分类高频词 ({len(words)} 个词)")
    else:
        # 即使没有待分类也生成空文件
        unmatched_path = output_dir / "unmatched_words.csv"
        unmatched_path.write_text("word,total_frequency,file_count\n", encoding="utf-8")
        print(f"      🔍 unmatched_words.csv — 无待分类对话 (空)")
    t5 = time.perf_counter()
    print()

    # 5. 加载手工标签
    print("[5/5] 处理手工标签...")
    manual_path = output_dir / "manual_tags.json"
    existing_manual = load_manual_tags(manual_path)
    if existing_manual:
        print(f"      已加载 {len(existing_manual)} 条手工标签")
    else:
        print(f"      无手工标签 (新文件)")
    # 写入空模板（保留已有手工标签）
    save_manual_tags(existing_manual, manual_path)
    print(f"      ✏️  manual_tags.json  — 手工标签 (已有 {len(existing_manual)} 条)  ({time.perf_counter() - t5:.2f}s)")
    print()

    # 汇总
    t_total = time.perf_counter() - t_start
    print("=" * 60)
    print(f"  ✅ 分类完成!")
    print(f"  输出目录: {output_dir}")
    print(f"  已分类:   {classified} / {len(results)} ({coverage:.1f}%)")
    print(f"  待分类:   {unmatched}")
    print(f"  ──────────────────────────")
    print(f"  总耗时:   {t_total:.2f}s")
    print(f"   加载映射表:   {t2 - t1:.2f}s")
    print(f"   收集文件:     {t3 - t2:.2f}s")
    print(f"   执行分类:     {t_classify:.2f}s ({avg_per_file*1000:.1f}ms/个)")
    print(f"   生成输出:     {t5 - t4:.2f}s")
    print(f"   处理标签:     {time.perf_counter() - t5:.2f}s")
    print(f"  ──────────────────────────")
    print(f"  使用:     查看 topic_index.md 概览全貌")
    print(f"           查看 unmatched_words.csv 发现新词")
    print(f"           查看 score_log.csv 调参")
    print("=" * 60)


if __name__ == "__main__":
    main()
