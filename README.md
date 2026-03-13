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
