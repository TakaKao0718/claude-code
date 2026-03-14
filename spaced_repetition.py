#!/usr/bin/env python3
"""
スペースド・レペティション学習アプリ with アクティブリコール
SM-2アルゴリズムとClaude APIを使って、Obsidianノートから学習カードを生成・管理する。
"""

import os
import re
import sys
import json
import argparse
import datetime
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("Please install anthropic: pip install anthropic")
    sys.exit(1)

try:
    from obsidian_reader import read_vault, search_notes
    OBSIDIAN_AVAILABLE = True
except ImportError:
    OBSIDIAN_AVAILABLE = False

DATA_FILE = Path.home() / ".spaced_repetition_data.json"


# ---------------------------------------------------------------------------
# SM-2 アルゴリズム
# ---------------------------------------------------------------------------

def sm2_update(card: dict, quality: int) -> dict:
    """
    SM-2アルゴリズムでカードのスケジュールを更新する。

    quality 0-5:
      0 = 全く思い出せなかった
      1 = 思い出せなかった（答えを見てやっと分かった）
      2 = 正解を見て思い出せた
      3 = かなり難しかったが思い出せた
      4 = 少し迷ったが思い出せた
      5 = 完璧に思い出せた
    """
    ef = card.get("easiness_factor", 2.5)
    reps = card.get("repetitions", 0)
    interval = card.get("interval", 1)

    if quality >= 3:
        # 正解 → インターバルを伸ばす
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = 6
        else:
            interval = round(interval * ef)
        reps += 1
    else:
        # 不正解 → リセット
        reps = 0
        interval = 1

    # Easiness Factor を更新（最小値 1.3）
    ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    ef = max(1.3, ef)

    card["easiness_factor"] = round(ef, 3)
    card["repetitions"] = reps
    card["interval"] = interval
    card["next_review"] = (
        datetime.date.today() + datetime.timedelta(days=interval)
    ).isoformat()
    card["last_review"] = datetime.date.today().isoformat()
    return card


# ---------------------------------------------------------------------------
# データ管理
# ---------------------------------------------------------------------------

def load_data() -> dict:
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"cards": [], "next_id": 1}


def save_data(data: dict) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_due_cards(data: dict) -> list[dict]:
    today = datetime.date.today().isoformat()
    return [c for c in data["cards"] if c.get("next_review", today) <= today]


# ---------------------------------------------------------------------------
# カード作成
# ---------------------------------------------------------------------------

def make_card(data: dict, question: str, answer: str,
              hint: str = "", source: str = "") -> dict:
    today = datetime.date.today().isoformat()
    card = {
        "id": data["next_id"],
        "question": question,
        "answer": answer,
        "hint": hint,
        "source": source,
        "created": today,
        "next_review": today,
        "last_review": None,
        "repetitions": 0,
        "interval": 1,
        "easiness_factor": 2.5,
    }
    data["cards"].append(card)
    data["next_id"] += 1
    return card


