#!/usr/bin/env python3
"""
Reads Chrome bookmarks from the "AI" folder and generates a plain HTML page.
Handles nested subfolders and shows table of contents.

Usage:
    python sync_bookmarks.py              # generate index.html
    python sync_bookmarks.py --push       # generate + git commit & push
"""

import json
import os
import subprocess
import sys
from datetime import datetime

CHROME_BOOKMARKS = os.path.expanduser(
    "~/Library/Application Support/Google/Chrome/Default/Bookmarks"
)
TARGET_FOLDER = "AI"
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
GIT_AUTHOR = "sanketny8 <2016eeb1087@iitrpr.ac.in>"


def find_folder(node, name):
    """Recursively find a bookmark folder by name."""
    if node.get("type") == "folder" and node.get("name") == name:
        return node
    for child in node.get("children", []):
        result = find_folder(child, name)
        if result:
            return result
    return None


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def slug(name):
    return name.lower().replace(" ", "-").replace("&", "and").replace("/", "-")


def collect_structure(node):
    """Collect full folder structure: top-level links + subfolders with links."""
    top_links = []
    folders = []
    for child in node.get("children", []):
        if child["type"] == "url":
            top_links.append({"name": child["name"], "url": child["url"]})
        elif child["type"] == "folder":
            links = [
                {"name": c["name"], "url": c["url"]}
                for c in child.get("children", [])
                if c["type"] == "url"
            ]
            folders.append({
                "name": child["name"],
                "links": links,
            })
    return top_links, folders


def generate_html(top_links, folders, timestamp):
    """Generate a plain HTML page, no CSS, old-school style."""
    total = len(top_links) + sum(len(f["links"]) for f in folders)
    non_empty = [f for f in folders if f["links"]]
    empty = [f for f in folders if not f["links"]]

    lines = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>AI Bookmarks</title>",
        "</head>",
        "<body>",
        "<h1>AI Bookmarks</h1>",
        f"<p>Last updated: {timestamp} | {total} links | {len(folders)} categories</p>",
        "<hr>",
        "",
        "<!-- Table of Contents -->",
        "<h2>Categories</h2>",
        "<ul>",
    ]

    for folder in non_empty:
        name = esc(folder["name"])
        anchor = slug(folder["name"])
        lines.append(f'  <li><a href="#{anchor}">{name}</a> ({len(folder["links"])})</li>')

    if top_links:
        lines.append(f'  <li><a href="#uncategorized">Uncategorized</a> ({len(top_links)})</li>')

    if empty:
        lines.append(f"  <li><i>{len(empty)} empty categories ready for future bookmarks</i></li>")

    lines.append("</ul>")
    lines.append("<hr>")

    # Subfolders with links
    for folder in non_empty:
        name = esc(folder["name"])
        anchor = slug(folder["name"])
        lines.append(f'<h2 id="{anchor}">{name} ({len(folder["links"])})</h2>')
        lines.append("<ul>")
        for link in folder["links"]:
            lname = esc(link["name"])
            url = esc(link["url"])
            lines.append(f'  <li><a href="{url}">{lname}</a></li>')
        lines.append("</ul>")
        lines.append('<p><a href="#top">[back to top]</a></p>')

    # Top-level uncategorized links
    if top_links:
        lines.append('<h2 id="uncategorized">Uncategorized</h2>')
        lines.append("<ul>")
        for link in top_links:
            lname = esc(link["name"])
            url = esc(link["url"])
            lines.append(f'  <li><a href="{url}">{lname}</a></li>')
        lines.append("</ul>")

    lines.extend([
        "<hr>",
        f"<p><i>{total} links across {len(non_empty)} categories</i></p>",
        '<p><a href="https://github.com/sanketny8/ai-bookmarks">source</a></p>',
        "</body>",
        "</html>",
    ])

    return "\n".join(lines)


def git_push(repo_dir):
    """Commit and push changes."""
    def run(cmd):
        subprocess.run(cmd, cwd=repo_dir, check=True)

    run(["git", "add", "index.html"])
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=repo_dir
    )
    if result.returncode == 0:
        print("No changes to commit.")
        return
    run(["git", "commit", "--author", GIT_AUTHOR, "-m", "Update AI bookmarks"])
    run(["git", "push", "origin", "main"])
    print("Pushed to GitHub.")


def main():
    if not os.path.exists(CHROME_BOOKMARKS):
        print(f"Chrome bookmarks not found at: {CHROME_BOOKMARKS}")
        sys.exit(1)

    with open(CHROME_BOOKMARKS) as f:
        data = json.load(f)

    target = None
    for root in data["roots"].values():
        if isinstance(root, dict):
            target = find_folder(root, TARGET_FOLDER)
            if target:
                break

    if not target:
        print(f"Folder '{TARGET_FOLDER}' not found in bookmarks.")
        sys.exit(1)

    top_links, folders = collect_structure(target)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    html = generate_html(top_links, folders, timestamp)

    with open(OUTPUT_FILE, "w") as f:
        f.write(html)

    total = len(top_links) + sum(len(f["links"]) for f in folders)
    print(f"Generated {OUTPUT_FILE} ({total} links, {len(folders)} categories)")

    if "--push" in sys.argv:
        git_push(os.path.dirname(os.path.abspath(__file__)))


if __name__ == "__main__":
    main()
