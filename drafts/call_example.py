#!/usr/bin/env python3
"""
调用示例：分析图片 /data_sdb/openclaw/02_llv_generated/06_article_notes/123.jpg

使用方式:
    python call_example.py
"""

import base64
import json
import requests
import sys

# 图片路径
IMAGE_PATH = "/data_sdb/openclaw/02_llv_generated/06_article_notes/123.jpg"

# TODO: 替换为你的 API Key
API_KEY = "YOUR_API_KEY_HERE"


def image_to_base64(image_path: str) -> str:
    """读取本地图片并转为 base64"""
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


def call_minimax_vision(api_key: str, base64_image: str, prompt: str) -> str:
    """调用 MiniMax Vision API"""
    url = "https://api.minimaxi.com/v1/text/chatcompletion_v2"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "MiniMax-M2.5",
        "max_tokens": 4096,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "data": base64_image
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    
    data = response.json()
    
    if data.get("choices") and len(data["choices"]) > 0:
        return data["choices"][0]["message"]["content"]
    
    raise Exception(f"Invalid response: {json.dumps(data, ensure_ascii=False)}")


def main():
    # 检查 API Key
    if API_KEY == "YOUR_API_KEY_HERE":
        print("❌ 请先替换脚本中的 API_KEY 为你的 MiniMax API Key")
        print("获取 API Key: https://platform.minimaxi.com/user-center/basic-information/interface-key")
        sys.exit(1)
    
    print(f"📷 读取图片: {IMAGE_PATH}")
    image_data = image_to_base64(IMAGE_PATH)
    print(f"✅ 图片已转为 base64 (长度: {len(image_data)} 字符)")
    
    prompt = "请描述这张图片的内容"
    print(f"❓ 问题: {prompt}")
    print("🔄 正在调用 MiniMax Vision API...")
    
    try:
        result = call_minimax_vision(API_KEY, image_data, prompt)
        print("\n" + "=" * 50)
        print("📝 分析结果:")
        print("=" * 50)
        print(result)
    except Exception as e:
        print(f"❌ 调用失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
