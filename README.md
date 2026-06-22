# Obsidian Vault Reader

ObsidianのボルトにあるMarkdownファイルをClaude APIを使って読み取り、質問できるツールです。

## セットアップ

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-api-key"
```

## 使い方

### ノートの一覧表示
```bash
python obsidian_reader.py /path/to/your/vault --list
```

### キーワード検索
```bash
python obsidian_reader.py /path/to/your/vault --search "プロジェクト"
```

### Claudeに質問する（全ノートを使用）
```bash
python obsidian_reader.py /path/to/your/vault --ask "先月のミーティングのまとめは？"
```

### 特定のノートに絞ってClaudeに質問する
```bash
python obsidian_reader.py /path/to/your/vault --ask "このプロジェクトの課題は？" --ask-about "プロジェクトA"
```

## 対応している機能

- `.md` ファイルの再帰的な読み取り
- YAMLフロントマターのパース（タグ、日付など）
- `[[wikilinks]]` の抽出
- キーワード検索
- Claude APIを使った自然言語での質問応答（日本語対応）

---

# 答弁訓練ログ → Notion 登録ツール (`notion_training_log.py`)

議会・委員会答弁訓練の記録を、Notion データベース **「答弁訓練ログ」** に1ページとして
追加するツールです。次回の訓練で再利用できる「型」として蓄積していきます。

## 保存方針

- AIの助言全文や模範答弁全文は**そのまま保存しません**。
- 保存するのは、**自分の答弁・質問の要約・弱点・次回使う型・改善ポイント**です。
- 長文7項目はページ**本文の見出し**に、検索用メタ情報はデータベースの**プロパティ**に入れます。

## Notion 側の構成

| データベース | 役割 |
| --- | --- |
| **答弁の型**（既存） | 再利用する答弁テンプレート集（型カタログ）。変更していません。 |
| **答弁訓練ログ**（新規作成） | 毎回の訓練記録。良かった型は「答弁の型」へ昇格させる運用。 |

「答弁訓練ログ」のプロパティ：タイトル / 日付 / 分野 / 質問区分 / 質問テーマ /
弱点 / 次回使う型 / タグ / ステータス（下書き・復習中・型化済み）。

ページ本文の見出し（この順番で出力）：
1. 元質問の要約
2. 聞き取り3点メモ
3. 答える前の整理
4. 自分の初稿
5. 自分の最終答弁
6. 弱点
7. 次回使う型

## セットアップ

```bash
pip install -r requirements.txt
export NOTION_API_KEY="secret_xxx"           # Notion インテグレーションのシークレット
export NOTION_TRAINING_LOG_DB_ID="xxxxxxxx"  # 「答弁訓練ログ」DBのID
```

> Notion インテグレーションを「答弁訓練ログ」DB に接続（共有）しておく必要があります。

## 使い方

```bash
# 送信予定の内容を確認（API は呼ばない）
python notion_training_log.py training_logs/2026-06-22_kokuho.json --dry-run

# 実際に1ページ登録する
python notion_training_log.py training_logs/2026-06-22_kokuho.json
```

## 今後の訓練を追加する

`training_logs/2026-06-22_kokuho.json` をコピーして中身を書き換えるだけです。
入力フォーマットはこのサンプル JSON を参照してください。
