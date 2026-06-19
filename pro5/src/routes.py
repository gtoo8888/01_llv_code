"""
API 路由
"""
import json
import re
from pathlib import Path
from fastapi import APIRouter, Body, Query
from fastapi.responses import JSONResponse

from src.config import DB_PATH, STATIC_DIR, BASE_DIR
from src.database import get_conn, get_or_init_status, upsert_status, get_status_for_sessions, get_status_counts, permanent_delete_status
from src.parser import strip_user_metadata

router = APIRouter()

# DeepSeek 归档路径
DEEPSEEK_ARCHIVE = BASE_DIR / "llm_conversation_archives" / "deepseek_data-merged"


@router.get("/api/sessions")
def get_sessions():
    """会话列表"""
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        SELECT
            m.session_key,
            MIN(m.timestamp) as start_time,
            COUNT(m.id) as message_count,
            MAX(m.channel) as channel
        FROM messages m
        GROUP BY m.session_key
        ORDER BY start_time DESC
    """)

    rows = c.fetchall()
    conn.close()

    return {
        "sessions": [
            {
                "session_key": row[0],
                "start_time": row[1],
                "message_count": row[2],
                "channel": row[3] or "unknown",
            }
            for row in rows
        ]
    }


@router.get("/api/sessions/{session_key}/messages")
def get_session_messages(session_key: str):
    """某会话的所有消息"""
    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT channel FROM sessions WHERE session_key = ?", (session_key,))
    row = c.fetchone()
    channel = row[0] if row else "unknown"

    c.execute("""
        SELECT id, role, content, thinking, timestamp, model,
               parent_id, has_tool_calls
        FROM messages
        WHERE session_key = ?
        ORDER BY timestamp ASC
    """, (session_key,))

    rows = c.fetchall()

    c.execute("""
        SELECT id, message_id, tool_name, arguments, result
        FROM tool_calls
        WHERE message_id IN (SELECT id FROM messages WHERE session_key = ?)
    """, (session_key,))
    tc_rows = c.fetchall()

    tool_calls_map = {}
    for tc_row in tc_rows:
        msg_id = tc_row[1]
        if msg_id not in tool_calls_map:
            tool_calls_map[msg_id] = []
        tool_calls_map[msg_id].append({
            "id": tc_row[0],
            "name": tc_row[2],
            "arguments": json.loads(tc_row[3]) if tc_row[3] else {},
            "result": tc_row[4],
        })

    conn.close()

    messages = []
    for row in rows:
        msg_id, role, content, thinking, timestamp, model, parent_id, has_tc = row
        is_system = bool(content and content.startswith("System:"))

        msg = {
            "id": msg_id,
            "role": role,
            "content": strip_user_metadata(content) if role == "user" else (content or ""),
            "timestamp": timestamp,
            "model": model or "",
            "is_system": is_system,
            "parent_id": parent_id,
        }

        if has_tc and msg_id in tool_calls_map:
            msg["tool_calls"] = tool_calls_map[msg_id]

        messages.append(msg)

    return {
        "session_key": session_key,
        "channel": channel,
        "messages": messages,
    }


@router.get("/")
def serve_index():
    """首页 -> 会话列表"""
    from fastapi.responses import FileResponse
    return FileResponse(STATIC_DIR / "index.html")


@router.get("/sessions")
def serve_sessions_page():
    """会话列表页（别名）"""
    from fastapi.responses import FileResponse
    return FileResponse(STATIC_DIR / "index.html")


# ═══════════════════════════════════════════════
# DeepSeek 对话浏览 API
# ═══════════════════════════════════════════════

@router.get("/api/deepseek/structure")
def deepseek_structure():
    """返回年月目录树：{ year: [month_label, ...] }"""
    years = {}
    if not DEEPSEEK_ARCHIVE.exists():
        return {"years": years}
    for year_dir in sorted(DEEPSEEK_ARCHIVE.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        months = []
        for month_dir in sorted(year_dir.iterdir()):
            if month_dir.is_dir():
                months.append(month_dir.name)
        years[year_dir.name] = months
    return {"years": years}


@router.get("/api/deepseek/sessions")
def deepseek_sessions(year: str = Query(...), month: str = Query(...),
                      status: str = Query(None)):
    """获取指定年月的会话列表，从 Markdown 文件头部解析元数据

    status 参数：
      - raw       → 仅待处理
      - archived  → 仅已归档
      - deleted   → 仅回收站
      - all       → 全部（含 deleted_permanent）
      - 不传       → 默认过滤 deleted 和 deleted_permanent
    """
    month_dir = DEEPSEEK_ARCHIVE / year / month
    if not month_dir.exists():
        return {"sessions": [], "year": year, "month": month}

    sessions = []
    for f in sorted(month_dir.glob("*.md")):
        if f.name.startswith("_"):
            continue  # 跳过 _index.md / _data.json

        with open(f, "r", encoding="utf-8") as fh:
            header = "".join(fh.readline() for _ in range(10))

        title = ""
        session_id = ""
        msg_count = 0
        model = ""
        date = f.name[:10]

        m = re.search(r"^#\s+(.+)$", header, re.MULTILINE)
        if m:
            title = m.group(1).strip()

        m = re.search(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            header,
        )
        if m:
            session_id = m.group(0)

        m = re.search(r"消息[：:][\s\*]*(\d+)\s*条", header)
        if m:
            msg_count = int(m.group(1))

        m = re.search(r"模型[：:][\s*`]*([^`\n*]+)", header)
        if m:
            model = m.group(1).strip()

        sessions.append({
            "id": session_id,
            "title": title or f.stem,
            "date": date,
            "message_count": msg_count,
            "model": model,
        })

    # 批量查询状态
    conn = get_conn()
    ids = [s["id"] for s in sessions if s["id"]]
    status_map = get_status_for_sessions(conn, ids)
    # 懒初始化未入库的会话
    for s in sessions:
        if s["id"] and s["id"] not in status_map:
            st = get_or_init_status(conn, s["id"])
            if st:
                status_map[s["id"]] = st
        s["status"] = (status_map.get(s["id"], {}) or {}).get("status", "raw")
    conn.close()

    # 按 status 筛选
    hidden_statuses = {"deleted", "deleted_permanent"}
    if status == "all":
        pass  # 全部显示
    elif status:
        sessions = [s for s in sessions if s.get("status") == status]
    else:
        sessions = [s for s in sessions if s.get("status") not in hidden_statuses]

    return {"sessions": sessions, "year": year, "month": month}


# ═══════════════════════════════════════════════
# DeepSeek 全量会话 API（必须在 {session_id} 前注册）
# ═══════════════════════════════════════════════


@router.get("/api/deepseek/sessions/all")
def deepseek_sessions_all():
    """返回所有 DeepSeek 对话（含状态），用于对话管理视图"""
    all_sessions = []
    seen_ids = set()

    for year_dir in sorted(DEEPSEEK_ARCHIVE.iterdir(), reverse=True):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        year = year_dir.name
        for month_dir in sorted(year_dir.iterdir(), reverse=True):
            if not month_dir.is_dir():
                continue
            data_file = month_dir / "_data.json"
            if not data_file.exists():
                continue
            try:
                with open(data_file, "r", encoding="utf-8") as f:
                    sessions = json.load(f)
            except (json.JSONDecodeError, IOError):
                continue

            for s in sessions:
                sid = s.get("id", "")
                if not sid or sid in seen_ids:
                    continue
                seen_ids.add(sid)

                inserted = s.get("inserted_at", "") or ""
                models = s.get("models", []) or []

                all_sessions.append({
                    "id": sid,
                    "title": s.get("title", "") or "",
                    "date": inserted[:10] if inserted else "",
                    "message_count": s.get("message_count", 0) or 0,
                    "model": models[0] if models else "",
                })

    # 批量查询状态
    if all_sessions:
        conn = get_conn()
        ids = [s["id"] for s in all_sessions]
        status_map = get_status_for_sessions(conn, ids)
        for s in all_sessions:
            st = status_map.get(s["id"]) or get_or_init_status(conn, s["id"])
            s["status"] = st["status"] if st else "raw"
            s["notes"] = st["notes"] if st else ""
        conn.close()

    return {"sessions": all_sessions, "count": len(all_sessions)}


@router.get("/api/deepseek/sessions/{session_id}")
def deepseek_session_content(session_id: str):
    """获取单个对话内容，按 ID 前缀匹配"""
    for f in DEEPSEEK_ARCHIVE.glob("**/*.md"):
        if f.name.startswith("_"):
            continue
        with open(f, "r", encoding="utf-8") as fh:
            first_block = fh.read(2000)
        if session_id in first_block:
            with open(f, "r", encoding="utf-8") as fh:
                content = fh.read()
            rel_path = str(f.relative_to(DEEPSEEK_ARCHIVE))
            return {
                "id": session_id,
                "filename": f.name,
                "path": rel_path,
                "abs_path": str(f.resolve()),
                "content": content,
            }

    return JSONResponse({"error": f"Session '{session_id}' not found"}, status_code=404)


@router.get("/api/deepseek/sessions-by-date")
def deepseek_sessions_by_date(date: str = Query(...)):
    """按具体日期查询会话（文件名前缀匹配）"""
    results = []
    seen_ids = set()

    for f in DEEPSEEK_ARCHIVE.glob(f"**/{date}_*.md"):
        if f.name.startswith("_"):
            continue

        meta = _parse_file_metadata(f)
        if meta is None or meta["id"] in seen_ids:
            continue
        seen_ids.add(meta["id"])

        rel = f.relative_to(DEEPSEEK_ARCHIVE)
        parts = rel.parts
        results.append({
            **meta,
            "year": parts[0] if len(parts) > 0 else "",
            "month": parts[1] if len(parts) > 1 else "",
        })

    # 批量查询状态
    if results:
        conn = get_conn()
        ids = [r["id"] for r in results if r["id"]]
        status_map = get_status_for_sessions(conn, ids)
        for r in results:
            if r["id"]:
                st = status_map.get(r["id"]) or get_or_init_status(conn, r["id"])
                r["status"] = st["status"] if st else "raw"
        conn.close()

    results.sort(key=lambda x: x["date"], reverse=True)
    return {"sessions": results, "date": date, "count": len(results)}


@router.get("/api/deepseek/dates")
def deepseek_dates(year: str = Query(...), month: str = Query(...)):
    """获取某月有对话的日期列表"""
    active_dates = {}  # { "YYYY-MM-DD": count }

    # 查找对应的月份目录
    for year_dir in DEEPSEEK_ARCHIVE.iterdir():
        if not year_dir.is_dir() or year_dir.name != year:
            continue
        for month_dir in year_dir.iterdir():
            if not month_dir.is_dir():
                continue
            month_num = month_dir.name[:2]
            if month_num != month:
                continue

            for f in month_dir.glob("*.md"):
                if f.name.startswith("_"):
                    continue
                date_str = f.name[:10]  # "YYYY-MM-DD"
                active_dates[date_str] = active_dates.get(date_str, 0) + 1

    return {"dates": active_dates, "year": year, "month": month}


@router.get("/api/deepseek/stats")
def deepseek_stats():
    """获取 DeepSeek 对话统计的真实数据"""
    from datetime import datetime, timedelta

    total_conversations = 0
    total_messages = 0
    total_user_messages = 0
    min_date = None
    max_date = None
    models = {}
    monthly_counts = {}  # "YYYY-MM": count
    daily_conversations = {}  # "YYYY-MM-DD": count
    length_buckets = {"2": 0, "3-6": 0, "7-10": 0, "11-20": 0, "21-30": 0, "31+": 0}
    hourly_all = {h: 0 for h in range(24)}  # 总对话数/小时
    hourly_weekday = {h: 0 for h in range(24)}
    hourly_weekend = {h: 0 for h in range(24)}
    hourly_msg_total = {h: 0 for h in range(24)}  # 消息总数/小时（用于计算平均条数）
    duration_buckets = {"0-5min": 0, "5-15min": 0, "15-30min": 0, "30-60min": 0, "1-2h": 0, "2h+": 0}
    scatter_data = []  # 散点图数据点
    model_durations = {}  # model -> {"total_min": 0, "count": 0}

    for year_dir in sorted(DEEPSEEK_ARCHIVE.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        year = year_dir.name
        for month_dir in sorted(year_dir.iterdir()):
            if not month_dir.is_dir():
                continue
            data_file = month_dir / "_data.json"
            if not data_file.exists():
                continue
            try:
                with open(data_file, "r", encoding="utf-8") as f:
                    sessions = json.load(f)
            except (json.JSONDecodeError, IOError):
                continue

            month_key = f"{year}-{month_dir.name[:2]}"
            if month_key not in monthly_counts:
                monthly_counts[month_key] = 0

            for s in sessions:
                total_conversations += 1
                mc = s.get("message_count", 0) or 0
                total_messages += mc
                total_user_messages += s.get("user_message_count", 0) or 0

                inserted = s.get("inserted_at", "") or ""
                if inserted:
                    if not min_date or inserted < min_date:
                        min_date = inserted
                    if not max_date or inserted > max_date:
                        max_date = inserted
                    date_key = inserted[:10]
                    daily_conversations[date_key] = daily_conversations.get(date_key, 0) + 1

                    # 24h 时段统计
                    try:
                        dt = datetime.strptime(inserted[:19], "%Y-%m-%dT%H:%M:%S")
                        hour = dt.hour
                        wd = dt.weekday()
                        is_weekend = wd >= 5
                        hourly_all[hour] += 1
                        if is_weekend:
                            hourly_weekend[hour] += 1
                        else:
                            hourly_weekday[hour] += 1
                        hourly_msg_total[hour] += mc
                    except (ValueError, IndexError):
                        pass

                # 对话时长
                updated = s.get("updated_at", "") or ""
                if inserted and updated:
                    try:
                        d_start = datetime.strptime(inserted[:19], "%Y-%m-%dT%H:%M:%S")
                        d_end = datetime.strptime(updated[:19], "%Y-%m-%dT%H:%M:%S")
                        dur_min = (d_end - d_start).total_seconds() / 60

                        if dur_min <= 5:
                            duration_buckets["0-5min"] += 1
                        elif dur_min <= 15:
                            duration_buckets["5-15min"] += 1
                        elif dur_min <= 30:
                            duration_buckets["15-30min"] += 1
                        elif dur_min <= 60:
                            duration_buckets["30-60min"] += 1
                        elif dur_min <= 120:
                            duration_buckets["1-2h"] += 1
                        else:
                            duration_buckets["2h+"] += 1

                        scatter_data.append({
                            "duration_min": round(dur_min, 1),
                            "message_count": mc,
                            "model": (s.get("models", ["unknown"]) or ["unknown"])[0],
                            "title": s.get("title", ""),
                        })

                        for m in (s.get("models", []) or []):
                            if m not in model_durations:
                                model_durations[m] = {"total_min": 0, "count": 0}
                            model_durations[m]["total_min"] += dur_min
                            model_durations[m]["count"] += 1
                    except (ValueError, IndexError):
                        pass

                for m in (s.get("models", []) or []):
                    models[m] = models.get(m, 0) + 1

                if mc == 2:
                    length_buckets["2"] += 1
                elif mc <= 6:
                    length_buckets["3-6"] += 1
                elif mc <= 10:
                    length_buckets["7-10"] += 1
                elif mc <= 20:
                    length_buckets["11-20"] += 1
                elif mc <= 30:
                    length_buckets["21-30"] += 1
                else:
                    length_buckets["31+"] += 1

                monthly_counts[month_key] += 1

    # 时间跨度
    days = 0
    if min_date and max_date:
        d1 = datetime.strptime(min_date[:10], "%Y-%m-%d")
        d2 = datetime.strptime(max_date[:10], "%Y-%m-%d")
        days = (d2 - d1).days + 1

    # 月度趋势（按时间排序）
    monthly_trend = [
        {"month": mk, "count": monthly_counts[mk]}
        for mk in sorted(monthly_counts.keys())
    ]

    # 模型分布
    model_distribution = [
        {"name": k, "count": v}
        for k, v in sorted(models.items(), key=lambda x: -x[1])
    ]

    # 长度分布
    length_distribution = [
        {"label": "2 条", "count": length_buckets["2"], "color": "#b8d4f0"},
        {"label": "3-6 条", "count": length_buckets["3-6"], "color": "#4a90d9"},
        {"label": "7-10 条", "count": length_buckets["7-10"], "color": "#50c878"},
        {"label": "11-20 条", "count": length_buckets["11-20"], "color": "#f5a623"},
        {"label": "21-30 条", "count": length_buckets["21-30"], "color": "#ff7a59"},
        {"label": "30+ 条", "count": length_buckets["31+"], "color": "#d93025"},
    ]

    # 热力图：最近 12 周（84 天）
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    heatmap = []
    for w in range(12):
        week = []
        for d in range(7):
            cell_date = today - timedelta(days=(11 - w) * 7 + (6 - d))
            date_str = cell_date.strftime("%Y-%m-%d")
            count = daily_conversations.get(date_str, 0)
            week.append(count)
        heatmap.append(week)

    # 可用年份（从 daily_conversations 提取）
    available_years = sorted(set(k[:4] for k in daily_conversations))

    # 归档统计
    conn = get_conn()
    archive_counts = get_status_counts(conn)
    conn.close()
    raw = archive_counts.get("raw", 0)
    archived = archive_counts.get("archived", 0)
    deleted = archive_counts.get("deleted", 0)
    deleted_permanent = archive_counts.get("deleted_permanent", 0)
    total_db = archive_counts.get("total", 0)
    completion_rate = round(archived / (raw + archived) * 100, 1) if (raw + archived) > 0 else 0

    return {
        "total_conversations": total_conversations,
        "archive_stats": {
            "total": total_db,
            "raw": raw,
            "archived": archived,
            "deleted": deleted,
            "deleted_permanent": deleted_permanent,
            "completion_rate": completion_rate,
        },
        "total_messages": total_messages,
        "total_user_messages": total_user_messages,
        "time_span_days": days,
        "model_count": len(models),
        "min_date": min_date[:10] if min_date else "",
        "max_date": max_date[:10] if max_date else "",
        "monthly_trend": monthly_trend,
        "model_distribution": model_distribution,
        "daily_conversations": daily_conversations,
        "available_years": available_years,
        "length_distribution": length_distribution,
        "heatmap": heatmap,  # 12 weeks × 7 days
        "hourly_distribution": {
            "all": [{"hour": h, "count": hourly_all[h], "avg_messages": round(hourly_msg_total[h] / hourly_all[h], 1) if hourly_all[h] else 0} for h in range(24)],
            "weekday": [{"hour": h, "count": hourly_weekday[h]} for h in range(24)],
            "weekend": [{"hour": h, "count": hourly_weekend[h]} for h in range(24)],
        },
        "duration_distribution": [
            {"label": "0-5 min", "count": duration_buckets["0-5min"], "color": "#4a90d9"},
            {"label": "5-15 min", "count": duration_buckets["5-15min"], "color": "#50c878"},
            {"label": "15-30 min", "count": duration_buckets["15-30min"], "color": "#f5a623"},
            {"label": "30-60 min", "count": duration_buckets["30-60min"], "color": "#ff7a59"},
            {"label": "1-2 h", "count": duration_buckets["1-2h"], "color": "#d973bf"},
            {"label": "2h+", "count": duration_buckets["2h+"], "color": "#d93025"},
        ],
        "scatter_data": scatter_data,
        "model_duration_avg": [
            {"name": k, "avg_min": round(v["total_min"] / v["count"], 1), "count": v["count"]}
            for k, v in sorted(model_durations.items(), key=lambda x: x[1]["total_min"] / x[1]["count"], reverse=True)
        ],
    }


@router.get("/api/deepseek/stats/topics")
def deepseek_topic_stats():
    """读取分类概要 CSV 返回主题分布"""
    import csv
    csv_path = DEEPSEEK_ARCHIVE / "category_summary.csv"
    if not csv_path.exists():
        return {"parents": [], "total": 0}

    parent_map = {}
    total = 0
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            parent = row["parent"]
            child = row["child"]
            count = int(row["count"])
            if parent not in parent_map:
                parent_map[parent] = {"parent": parent, "children": [], "total": 0}
            parent_map[parent]["children"].append({"child": child, "count": count})
            parent_map[parent]["total"] += count
            total += count

    parents = list(parent_map.values())
    for p in parents:
        p["pct"] = round(p["total"] / total * 100) if total > 0 else 0

    return {"parents": parents, "total": total}


def _parse_file_metadata(file_path):
    """从 Markdown 文件头部解析元数据"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            header = "".join(f.readline() for _ in range(10))
    except IOError:
        return None

    title = ""
    session_id = ""
    msg_count = 0
    model = ""
    date = file_path.name[:10]

    m = re.search(r"^#\s+(.+)$", header, re.MULTILINE)
    if m:
        title = m.group(1).strip()

    m = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", header)
    if m:
        session_id = m.group(0)

    m = re.search(r"消息[：:][\s\*]*(\d+)\s*条", header)
    if m:
        msg_count = int(m.group(1))

    m = re.search(r"模型[：:][\s*`]*([^`\n*]+)", header)
    if m:
        model = m.group(1).strip()

    if not title and not session_id:
        return None

    return {
        "id": session_id,
        "title": title or file_path.stem,
        "date": date,
        "message_count": msg_count,
        "model": model,
    }


