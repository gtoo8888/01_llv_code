#!/usr/bin/env python3
"""
淘票票单片每日票房明细 HTML -> CSV 转换脚本

支持批量处理目录下的所有HTML文件。

使用方法:
    # 处理整个目录
    python taopiaopiao_to_csv.py 01_raw/2024/

    # 或处理单个文件 (自动从文件名提取电影名)
    python taopiaopiao_to_csv.py 01_raw/2024/01_20240210_热辣滚烫.html

输出目录: 将输入路径中的 01_raw 替换为 02_csv
    例: 01_raw/2024/xxx.html -> 02_csv/2024/xxx.csv
"""

import sys
import re
import csv
import os
from bs4 import BeautifulSoup

# 百分比列（保留 % 符号）
PCT_COLUMNS = {
    "综合票房大盘占比",
    "排片大盘占比",
    "人次大盘占比",
    "上座率",
    "排座大盘占比",
    "黄金场单片占比",
    "黄金场大盘占比",
    "大盘退票率",
    "猫眼退票率",
    "网售票房占比",
    "网售人次占比",
    "分账票房大盘占比",
}

# 表头定义（26列，含日期）
HEADERS = [
    "日期",             # 0
    "综合票房_万元",     # 1
    "综合票房大盘占比",  # 2  %
    "场次",             # 3
    "排片大盘占比",     # 4  %
    "排场效益_B值",     # 5
    "人次",             # 6
    "人次大盘占比",     # 7  %
    "场均人次",         # 8
    "综合票价",         # 9
    "座位数",           # 10
    "排座大盘占比",     # 11 %
    "上座率",           # 12 %
    "排片影院数",       # 13
    "黄金场次",         # 14
    "黄金场单片占比",   # 15 %
    "黄金场大盘占比",   # 16 %
    "大盘退票人次",     # 17
    "大盘退票率",       # 18 %
    "猫眼退票人次",     # 19
    "猫眼退票率",       # 20 %
    "网售票房占比",     # 21 %
    "网售人次占比",     # 22 %
    "分账票房_万元",    # 23
    "分账票房大盘占比", # 24 %
    "分账票价",         # 25
]

FULL_HEADERS = ["电影", "日期", "星期", "标签"] + HEADERS[1:]

# 文件名格式: 序号_YYYYMMDD_电影名.html
FILENAME_PATTERN = re.compile(r'(\d+)_(\d{8})_(.+)\.html$')


def extract_movie_info(filename: str):
    """从文件名提取 (电影名, 上映日期, 序号)"""
    m = FILENAME_PATTERN.search(filename)
    if m:
        rank = m.group(1)
        date = f"{m.group(2)[:4]}-{m.group(2)[4:6]}-{m.group(2)[6:8]}"
        name = m.group(3)
        return name, date, rank
    basename = os.path.splitext(filename)[0]
    return basename, "", ""


def convert_value(raw: str, is_pct: bool):
    """
    根据列类型转换数值。
    - 百分比列：保留原始字符串（如 "0.1%" / "<0.1%" / "--"）
    - 数值列：转为 float（"1.0万" -> 10000.0）
    """
    raw = raw.strip()
    if not raw or raw == "--":
        return raw if is_pct else None

    if is_pct:
        return raw

    if raw == "0":
        return 0.0

    lt_match = re.match(r'^<([\d.]+)%?$', raw)
    if lt_match:
        return float(lt_match.group(1)) / 2.0

    wan_match = re.match(r'^([\d.]+)万$', raw)
    if wan_match:
        return float(wan_match.group(1)) * 10000

    try:
        return float(raw)
    except ValueError:
        return None


def extract_date(td):
    """从日期td中提取 YYYY-MM-DD"""
    date_div = td.select_one('div.t-date p')
    if date_div:
        m = re.search(r'(\d{4}-\d{2}-\d{2})', date_div.get_text(strip=True))
        if m:
            return m.group(1)
    full = td.get_text(strip=True)
    m = re.search(r'(\d{4}-\d{2}-\d{2})', full)
    return m.group(1) if m else full


def extract_day_label(td):
    """从日期td中提取星期和标签（点映/上映首日等）"""
    spans = td.select('div.t-date p span')
    day = ""
    label = ""
    for i, s in enumerate(spans):
        txt = s.get_text(strip=True)
        if i == 0:
            day = txt
        else:
            label = txt
    return day, label


def parse_html(html_path: str):
    """解析HTML，返回行字典列表"""
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    tbody = soup.select_one('tbody.cm-table-tbody')
    if not tbody:
        print(f"  [跳过] 未找到数据表格")
        return None

    tr_list = tbody.select('tr.cm-table-row')
    if not tr_list:
        print(f"  [跳过] 未找到数据行")
        return None

    col_names = HEADERS[1:]
    rows = []

    for tr in tr_list:
        tds = tr.find_all('td')
        if len(tds) < 26:
            continue

        row = {}
        row["日期"] = extract_date(tds[0])
        row["星期"], row["标签"] = extract_day_label(tds[0])

        for i, td in enumerate(tds[1:27]):
            div = td.find('div')
            raw = div.get_text(strip=True) if div else td.get_text(strip=True)
            name = col_names[i] if i < len(col_names) else f"列_{i+1}"
            is_pct = name in PCT_COLUMNS
            row[name] = convert_value(raw, is_pct)

        rows.append(row)

    return rows


def calc_output_path(input_path: str):
    """
    计算输出路径：将输入路径中的 01_raw 替换为 02_csv。
    - 01_raw/2024/xxx.html -> 02_csv/2024/xxx.csv
    - 01_raw/ame.html      -> 02_csv/ame.csv
    """
    parts = input_path.split(os.sep)
    parts = [p.replace('01_raw', '02_csv') for p in parts]
    output_path = os.sep.join(parts)
    output_path = os.path.splitext(output_path)[0] + '.csv'
    return output_path


def process_one_file(html_path: str):
    """处理单个HTML文件"""
    filename = os.path.basename(html_path)

    movie_name, release_date, rank = extract_movie_info(filename)

    rows = parse_html(html_path)
    if rows is None:
        return False

    csv_path = calc_output_path(html_path)
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FULL_HEADERS)
        writer.writeheader()
        for row in rows:
            row["电影"] = movie_name
            writer.writerow(row)

    print(f"  [完成] 共 {len(rows)} 天 -> {movie_name}")
    return True


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_path = sys.argv[1]

    if os.path.isdir(input_path):
        # 目录模式：批量处理
        print(f"扫描目录: {input_path}")
        html_files = sorted([
            f for f in os.listdir(input_path)
            if f.endswith('.html')
        ])
        if not html_files:
            print("  未找到任何 .html 文件")
            sys.exit(0)

        success = 0
        for fname in html_files:
            html_full = os.path.join(input_path, fname)
            if process_one_file(html_full):
                success += 1

        csv_output_path = calc_output_path(input_path)
        print(f"\n完成: {success}/{len(html_files)} 个文件 -> {csv_output_path}")

    elif os.path.isfile(input_path):
        # 单文件模式
        print(f"处理文件: {input_path}")
        process_one_file(input_path)

    else:
        print(f"错误：路径不存在 -> {input_path}")
        sys.exit(1)


if __name__ == '__main__':
    main()
