#!/usr/bin/env python3
"""
MiniMax Vision 图片理解工具
调用 MiniMax API 分析图片内容

使用方式:
    python minimax_vision.py --api-key YOUR_API_KEY --url IMAGE_URL --prompt "图片显示了什么？"
    python minimax_vision.py --api-key YOUR_API_KEY --base64 BASE64_DATA --prompt "描述这张图片"
"""

import argparse
import base64
import json
import requests
import sys


def image_url_to_base64(url: str) -> str:
    """从 URL 获取图片并转为 base64"""
    response = requests.get(url)
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "image/jpeg")
    b64 = base64.b64encode(response.content).decode("utf-8")
    return f"data:{content_type};base64,{b64}"


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
    parser = argparse.ArgumentParser(description="MiniMax Vision 图片理解工具")
    parser.add_argument("--api-key", required=True, help="MiniMax API Key")
    parser.add_argument("--url", help="图片 URL")
    parser.add_argument("--base64", help="图片 base64 数据")
    parser.add_argument("--prompt", required=True, help="要问图片的问题")
    
    args = parser.parse_args()
    
    # 获取图片数据
    if args.url:
        image_data = image_url_to_base64(args.url)
    elif args.base64:
        image_data = args.base64
    else:
        print(json.dumps({"error": "请提供 --url 或 --base64 参数"}))
        sys.exit(1)
    
    try:
        result = call_minimax_vision(args.api_key, image_data, args.prompt)
        print(json.dumps({"result": result}, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
