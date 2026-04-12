#!/usr/bin/env python3
"""
解析测试脚本 - Step 0
先于主项目运行，解析 JSONL 前 N 条记录并打印输出
供用户确认格式理解是否正确
"""
import json
import sys
from pathlib import Path

SAMPLE_FILE = "/data_sdb/openclaw/KnowledgeWorkspace/03_workspace/03_drafts/0d23113d-9faa-48b8-b61d-cd3e546189f4.jsonl.reset.2026-04-03T12-04-56.005Z"
LIMIT = 30  # 解析前多少行


def extract_text_content(content_list):
    """从 message.content 数组中提取人类可读文本"""
    if not content_list:
        return ""
    texts = []
    for item in content_list:
        t = item.get("type", "")
        if t == "text":
            texts.append(item.get("text", ""))
        elif t == "toolCall":
            args = item.get("arguments", {})
            # 工具名 + 简要参数
            args_str = json.dumps(args, ensure_ascii=False)
            if len(args_str) > 200:
                args_str = args_str[:200] + "..."
            texts.append(f"[工具调用: {item.get('name')}，参数: {args_str}]")
        elif t == "toolResult":
            result = item.get("content", "")
            if isinstance(result, list):
                # 工具返回可能也是数组，找 text
                for r in result:
                    if isinstance(r, dict) and r.get("type") == "text":
                        result = r.get("text", "")
                        break
            texts.append(f"[工具返回: {str(result)[:200]}]")
        # 跳过 thinking（太冗长）
    return "\n".join(texts).strip()


def main():
    print(f"📄 解析样本文件: {SAMPLE_FILE}\n")

    path = Path(SAMPLE_FILE)
    if not path.exists():
        print(f"❌ 文件不存在: {SAMPLE_FILE}")
        sys.exit(1)

    count = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                print(f"⚠️  JSON 解析失败: {line[:80]}...")
                continue

            event_type = event.get("type", "?")
            ts = event.get("timestamp", "")
            event_id = event.get("id", "")[:12] if event.get("id") else "?"
            parent_id = str(event.get("parentId", ""))[:12] if event.get("parentId") else "-"

            print(f"\n{'='*60}")
            print(f"type: {event_type}  |  id: {event_id}  |  parent: {parent_id}  |  ts: {ts}")

            if event_type == "session":
                print(f"  → 新会话开始 (cwd={event.get('cwd')})")

            elif event_type == "model_change":
                print(f"  → 模型切换: {event.get('modelId')} ({event.get('provider')})")

            elif event_type == "thinking_level_change":
                print(f"  → 思考级别变更: {event.get('thinkingLevel')}")

            elif event_type == "custom":
                custom_t = event.get("customType", "?")
                data = event.get("data", {})
                print(f"  → custom type: {custom_t}, model: {data.get('modelId')} ({data.get('provider')})")

            elif event_type == "message":
                msg = event.get("message", {})
                role = msg.get("role", "?")
                model = msg.get("model", "-")
                provider = msg.get("provider", "-")
                usage = msg.get("usage", {})
                stop_reason = msg.get("stopReason", "-")
                content = msg.get("content", [])
                text_preview = extract_text_content(content)

                print(f"  → 角色: {role}")
                print(f"  → 模型: {model} ({provider})")
                print(f"  → Token: input={usage.get('input',0)}, output={usage.get('output',0)}, total={usage.get('totalTokens',0)}")
                print(f"  → 停止原因: {stop_reason}")
                print(f"  → 内容预览:\n{text_preview[:300]}{'...' if len(text_preview) > 300 else ''}")

            else:
                print(f"  → [未知类型，跳过]")

            count += 1
            if count >= LIMIT:
                print(f"\n\n✅ 已解析 {count} 条记录，停止（测试模式）")
                break

    print(f"\n\n共解析 {count} 条事件记录")


if __name__ == "__main__":
    main()