def generate_cards_from_note(note: dict, num_cards: int = 3) -> list[dict]:
    """Claude APIでノートからフラッシュカードを自動生成する。"""
    client = anthropic.Anthropic()

    prompt = f"""以下のノートから、アクティブリコール（積極的想起）の練習に最適な
フラッシュカードを{num_cards}枚作成してください。

ノートタイトル: {note['title']}
内容:
{note['body'][:3000]}

以下のJSON形式だけで回答してください（説明文は不要）:
[
  {{
    "question": "質問文",
    "answer": "答え",
    "hint": "ヒント（難しい場合の手がかり）"
  }}
]

重要なポイントを問う質問を作り、記憶定着に役立つカードを作成してください。"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()
    json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
    if not json_match:
        return []

    cards_data = json.loads(json_match.group())
    return [
        {
            "question": d.get("question", ""),
            "answer": d.get("answer", ""),
            "hint": d.get("hint", ""),
            "source": note["title"],
        }
        for d in cards_data
        if d.get("question") and d.get("answer")
    ]


def add_cards_from_note(data: dict, note: dict, num_cards: int = 3) -> list[dict]:
    print(f"  Claude が '{note['title']}' からカードを生成中...")
    try:
        cards_data = generate_cards_from_note(note, num_cards)
        added = []
        for cd in cards_data:
            card = make_card(data, cd["question"], cd["answer"],
                             cd.get("hint", ""), cd.get("source", note["title"]))
            added.append(card)
        return added
    except Exception as e:
        print(f"  エラー: {e}")
        return []


# ---------------------------------------------------------------------------
# レビューセッション
# ---------------------------------------------------------------------------

def run_review_session(data: dict) -> None:
    due = get_due_cards(data)

    if not due:
        print("\n今日のレビューはありません！よく頑張りました！")
        print(f"総カード数: {len(data['cards'])}")
        upcoming = sorted(
            [c for c in data["cards"] if c.get("next_review")],
            key=lambda c: c["next_review"],
        )
        if upcoming:
            print(f"次のレビュー予定: {upcoming[0]['next_review']}")
        return

    print(f"\n今日のレビュー: {len(due)} 枚")
    print("=" * 52)

    correct = 0
    for i, card in enumerate(due, 1):
        source_label = f" (出典: {card['source']})" if card.get("source") else ""
        print(f"\n[{i}/{len(due)}]{source_label}")
        print(f"\n質問: {card['question']}")

        if card.get("hint"):
            show_hint = input("\nヒントを見る？ (y/n, Enterで答えへ): ").strip().lower()
            if show_hint == "y":
                print(f"ヒント: {card['hint']}")

        input("\n[Enterを押して答えを確認] ")
        print(f"\n答え: {card['answer']}")

        print("\nどれくらい思い出せましたか？")
        print("  0 全く思い出せなかった")
        print("  1 思い出せなかった（答えを見てやっと理解）")
        print("  2 答えを見て思い出せた")
        print("  3 かなり難しかったが思い出せた")
        print("  4 少し迷ったが思い出せた")
        print("  5 完璧に思い出せた")

        while True:
            try:
                quality = int(input("評価 (0-5): "))
                if 0 <= quality <= 5:
                    break
                print("0から5の数字を入力してください。")
            except ValueError:
                print("数字を入力してください。")

        if quality >= 3:
            correct += 1

        for j, c in enumerate(data["cards"]):
            if c["id"] == card["id"]:
                data["cards"][j] = sm2_update(c, quality)
                nxt = data["cards"][j]["next_review"]
                ivl = data["cards"][j]["interval"]
                print(f"次のレビュー: {nxt} ({ivl}日後)")
                break

    save_data(data)
    pct = correct * 100 // len(due) if due else 0
    print(f"\n{'='*52}")
    print(f"セッション完了！  正答率: {correct}/{len(due)} ({pct}%)")


# ---------------------------------------------------------------------------
# 統計
# ---------------------------------------------------------------------------

def show_stats(data: dict) -> None:
    cards = data["cards"]
    if not cards:
        print("カードがまだありません。")
        return

    today = datetime.date.today().isoformat()
    due      = [c for c in cards if c.get("next_review", today) <= today]
    mastered = [c for c in cards if c.get("repetitions", 0) >= 5]
    learning = [c for c in cards if 0 < c.get("repetitions", 0) < 5]
    new_cards = [c for c in cards if c.get("repetitions", 0) == 0]

    sources: dict[str, int] = {}
    for card in cards:
        src = card.get("source") or "手動追加"
        sources[src] = sources.get(src, 0) + 1

    print(f"\n{'='*40}")
    print("学習統計")
    print(f"{'='*40}")
    print(f"総カード数      : {len(cards)}")
    print(f"今日のレビュー  : {len(due)}")
    print(f"新規             : {len(new_cards)}")
    print(f"学習中           : {len(learning)}")
    print(f"習得済み (5回+) : {len(mastered)}")

    if sources:
        print("\n出典別カード数:")
        for src, count in sorted(sources.items(), key=lambda x: -x[1]):
            print(f"  {src}: {count}枚")

    upcoming = sorted(
        [c for c in cards if c.get("next_review") and c["next_review"] > today],
        key=lambda c: c["next_review"],
    )[:5]
    if upcoming:
        print("\n次回のレビュー予定 (直近5件):")
        for c in upcoming:
            print(f"  {c['next_review']} : {c['question'][:45]}...")


# ---------------------------------------------------------------------------
# メインCLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="スペースド・レペティション学習アプリ (SM-2 + アクティブリコール)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
コマンド例:
  python spaced_repetition.py review                        # 今日のレビュー
  python spaced_repetition.py add -q "質問" -a "答え"       # カードを手動追加
  python spaced_repetition.py generate /path/to/vault       # Obsidianから自動生成
  python spaced_repetition.py generate /path/to/vault -s "歴史" -c 5
  python spaced_repetition.py stats                         # 学習統計を表示
  python spaced_repetition.py list                          # 全カードを一覧表示
""",
    )
    sub = parser.add_subparsers(dest="command")

    # review
    sub.add_parser("review", help="今日のレビューセッションを開始")

    # add
    ap = sub.add_parser("add", help="カードを手動で追加")
    ap.add_argument("--question", "-q", required=True, help="質問文")
    ap.add_argument("--answer",   "-a", required=True, help="答え")
    ap.add_argument("--hint",     "-H", default="",   help="ヒント（省略可）")
    ap.add_argument("--source",   "-s", default="",   help="出典メモ（省略可）")

    # generate
    gp = sub.add_parser("generate", help="ObsidianノートからAIでカードを生成")
    gp.add_argument("vault", help="Obsidianボルトのパス")
    gp.add_argument("--search", "-s", help="絞り込むキーワード")
    gp.add_argument("--cards",  "-c", type=int, default=3,
                    help="ノートあたりのカード数 (デフォルト: 3)")
    gp.add_argument("--limit",  "-l", type=int, default=5,
                    help="処理するノートの最大数 (デフォルト: 5)")

    # stats
    sub.add_parser("stats", help="学習統計を表示")

    # list
    sub.add_parser("list", help="全カードを一覧表示")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    data = load_data()

    if args.command == "review":
        run_review_session(data)

    elif args.command == "add":
        card = make_card(data, args.question, args.answer, args.hint, args.source)
        save_data(data)
        print(f"カードを追加しました (ID: {card['id']})")
        print(f"質問: {card['question']}")
        print(f"答え: {card['answer']}")

    elif args.command == "generate":
        if not OBSIDIAN_AVAILABLE:
            print("Error: obsidian_reader.py が見つかりません。同じディレクトリに配置してください。")
            sys.exit(1)

        print(f"ボルトを読み込み中: {args.vault}")
        notes = read_vault(args.vault)
        print(f"{len(notes)} 件のノートを読み込みました。")

        if args.search:
            notes = search_notes(notes, args.search)
            print(f"'{args.search}' で絞り込み: {len(notes)} 件")

        notes = notes[: args.limit]
        print(f"{len(notes)} 件のノートからカードを生成します...\n")

        total = 0
        for note in notes:
            added = add_cards_from_note(data, note, args.cards)
            total += len(added)
            for card in added:
                print(f"  + Q: {card['question'][:55]}...")
            save_data(data)

        print(f"\n{total} 枚のカードを追加しました！")
        print("'python spaced_repetition.py review' でレビューを開始できます。")

    elif args.command == "stats":
        show_stats(data)

    elif args.command == "list":
        cards = data["cards"]
        if not cards:
            print("カードがまだありません。")
            return
        today = datetime.date.today().isoformat()
        print(f"\n全カード ({len(cards)} 枚):")
        print("=" * 60)
        for card in cards:
            due_marker = " [TODAY]" if card.get("next_review", today) <= today else ""
            print(f"[{card['id']}]{due_marker}  {card['question'][:55]}")
            print(f"      -> {card['answer'][:55]}")
            print(
                f"      次回: {card.get('next_review', '未設定')}  "
                f"繰り返し: {card.get('repetitions', 0)}回  "
                f"EF: {card.get('easiness_factor', 2.5):.2f}"
            )


if __name__ == "__main__":
    main()
