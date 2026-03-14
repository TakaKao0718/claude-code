# Obsidian 学習ツール集

ObsidianのボルトにあるMarkdownファイルをClaude APIで活用する2つのツールです。

## セットアップ

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-api-key"
```

---

## 1. スペースド・レペティション学習アプリ (`spaced_repetition.py`)

**アクティブリコール**（積極的想起）と **SM-2アルゴリズム**（分散学習）を組み合わせた学習アプリです。
Obsidianのノートから Claude API が自動でフラッシュカードを生成し、最適なタイミングでレビューを促します。

### 仕組み

| 機能 | 説明 |
|------|------|
| アクティブリコール | 答えを見る前に思い出す練習をする |
| SM-2アルゴリズム | 正解率に応じてレビュー間隔を自動調整（1日→6日→数週間…） |
| AI カード生成 | Claude が Obsidian ノートから重要な問いを自動作成 |

### 使い方

```bash
# Obsidianノートから自動でカード生成（最大5件のノートから）
python spaced_repetition.py generate /path/to/your/vault

# キーワードで絞り込んで生成（歴史ノートから5枚ずつ、最大10件）
python spaced_repetition.py generate /path/to/your/vault --search "歴史" --cards 5 --limit 10

# カードを手動で追加
python spaced_repetition.py add -q "光合成とは？" -a "植物が光エネルギーを使ってCO2と水から糖を作る反応" -H "葉緑体"

# 今日のレビューセッションを開始
python spaced_repetition.py review

# 学習統計を確認
python spaced_repetition.py stats

# 全カードを一覧表示
python spaced_repetition.py list
```

### レビューの評価基準 (0–5)

| スコア | 意味 | 結果 |
|--------|------|------|
| 0 | 全く思い出せなかった | リセット（翌日再出題） |
| 1 | 思い出せなかった（答えを見てやっと理解） | リセット |
| 2 | 答えを見て思い出せた | リセット |
| 3 | かなり難しかったが思い出せた | インターバル延長 |
| 4 | 少し迷ったが思い出せた | インターバル延長 |
| 5 | 完璧に思い出せた | インターバル延長 |

3以上で「正解」とみなし、インターバルが伸びます（例: 1日→6日→数週間）。

### データ保存先

`~/.spaced_repetition_data.json` に自動保存されます。

---

## 2. Obsidian Vault Reader (`obsidian_reader.py`)

ObsidianのボルトにあるMarkdownファイルをClaude APIを使って読み取り、質問できるツールです。

### 使い方

```bash
# ノートの一覧表示
python obsidian_reader.py /path/to/your/vault --list

# キーワード検索
python obsidian_reader.py /path/to/your/vault --search "プロジェクト"

# Claudeに質問する（全ノートを使用）
python obsidian_reader.py /path/to/your/vault --ask "先月のミーティングのまとめは？"

# 特定のノートに絞ってClaudeに質問する
python obsidian_reader.py /path/to/your/vault --ask "このプロジェクトの課題は？" --ask-about "プロジェクトA"
```

### 対応している機能

- `.md` ファイルの再帰的な読み取り
- YAMLフロントマターのパース（タグ、日付など）
- `[[wikilinks]]` の抽出
- キーワード検索
- Claude APIを使った自然言語での質問応答（日本語対応）
