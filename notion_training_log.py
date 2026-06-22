#!/usr/bin/env python3
"""
答弁訓練ログ Notion 登録ツール（シンプル版）

議会・委員会答弁訓練の記録を、Notion データベース「答弁訓練ログ」に1ページとして
追加するスクリプトです。入力は JSON ファイルで差し替えられます。

設計方針（続けやすさ優先）:
- プロパティは最小限（タイトル / 日付 / 分野 / 次回使う型）。振り分けの手間を減らす。
- 本文は決まった見出しを強制しない。JSON の "sections" に書いた見出しが、
  書いた順番でそのまま出力される「汎用フォーマット」。最小は3見出しでOK。
- AI の助言全文や模範答弁全文はそのまま保存しない。自分の答弁・要約・次回使う型が中心。

セットアップ:
    pip install -r requirements.txt
    export NOTION_API_KEY="secret_xxx"           # Notion インテグレーションのシークレット
    export NOTION_TRAINING_LOG_DB_ID="xxxxxxxx"  # 「答弁訓練ログ」DB（データソース）のID

使い方:
    python notion_training_log.py training_logs/2026-06-22_kokuho.json
    python notion_training_log.py training_logs/2026-06-22_kokuho.json --dry-run

入力 JSON の最小例は training_logs/_template.json を参照してください。
"""

import os
import sys
import json
import argparse
from pathlib import Path

try:
    import requests
except ImportError:
    print("Please install requests: pip install -r requirements.txt")
    sys.exit(1)

NOTION_API = "https://api.notion.com/v1/pages"
NOTION_VERSION = "2022-06-28"


def _rich_text(content: str) -> list[dict]:
    """Notion の rich_text 配列を作る（2000文字制限に配慮して分割）。"""
    chunks = [content[i:i + 2000] for i in range(0, len(content), 2000)] or [""]
    return [{"type": "text", "text": {"content": c}} for c in chunks]


def build_properties(data: dict) -> dict:
    """JSON から最小限のプロパティ payload を作る。"""
    props: dict = {
        "タイトル": {"title": _rich_text(data["title"])},
    }
    if data.get("date"):
        props["日付"] = {"date": {"start": data["date"]}}
    if data.get("field"):
        props["分野"] = {"select": {"name": data["field"]}}
    if data.get("next_pattern"):
        props["次回使う型"] = {"rich_text": _rich_text(data["next_pattern"])}
    return props


def build_children(sections: dict) -> list[dict]:
    """本文ブロックを作る。JSON に書いた見出しを書いた順番でそのまま出力する。"""
    children: list[dict] = []
    for heading, text in sections.items():
        text = (text or "").strip()
        if not text:
            continue
        children.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": _rich_text(heading)},
        })
        # 空行で段落を分割する
        for para in [p.strip() for p in text.split("\n\n") if p.strip()]:
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": _rich_text(para)},
            })
    return children


def build_payload(data: dict, database_id: str) -> dict:
    return {
        "parent": {"database_id": database_id},
        "properties": build_properties(data),
        "children": build_children(data.get("sections", {})),
    }


def create_page(payload: dict, api_key: str) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    resp = requests.post(NOTION_API, headers=headers, json=payload, timeout=30)
    if resp.status_code >= 400:
        raise SystemExit(f"Notion API error {resp.status_code}: {resp.text}")
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="答弁訓練ログを Notion に登録する")
    parser.add_argument("input", help="登録する訓練ログの JSON ファイル")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="API を呼ばず、送信予定の payload を表示するだけ",
    )
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if not data.get("title"):
        raise SystemExit("入力 JSON に 'title' がありません。")

    database_id = os.environ.get("NOTION_TRAINING_LOG_DB_ID", "")

    if args.dry_run:
        payload = build_payload(data, database_id or "<NOTION_TRAINING_LOG_DB_ID>")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    api_key = os.environ.get("NOTION_API_KEY")
    if not api_key:
        raise SystemExit("環境変数 NOTION_API_KEY が設定されていません。")
    if not database_id:
        raise SystemExit("環境変数 NOTION_TRAINING_LOG_DB_ID が設定されていません。")

    payload = build_payload(data, database_id)
    result = create_page(payload, api_key)
    print(f"登録しました: {result.get('url')}")


if __name__ == "__main__":
    main()
