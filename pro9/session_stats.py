#!/usr/bin/env python3
"""
session_stats.py - 通过 RPC 调取 chat.history 并输出会话统计信息（JSON）

用法:
    conda activate openclaw_tool
    python session_stats.py --token <token>
"""

import argparse
import asyncio
import json
import os
import sys
import traceback
from datetime import datetime, timezone

import websockets


# ── DeepSeek 官方定价（人民币 ¥/1M tokens，2026-06-19）──
DEEPSEEK_PRICING = {
    "v4-flash": {
        "input_cache_miss": 1.00,   # 缓存未命中
        "input_cache_hit": 0.02,    # 缓存命中
        "output": 2.00,
    },
    "v4-pro": {
        "input_cache_miss": 3.00,
        "input_cache_hit": 0.025,
        "output": 6.00,
    },
}

# 未知模型默认值（保守按 Flash 定价）
DEFAULT_PRICING = DEEPSEEK_PRICING["v4-flash"]


# 支持多个会话 ID，脚本会逐一导出
SESSION_KEYS = [
    "agent:main:dashboard:63f3f8ce-6815-4dd5-88b8-742b29a16b83",
    "agent:main:dashboard:eae19d5d-8f0a-46e3-9e84-4e5d2d0e649e",
    "agent:main:dashboard:8ee386bb-7e59-4f7f-9a83-53f7581d3591",
    "agent:main:dashboard:689c7b46-74c0-48cb-b96a-40a956f82118",
    "agent:main:dashboard:515af2ce-23b1-431c-9fa7-0e9e91369985",
]

# 输出目录（自动创建）
OUTPUT_DIR = "openclaw_rpc_output"


def get_model_price_key(model_name: str | None) -> str:
    """根据模型名匹配定价表 key，默认返回 v4-flash"""
    if not isinstance(model_name, str):
        return "v4-flash"
    name = model_name.lower()
    if "pro" in name:
        return "v4-pro"
    return "v4-flash"


def compute_cost_cny(input_tokens: int, output_tokens: int, cache_read: int, model: str | None) -> float:
    """
    根据 DeepSeek 官方定价计算人民币成本。

    计费逻辑：
    - 缓存命中（cache_hit）：cache_read
    - 缓存未命中（cache_miss）：input_tokens（每次请求的新输入）
      注意：input_tokens 是每次请求的"新输入"部分，cache_read 是跨请求的累计缓存上下文。
      但在 DeepSeek API 中，input 是本次请求的总输入 token，
      cacheRead 是其中命中缓存的 token。所以 cache_miss = max(0, input_tokens - cache_read)。
    - 输出：output_tokens
    """
    pricing_key = get_model_price_key(model)
    p = DEEPSEEK_PRICING.get(pricing_key, DEFAULT_PRICING)

    # DeepSeek 每条消息的 input 是"新输入"，cacheRead 是"缓存的上下文"
    # 对于 API 计费：input 是 cache_miss，cacheRead 是 cache_hit
    cost = (
        (input_tokens / 1_000_000) * p["input_cache_miss"]
        + (cache_read / 1_000_000) * p["input_cache_hit"]
        + (output_tokens / 1_000_000) * p["output"]
    )
    return round(cost, 4)


