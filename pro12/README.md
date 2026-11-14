# Android 分析工具

> 围绕 Android 设备做分析与自动化的一组工具。目前只做了文件传输，后续会继续加别的方向。
>
> 所有工具都是**只读分析 + 自动化操作**，不需要 root，不修改系统。

---

## 目录结构

```
pro12/
├── src/          传输工具的主体代码
│   └── runtime/      运行时产物（state / log / metrics，可整目录删）
├── script/       零散工具脚本
├── docs/         正式文档
├── dev/          本地开发过程记录（不入库）
└── out/          截图等杂项输出
```

`runtime/` 和 `out/` 不是职责重叠：`runtime/` 是这个工具的账本（状态、日志、指标），
`out/` 是别的工具产出的杂物。前者结构固定，后者随手扔。

---

## 环境

### 依赖

| 依赖 | 版本要求 | 说明 |
|---|---|---|
| `adb` | 任意近期版本 | 已验证 `1.0.41`（`34.0.4-debian`），apt 装的 `/usr/bin/adb` |
| `python3` | **≥ 3.11** | 用到标准库 `tomllib`，**无第三方依赖，不用 pip install 任何东西** |
| `tar` / `stat` | 任意 | 主机端只用来做 tar 头校验，GNU tar 1.35 已验证 |

手机端**不需要 Python**，也不需要 root。

### Python 版本：必须 3.11 以上

这是唯一一个容易踩的坑。`config.toml` 用标准库 `tomllib` 解析，而它是 **Python 3.11
才引入的**。低于 3.11 会直接报 `ModuleNotFoundError: No module named 'tomllib'`，
代码里**故意不做回退**（不引 `tomli`），配错版本就应该立刻报错。

本机实际情况：

| 解释器 | 版本 | 能跑吗 |
|---|---|---|
| `/usr/bin/python3` | 3.12.3 | ✅ 可以直接用 |
| conda `base` | **3.10.9** | ❌ 缺 `tomllib` |
| conda `android_analyze` | 3.12.16 | ✅ 推荐 |

**如果你在 conda `base` 里跑，一定会失败**——这是最容易犯的错。

### 用 conda 环境（推荐）

项目专用环境已经建好，名为 `android_analyze`：

```bash
conda activate android_analyze
cd pro12/src
./run.sh weixin
```

从零重建同样的环境：

```bash
conda create -n android_analyze python=3.12 -y
conda activate android_analyze
```

### 不用 conda 也行

系统自带的 `/usr/bin/python3` 是 3.12.3，已经满足要求。只要注意别在
conda `base` 里执行即可：

```bash
cd pro12/src
/usr/bin/python3 prepare.py --dataset weixin
```

### 自检

动手之前先确认两件事，能省掉大部分"莫名其妙的报错"：

```bash
# 1. Python 版本够不够
python3 -c "import tomllib, sys; print(sys.version)"

# 2. 手机连上没有（要看到 device，不是 unauthorized，也不是空）
adb devices
```

`adb devices` 为空 → 线/口/USB 调试没开；显示 `unauthorized` → 手机上没点允许。

---

## 工具一览

| 工具 | 作用 | 启动 |
|---|---|---|
| **传输工具** | 大批量文件从手机拉回主机，针对 USB 2.0 做过极限优化 | `cd src && ./run.sh <数据集>` |
| **设备配置** | 一键设置手机（关动画、屏幕常亮、超时等），可只检测不修改 | `./script/mob.sh`（带 `check` 只比对）|
| **截图流水线** | 一次调用拿到判断页面所需的全部上下文，输出 JSON | `./script/shot.py [--ui] [--scale 0.5]` |

---

## 传输工具

```bash
cd src
./run.sh                    # 默认数据集
./run.sh weixin             # 指定数据集
./run.sh weixin --dst ~/x   # 指定落盘目录
```

覆盖 7500+ 文件 / 33.9 GB 的场景，实测吞吐 **44.2 MiB/s**，已达 USB 2.0
链路物理上限的 92%（折算协议开销后 98%）。

---

## 文档

- 正式文档在 `docs/`，目前有传输工具的完整使用手册
- `dev/` 是本地开发过程记录，不入库
