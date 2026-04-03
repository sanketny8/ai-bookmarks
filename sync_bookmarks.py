#!/usr/bin/env python3
"""
Reads Chrome bookmarks from the "AI" folder and generates a plain HTML page.

Usage:
    python sync_bookmarks.py              # generate index.html
    python sync_bookmarks.py --push       # generate + git commit & push
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

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


def collect_links(node):
    """Collect all links and subfolders from a bookmark folder node."""
    links = []
    subfolders = []
    for child in node.get("children", []):
        if child["type"] == "url":
            links.append({"name": child["name"], "url": child["url"]})
        elif child["type"] == "folder" and child["name"] != "New folder":
            sub_links = []
            for sub_child in child.get("children", []):
                if sub_child["type"] == "url":
                    sub_links.append({"name": sub_child["name"], "url": sub_child["url"]})
            if sub_links:
                subfolders.append({"name": child["name"], "links": sub_links})
    return links, subfolders


def generate_html(links, subfolders, timestamp):
    """Generate a plain HTML page, no CSS, old-school style."""
    lines = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset=\"utf-8\">",
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
        "<title>AI Bookmarks</title>",
        "</head>",
        "<body>",
        "<h1>AI Bookmarks</h1>",
        f"<p>Last updated: {timestamp}</p>",
        "<hr>",
    ]

    # Main AI folder links
    if links:
        lines.append("<h2>AI</h2>")
        lines.append("<ul>")
        for link in links:
            name = link["name"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            url = link["url"].replace("&", "&amp;")
            lines.append(f'  <li><a href="{url}">{name}</a></li>')
        lines.append("</ul>")

    # Subfolders
    for folder in subfolders:
        folder_name = folder["name"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        lines.append(f"<h2>{folder_name}</h2>")
        lines.append("<ul>")
        for link in folder["links"]:
            name = link["name"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            url = link["url"].replace("&", "&amp;")
            lines.append(f'  <li><a href="{url}">{name}</a></li>')
        lines.append("</ul>")

    total = len(links) + sum(len(f["links"]) for f in subfolders)
    lines.extend([
        "<hr>",
        f"<p><i>{total} links</i></p>",
        "</body>",
        "</html>",
    ])

    return "\n".join(lines)


def git_push(repo_dir):
    """Commit and push changes."""
    def run(cmd):
        subprocess.run(cmd, cwd=repo_dir, check=True)

    run(["git", "add", "index.html"])
    # Check if there are changes to commit
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

    # Search all roots for the target folder
    target = None
    for root in data["roots"].values():
        if isinstance(root, dict):
            target = find_folder(root, TARGET_FOLDER)
            if target:
                break

    if not target:
        print(f"Folder '{TARGET_FOLDER}' not found in bookmarks.")
        sys.exit(1)

    links, subfolders = collect_links(target)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    html = generate_html(links, subfolders, timestamp)

    with open(OUTPUT_FILE, "w") as f:
        f.write(html)

    total = len(links) + sum(len(f["links"]) for f in subfolders)
    print(f"Generated {OUTPUT_FILE} ({total} links)")

    if "--push" in sys.argv:
        git_push(os.path.dirname(os.path.abspath(__file__)))


if __name__ == "__main__":
    main()