def compute_stats(messages: list) -> dict:
    """从消息列表中提取统计信息"""
    if not isinstance(messages, list) or not messages:
        return {}

    # ── 消息统计 ──
    total = len(messages)
    user_count = sum(1 for m in messages if m.get("role") == "user")
    assistant_count = sum(1 for m in messages if m.get("role") == "assistant")
    tool_count = sum(1 for m in messages if m.get("role") == "toolResult")

    # ── 工具调用统计 ──
    tool_dist = {}
    tool_errors = 0
    for m in messages:
        content = m.get("content")
        if m.get("role") == "assistant" and isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "toolCall":
                    name = block.get("name", "unknown")
                    tool_dist[name] = tool_dist.get(name, 0) + 1
        if m.get("role") == "toolResult":
            # isError 或 error 字段表示工具执行出错
            if m.get("isError") or m.get("error") or m.get("is_error"):
                tool_errors += 1

    total_tool_calls = sum(tool_dist.values())
    distinct_tools = len(tool_dist)

    # ── 时间范围 ──
    timestamps = []
    for m in messages:
        ts = m.get("createdAt") or m.get("timestamp")
        if ts is not None:
            timestamps.append(ts)
    timestamps.sort()

    duration_info = {}
    if len(timestamps) >= 2:
        try:
            raw_start = timestamps[0]
            raw_end = timestamps[-1]
            if isinstance(raw_start, (int, float)):
                start_dt = datetime.fromtimestamp(raw_start / 1000)
                end_dt = datetime.fromtimestamp(raw_end / 1000)
                start_str = start_dt.isoformat()
                end_str = end_dt.isoformat()
            else:
                start_str = str(raw_start)
                end_str = str(raw_end)
                fmt = "%Y-%m-%dT%H:%M:%S" if "T" in start_str else "%Y-%m-%d %H:%M:%S"
                start_dt = datetime.strptime(start_str[:19], fmt)
                end_dt = datetime.strptime(end_str[:19], fmt)
            seconds = int((end_dt - start_dt).total_seconds())
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            duration_info = {
                "start": start_str,
                "end": end_str,
                "seconds": seconds,
                "readable": f"{hours}h {minutes}m",
            }
        except (ValueError, IndexError, TypeError):
            pass

    # ── Token 统计与成本计算（累加每条消息的 usage，按官方定价算人民币）──
    token_info = {"total": 0, "input": 0, "output": 0, "cache_write": 0, "cache_read": 0}
    model = None
    total_input = 0
    total_output = 0
    total_cache_read = 0

    for m in messages:
        u = m.get("usage")
        if isinstance(u, dict):
            inp = u.get("input", 0) or u.get("promptTokens", 0) or u.get("inputTokens", 0) or 0
            out = u.get("output", 0) or u.get("completionTokens", 0) or u.get("outputTokens", 0) or 0
            cr = u.get("cacheRead", 0) or u.get("cacheReadTokens", 0) or 0
            cw = u.get("cacheWrite", 0) or u.get("cacheWriteTokens", 0) or 0
            tt = u.get("totalTokens", 0) or 0

            token_info["input"] += inp
            token_info["output"] += out
            token_info["cache_read"] += cr
            token_info["cache_write"] += cw
            token_info["total"] += tt

            total_input += inp
            total_output += out
            total_cache_read += cr

        # 提取模型名
        if model is None and m.get("role") == "assistant" and m.get("model"):
            model = m["model"]

    # 按官方定价计算人民币成本（不使用不可靠的 usage.cost 字段）
    cost_cny = compute_cost_cny(total_input, total_output, total_cache_read, model)

    return {
        "model": model,
        "duration": duration_info,
        "messages": {
            "total": total,
            "user": user_count,
            "assistant": assistant_count,
            "tool_result": tool_count,
        },
        "tool_calls": {
            "total": total_tool_calls,
            "distinct_tools": distinct_tools,
            "distribution": dict(sorted(tool_dist.items(), key=lambda x: -x[1])),
            "errors": tool_errors,
        },
        "tokens": token_info,
        "cost_cny": cost_cny,
    }


