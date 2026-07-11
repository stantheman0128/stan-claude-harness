"""Mistral OCR：把 PDF / 影像（本機路徑或 URL）轉成 Markdown。

用法：
    python ocr.py <檔案或URL>                 # 印到畫面
    python ocr.py <檔案或URL> -o out.md       # 寫成檔案
    python ocr.py scan.pdf --model mistral-ocr-latest

OCR 是多語的，中文沒問題（但官方不分繁簡）。
"""
import argparse
import base64
import os
import sys

from _client import get_client

IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff"}


def build_document(src):
    """依來源是 URL 或本機檔、是 PDF 或影像，組出 OCR API 要的 document 參數。"""
    is_url = src.startswith("http://") or src.startswith("https://")
    ext = os.path.splitext(src.split("?")[0])[1].lower()

    if is_url:
        if ext in IMG_EXT:
            return {"type": "image_url", "image_url": src}
        return {"type": "document_url", "document_url": src}

    if not os.path.exists(src):
        sys.exit(f"找不到檔案：{src}")
    b64 = base64.b64encode(open(src, "rb").read()).decode()
    if ext in IMG_EXT:
        mime = "image/jpeg" if ext in {".jpg", ".jpeg"} else "image/" + ext.lstrip(".")
        return {"type": "image_url", "image_url": f"data:{mime};base64,{b64}"}
    return {"type": "document_url", "document_url": f"data:application/pdf;base64,{b64}"}


def main():
    ap = argparse.ArgumentParser(description="Mistral OCR -> Markdown")
    ap.add_argument("source", help="PDF/影像 的本機路徑或 URL")
    ap.add_argument("-o", "--output", help="輸出 .md 路徑；省略則印到畫面")
    ap.add_argument("--model", default="mistral-ocr-latest")
    args = ap.parse_args()

    client = get_client()
    resp = client.ocr.process(model=args.model, document=build_document(args.source))
    md = "\n\n---\n\n".join(p.markdown for p in resp.pages)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"OCR 完成：{len(resp.pages)} 頁 -> {args.output}")
    else:
        print(md)


if __name__ == "__main__":
    main()
