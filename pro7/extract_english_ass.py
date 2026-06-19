#!/usr/bin/env python3

# 从双语 ASS 字幕中提取英文字幕


import re
import os

# 样式模板：纯英文输出样式
# 可按需修改字体/大小/颜色
ENGLISH_STYLE = (
    "Style: English,Times New Roman,18,&H00FFFFFF,"
    "&H00000000,&H00000000,&H00000000,"
    "0,0,0,0,100,100,0,0.00,1,2,1,2,5,5,15,1"
)

# 需要过滤掉的中文字体（用于排除歌词/场景内嵌中文叠加）
CHINESE_FONT_PATTERNS = [
    r'\\fn方正',
    r'\\fn微软雅黑',
    r'\\fn黑体',
    r'\\fn楷体',
    r'\\fn华文',
    r'\\fn文泉驿',
]


def is_chinese_line(text: str) -> bool:
    """检测文本是否包含中文字符"""
    return bool(re.search(r'[\u4e00-\u9fff]', text))


def should_skip_line(line: str) -> bool:
    """判断该行是否应该跳过（中文嵌入行）"""
    for pattern in CHINESE_FONT_PATTERNS:
        if re.search(pattern, line):
            return True
    return False


def extract_english_from_dialogue(line: str) -> str:
    m = re.match(r'(Dialogue: .+?,,)(.+)', line)
    if not m:
        return line

    prefix = m.group(1)
    text_part = m.group(2)

    eng_match = re.search(r'\\N\{\\r[^}]+\}(.+)', text_part)
    if eng_match:
        return prefix + eng_match.group(1)

    # 如果行内没有 \N{\r...} 但也没有中文，直接返回（可能是纯英文行）
    if not is_chinese_line(text_part):
        return line

    return line  # 保留原样（避免误删）


def process_ass(content: str, english_style: str = ENGLISH_STYLE) -> str:
    """
    处理整个 ASS 文件内容，输出纯英文字幕。
    """
    lines = content.split('\n')
    output_lines = []
    style_replaced = False

    for line in lines:
        # Dialogue 行：提取英文部分
        if line.startswith('Dialogue:'):
            if should_skip_line(line):
                continue  # 跳过中文嵌入行（歌词/标题卡）
            line = extract_english_from_dialogue(line)

        # 更新 Title
        elif line.startswith('Title:'):
            line = 'Title: extracted-English'
        elif line.startswith('Original Script:'):
            line = 'Original Script: extracted'

        # 跳过中文字体样式 Default（避免重名冲突）
        elif line.startswith('Style: Default,'):
            continue

        # 原文字幕样式 → English
        elif line.startswith('Style: 原文字幕') or \
                line.startswith('Style: Original') or \
                re.match(r'Style: \w+,.*Calibri.*Italic=1', line):
            if not style_replaced:
                line = english_style
                style_replaced = True
            else:
                continue  # 已有一个 English 样式了，跳过多余的

        output_lines.append(line)

    return '\n'.join(output_lines)


if __name__ == '__main__':
    input_path = r"test.ass"
    name, ext = os.path.splitext(input_path)
    output_path = f"{name}.EN.ass"

    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    result = process_ass(content)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result)

    print(f"output_path: {output_path}")
