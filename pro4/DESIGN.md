# 语音转文字工具 — 设计文档

## 1. 项目概述

**项目名称**：voice2text  
**项目路径**：`/data_sdb/openclaw/02_llv_generated/01_llv_code/pro4/`  
**定位**：纯 Python CLI 工具，扫描指定文件夹，将音频批量转写为同名 `.txt` 文件  
**核心引擎**：`faster-whisper small` + `OpenCC`（繁简转换）

---

## 2. 功能范围

1. **文件夹扫描**：遍历指定路径，支持格式（m4a / mp3 / wav / flac / ogg / webm）
2. **批量转写**：逐个调用 faster-whisper 处理音频
3. **繁简转换**：通过 OpenCC 将繁体中文转为简体中文
4. **结果输出**：转写结果保存为同名 `.txt`（如 `16.m4a` → `16.txt`），存放在原音频同一目录

---

## 3. 程序结构

```
pro4/
├── main.py              # CLI 入口，扫描文件夹 + 调度转写
├── transcribe.py        # 转写核心逻辑
├── converter.py         # OpenCC 繁简转换封装
└── README.md            # 使用说明
```

---

## 4. 核心逻辑

### 4.1 转写流程

```
指定文件夹路径
      │
      ▼
扫描目录下所有音频文件（支持格式过滤）
      │
      ▼
遍历每个音频文件
      │
      ├── faster-whisper small 转写
      ├── OpenCC 繁简转换
      └── 输出同名 .txt 到同目录
      │
      ▼
全部处理完毕，汇总报告
```

### 4.2 输出示例

```
开始处理文件夹: /path/to/audio
找到 3 个音频文件

[1/3] 正在处理: 16.m4a
16.m4a 转写完成 → 16.txt ✓

[2/3] 正在处理: meeting.mp3
meeting.mp3 转写完成 → meeting.txt ✓

[3/3] 正在处理: record.ogg
record.ogg 转写完成 → record.txt ✓

全部完成，共处理 3 个文件
```

---

## 5. CLI 用法

```bash
python main.py /path/to/your/audio/folder
```

---

## 6. 依赖

- `faster-whisper`
- `opencc`
- `ffmpeg`（系统依赖，音频格式处理）

运行环境：`conda activate whisper_dashboard`

---

## 7. 约束与限制

- 模型固定为 `small`，不支持切换
- 不做文件上传功能，程序读取指定文件夹的现有文件
- 不做实时流式处理，批量扫描、逐个转写

---

> 文档版本：v0.2（简化版）  
> 更新日期：2026-03-22