def _extract_snippet(content, query_lower, context=80):
    """从内容中提取匹配位置附近的片段"""
    idx = content.lower().find(query_lower)
    if idx == -1:
        return content[:200]

    start = max(0, idx - context)
    end = min(len(content), idx + len(query_lower) + context)

    snippet = content[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(content):
        snippet += "..."

    return snippet.strip()


@router.get("/api/deepseek/search")
def deepseek_search(q: str = Query(...), mode: str = Query("title")):
    """搜索 DeepSeek 对话
    - mode=title: 按标题搜索
    - mode=full:  全文搜索
    """
    if not q.strip():
        return {"results": [], "query": q, "mode": mode, "count": 0}

    q_lower = q.strip().lower()
    results = []
    seen_ids = set()

    if mode == "full":
        # 全文搜索：逐文件 grep
        for year_dir in sorted(DEEPSEEK_ARCHIVE.iterdir(), reverse=True):
            if not year_dir.is_dir() or not year_dir.name.isdigit():
                continue
            year = year_dir.name
            for month_dir in sorted(year_dir.iterdir(), reverse=True):
                if not month_dir.is_dir():
                    continue

                for f in sorted(month_dir.glob("*.md"), reverse=True):
                    if f.name.startswith("_"):
                        continue

                    meta = _parse_file_metadata(f)
                    if meta is None or meta["id"] in seen_ids:
                        continue

                    try:
                        with open(f, "r", encoding="utf-8") as fh:
                            content = fh.read()
                    except IOError:
                        continue

                    if q_lower not in content.lower():
                        continue

                    seen_ids.add(meta["id"])
                    snippet = _extract_snippet(content, q_lower)
                    results.append({
                        **meta,
                        "snippet": snippet,
                        "year": year,
                        "month": month_dir.name,
                    })

        # 批量查询状态
        if results:
            conn = get_conn()
            ids = [r["id"] for r in results if r["id"]]
            status_map = get_status_for_sessions(conn, ids)
            for r in results:
                if r["id"]:
                    st = status_map.get(r["id"]) or get_or_init_status(conn, r["id"])
                    r["status"] = st["status"] if st else "raw"
            conn.close()

        # 按时间倒序
        results.sort(key=lambda x: x["date"], reverse=True)
        return {"results": results, "query": q, "mode": mode, "count": len(results)}

    # 标题搜索：扫描所有 _data.json
    for year_dir in sorted(DEEPSEEK_ARCHIVE.iterdir(), reverse=True):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        year = year_dir.name
        for month_dir in sorted(year_dir.iterdir(), reverse=True):
            if not month_dir.is_dir():
                continue

            data_file = month_dir / "_data.json"
            if not data_file.exists():
                continue

            try:
                with open(data_file, "r", encoding="utf-8") as f:
                    sessions = json.load(f)
            except (json.JSONDecodeError, IOError):
                continue

            for s in sessions:
                sid = s.get("id", "")
                if sid in seen_ids:
                    continue
                title = s.get("title", "") or ""
                if q_lower in title.lower():
                    seen_ids.add(sid)
                    results.append({
                        "id": sid,
                        "title": title,
                        "date": (s.get("inserted_at", "") or "")[:10],
                        "message_count": s.get("message_count", 0),
                        "models": s.get("models", []),
                        "year": year,
                        "month": month_dir.name,
                        "snippet": "",
                    })

    # 批量查询状态
    if results:
        conn = get_conn()
        ids = [r["id"] for r in results if r["id"]]
        status_map = get_status_for_sessions(conn, ids)
        for r in results:
            if r["id"]:
                st = status_map.get(r["id"]) or get_or_init_status(conn, r["id"])
                r["status"] = st["status"] if st else "raw"
        conn.close()

    # 按时间倒序
    results.sort(key=lambda x: x["date"], reverse=True)

    return {"results": results, "query": q, "mode": mode, "count": len(results)}


# ═══════════════════════════════════════════════
# DeepSeek 对话状态管理 API
# ═══════════════════════════════════════════════


@router.get("/api/deepseek/sessions/{session_id}/status")
def deepseek_session_status(session_id: str):
    """获取单条对话的状态信息（含笔记）"""
    conn = get_conn()
    st = get_or_init_status(conn, session_id)
    conn.close()

    if not st:
        return JSONResponse({"error": f"Session '{session_id}' not found"}, status_code=404)

    return {
        "id": st["id"],
        "status": st["status"],
        "archived_at": st["archived_at"],
        "deleted_at": st["deleted_at"],
        "notes": st["notes"] or "",
    }


@router.patch("/api/deepseek/sessions/{session_id}/status")
def deepseek_update_status(session_id: str, body: dict = Body(...)):
    """
    更新对话状态。

    请求体：
    {
        "status": "archived" | "deleted" | "raw",
        "notes": "可选的知识提炼笔记"
    }
    """
    new_status = body.get("status", "")
    notes = body.get("notes", "")

    if new_status not in ("raw", "archived", "deleted"):
        return JSONResponse({"error": f"Invalid status '{new_status}'"}, status_code=400)

    conn = get_conn()
    st = upsert_status(conn, session_id, new_status, notes)
    conn.close()

    return {
        "id": st["id"],
        "status": st["status"],
        "archived_at": st["archived_at"],
        "deleted_at": st["deleted_at"],
        "notes": st["notes"] or "",
    }


@router.delete("/api/deepseek/sessions/{session_id}/permanent")
def deepseek_permanent_delete(session_id: str):
    """
    永久删除对话（仅标记为 deleted_permanent，不操作原始 .md 文件）。
    仅在回收站中执行，前端需二次确认。
    """
    conn = get_conn()
    permanent_delete_status(conn, session_id)
    conn.close()

    return {"ok": True, "id": session_id, "status": "deleted_permanent"}
