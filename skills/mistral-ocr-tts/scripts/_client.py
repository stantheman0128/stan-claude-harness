"""讀取 MISTRAL_API_KEY 環境變數並建立 Mistral client。

兩支腳本（ocr.py / tts.py）共用，所以 key 的讀取與錯誤訊息只有一處。
"""
import os
import sys

try:
    from mistralai import Mistral          # mistralai v1.x
except ImportError:
    from mistralai.client import Mistral   # mistralai v2.x：client 搬到 mistralai.client


def get_client():
    key = os.environ.get("MISTRAL_API_KEY")
    if not key:
        sys.exit(
            "找不到 MISTRAL_API_KEY 環境變數。\n"
            "設定方式（PowerShell，設一次即可）：\n"
            '    setx MISTRAL_API_KEY "你的key"\n'
            "設定後要重開終端機 / 重啟 Claude Code 才會生效。"
        )
    # strip() 防止從檔案複製貼上時夾帶換行或空白
    return Mistral(api_key=key.strip())
