#!/usr/bin/env python3
"""
交互式调用示例：分析图片
通过命令行交互输入 API Key

使用方式:
    python call_interactive.py
"""

import base64
import json
import requests
import sys
import getpass

# 图片路径
IMAGE_PATH = "/data_sdb/openclaw/02_llv_generated/06_article_notes/123.jpg"


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
    print("=" * 50)
    print("🔍 MiniMax Vision 图片理解工具")
    print("=" * 50)
    
    # 交互式输入 API Key
    print("\n📌 请输入你的 MiniMax API Key:")
    print("   (获取地址: https://platform.minimaxi.com/user-center/basic-information/interface-key)")
    api_key = getpass.getpass("> ")
    
    if not api_key.strip():
        print("❌ API Key 不能为空")
        sys.exit(1)
    
    # 交互式输入图片路径
    print(f"\n📷 图片路径 (默认: {IMAGE_PATH}):")
    image_path = input("> ").strip() or IMAGE_PATH
    
    # 检查图片是否存在
    try:
        with open(image_path, "rb") as f:
            pass
    except FileNotFoundError:
        print(f"❌ 图片文件不存在: {image_path}")
        sys.exit(1)
    
    # 交互式输入问题
    print("\n❓ 请输入要问图片的问题 (例如: 这张图片显示了什么？)")
    prompt = input("> ").strip()
    
    if not prompt:
        prompt = "请描述这张图片的内容"
        print(f"   使用默认问题: {prompt}")
    
    print(f"\n📷 读取图片: {image_path}")
    image_data = image_to_base64(image_path)
    print(f"✅ 图片已转为 base64 (长度: {len(image_data)} 字符)")
    
    print("🔄 正在调用 MiniMax Vision API...")
    
    try:
        result = call_minimax_vision(api_key, image_data, prompt)
        print("\n" + "=" * 50)
        print("📝 分析结果:")
        print("=" * 50)
        print(result)
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ API 调用失败: {e}")
        try:
            error_data = e.response.json()
            print(f"   错误信息: {error_data}")
        except:
            print(f"   {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 调用失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