async def fetch_session_stats(
    session_key: str,
    gateway_url: str = "ws://127.0.0.1:18789",
    token: str | None = None,
    password: str | None = None,
) -> dict:
    """连接 Gateway WS，调用 chat.history，返回统计信息"""
    async with websockets.connect(gateway_url, max_size=50 * 1024 * 1024) as ws:
        # 1. 等待 connect.challenge
        challenge_msg = await asyncio.wait_for(ws.recv(), timeout=10)
        challenge = json.loads(challenge_msg)
        assert challenge.get("event") == "connect.challenge", f"期望 challenge，收到: {challenge.get('event')}"

        # 2. 发送 connect 请求
        auth_params = {}
        if token:
            auth_params["token"] = token
        if password:
            auth_params["password"] = password

        connect_req = {
            "type": "req",
            "id": "1",
            "method": "connect",
            "params": {
                "minProtocol": 3,
                "maxProtocol": 3,
                "client": {
                    "id": "gateway-client",
                    "version": "1.0.0",
                    "platform": "linux",
                    "mode": "backend",
                },
                "role": "operator",
                "scopes": ["operator.read"],
                "caps": [],
                "commands": [],
                "permissions": {},
                "auth": auth_params,
                "locale": "zh-CN",
                "userAgent": "session-stats/1.0",
            },
        }
        await ws.send(json.dumps(connect_req))

        # 3. 等待 hello-ok
        hello_resp = await asyncio.wait_for(ws.recv(), timeout=10)
        hello = json.loads(hello_resp)
        if not hello.get("ok"):
            error_detail = hello.get("error", hello)
            raise RuntimeError(
                f"连接失败: {error_detail.get('message', 'unknown')} "
                f"(code: {error_detail.get('code', 'N/A')})"
            )
        assert hello["payload"]["type"] == "hello-ok"

        # 4. 发送 chat.history RPC 请求
        history_req = {
            "type": "req",
            "id": "2",
            "method": "chat.history",
            "params": {"sessionKey": session_key, "limit": 1000},
        }
        await ws.send(json.dumps(history_req))

        # 5. 接收响应
        history_resp = None
        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=120)
            msg = json.loads(raw)
            if msg.get("type") == "res" and msg.get("id") == "2":
                history_resp = msg
                break

        if not history_resp.get("ok"):
            error_detail = history_resp.get("error", history_resp)
            raise RuntimeError(
                f"chat.history 调用失败: {error_detail.get('message', 'unknown')} "
                f"(code: {error_detail.get('code', 'N/A')})"
            )

        payload = history_resp["payload"]
        messages = payload.get("messages") or payload.get("entries") or []
        return compute_stats(messages)


def parse_args():
    parser = argparse.ArgumentParser(description="提取 OpenClaw 会话统计信息")
    parser.add_argument("--token", required=True, help="Gateway 认证 token")
    parser.add_argument("--password", help="Gateway 认证密码")
    parser.add_argument("--gateway", default="ws://127.0.0.1:18789", help="Gateway WebSocket 地址")
    return parser.parse_args()


def main():
    args = parse_args()

    token = args.token or os.environ.get("OPENCLAW_GATEWAY_TOKEN")
    password = args.password or os.environ.get("OPENCLAW_GATEWAY_PASSWORD")

    if not SESSION_KEYS:
        print(json.dumps({"error": "SESSION_KEYS 为空，请先在脚本中添加会话 key"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    all_results = []

    for session_key in SESSION_KEYS:
        print(f"正在处理: {session_key}")
        try:
            stats = asyncio.run(fetch_session_stats(
                session_key=session_key,
                gateway_url=args.gateway,
                token=token,
                password=password,
            ))
        except Exception as e:
            print(json.dumps({"error": str(e), "traceback": traceback.format_exc()}, ensure_ascii=False, indent=2), file=sys.stderr)
            continue

        short_id = session_key.split(":")[-1] if ":" in session_key else session_key
        output_path = os.path.join(OUTPUT_DIR, f"{short_id}.json")

        result = {
            "session_id": session_key,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "statistics": stats,
        }

        output = json.dumps(result, ensure_ascii=False, indent=2)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output)
            f.write("\n")
        print(f"  ✓ 已写入: {output_path}")
        all_results.append(result)

    # 写入总结文件（一行）
    if all_results:
        merged = {
            "total_sessions": len(all_results),
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "sessions": [r["statistics"] for r in all_results],
            "summary": {
                "total_messages": sum(r["statistics"]["messages"]["total"] for r in all_results),
                "total_tool_calls": sum(r["statistics"]["tool_calls"]["total"] for r in all_results),
                "total_tokens": sum(r["statistics"]["tokens"]["total"] for r in all_results),
                "total_cost_cny": round(sum(r["statistics"]["cost_cny"] for r in all_results), 4),
            },
        }
        summary_path = os.path.join(OUTPUT_DIR, "summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(merged, ensure_ascii=False, separators=(",", ":")))
            f.write("\n")
        print(f"📊 总结已写入: {summary_path}")


if __name__ == "__main__":
    main()
