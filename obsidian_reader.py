#!/usr/bin/env python3
"""
Obsidian Vault Reader with Claude API
Reads Obsidian .md files from a vault and lets you query them using Claude.
"""

import os
import re
import sys
import argparse
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("Please install anthropic: pip install anthropic")
    sys.exit(1)


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from a markdown file."""
    frontmatter = {}
    body = content

    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            fm_text = content[3:end].strip()
            body = content[end + 3:].strip()
            for line in fm_text.splitlines():
                if ":" in line:
                    key, _, value = line.partition(":")
                    frontmatter[key.strip()] = value.strip()

    return frontmatter, body


def extract_wikilinks(content: str) -> list[str]:
    """Extract [[wikilinks]] from Obsidian markdown."""
    return re.findall(r"\[\[([^\]]+)\]\]", content)


def read_vault(vault_path: str) -> list[dict]:
    """Read all markdown files from an Obsidian vault."""
    vault = Path(vault_path)
    if not vault.exists():
        print(f"Error: Vault path '{vault_path}' does not exist.")
        sys.exit(1)

    notes = []
    for md_file in vault.rglob("*.md"):
        # Skip .obsidian directory and trash
        if ".obsidian" in md_file.parts or ".trash" in md_file.parts:
            continue

        try:
            content = md_file.read_text(encoding="utf-8")
            frontmatter, body = parse_frontmatter(content)
            wikilinks = extract_wikilinks(body)
            rel_path = md_file.relative_to(vault)

            notes.append({
                "path": str(rel_path),
                "title": md_file.stem,
                "frontmatter": frontmatter,
                "body": body,
                "wikilinks": wikilinks,
                "full_content": content,
            })
        except Exception as e:
            print(f"Warning: Could not read {md_file}: {e}")

    return notes


def search_notes(notes: list[dict], query: str) -> list[dict]:
    """Simple keyword search across notes."""
    query_lower = query.lower()
    results = []
    for note in notes:
        if (query_lower in note["title"].lower() or
                query_lower in note["body"].lower()):
            results.append(note)
    return results


def build_context(notes: list[dict], max_chars: int = 50000) -> str:
    """Build a text context from notes for Claude, respecting a character limit."""
    context_parts = []
    total_chars = 0

    for note in notes:
        entry = f"## {note['title']}\nFile: {note['path']}\n\n{note['body']}\n\n---\n"
        if total_chars + len(entry) > max_chars:
            context_parts.append(f"## {note['title']}\nFile: {note['path']}\n[Content truncated due to size]\n\n---\n")
        else:
            context_parts.append(entry)
            total_chars += len(entry)

    return "".join(context_parts)


def query_claude(notes: list[dict], question: str) -> str:
    """Send notes context and a question to Claude."""
    client = anthropic.Anthropic()

    context = build_context(notes)
    prompt = f"""以下はObsidianのノートです。これらのノートを参考に質問に答えてください。

<notes>
{context}
</notes>

質問: {question}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text


def list_notes(notes: list[dict]) -> None:
    """Print a summary list of all notes."""
    print(f"\nFound {len(notes)} notes in vault:\n")
    for note in sorted(notes, key=lambda n: n["path"]):
        tags = note["frontmatter"].get("tags", "")
        link_count = len(note["wikilinks"])
        print(f"  {note['path']}")
        if tags:
            print(f"    Tags: {tags}")
        if link_count:
            print(f"    Links: {link_count} wikilinks")


def main():
    parser = argparse.ArgumentParser(
        description="Read Obsidian vault files and query them with Claude"
    )
    parser.add_argument("vault", help="Path to your Obsidian vault directory")
    parser.add_argument(
        "--list", action="store_true", help="List all notes in the vault"
    )
    parser.add_argument(
        "--search", metavar="KEYWORD", help="Search notes by keyword"
    )
    parser.add_argument(
        "--ask", metavar="QUESTION", help="Ask Claude a question about your notes"
    )
    parser.add_argument(
        "--ask-about",
        metavar="KEYWORD",
        help="Limit Claude's context to notes matching this keyword",
    )

    args = parser.parse_args()

    print(f"Reading vault: {args.vault}")
    notes = read_vault(args.vault)
    print(f"Loaded {len(notes)} notes.")

    if args.list:
        list_notes(notes)

    if args.search:
        results = search_notes(notes, args.search)
        print(f"\nSearch results for '{args.search}': {len(results)} notes found\n")
        for note in results:
            print(f"  {note['path']}: {note['title']}")
            snippet = note["body"][:200].replace("\n", " ")
            print(f"    ...{snippet}...\n")

    if args.ask:
        context_notes = notes
        if args.ask_about:
            context_notes = search_notes(notes, args.ask_about)
            print(f"\nUsing {len(context_notes)} notes matching '{args.ask_about}' as context.")

        if not context_notes:
            print("No notes found to use as context.")
            return

        print(f"\nAsking Claude about {len(context_notes)} notes...")
        answer = query_claude(context_notes, args.ask)
        print(f"\n--- Claude's Answer ---\n{answer}\n")


if __name__ == "__main__":
    main()
