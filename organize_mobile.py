#!/usr/bin/env python3
"""
Moves AI-related mobile bookmarks into the AI folder's category structure.
Non-AI bookmarks stay in Mobile Bookmarks.

Usage:
    python organize_mobile.py          # dry run
    python organize_mobile.py --apply  # modify Chrome bookmarks
"""

import json
import os
import shutil
import sys
from datetime import datetime

CHROME_BOOKMARKS = os.path.expanduser(
    "~/Library/Application Support/Google/Chrome/Default/Bookmarks"
)

# Mobile bookmarks that are NOT AI — leave them in Mobile
NOT_AI = [
    "chrome-native://newtab",
    "keka.com",
    "amazon.in",
    "paypal.atlassian.net",
    "miro.com/app",
    "grok.com/chat/93d00d17",  # specific chat, not the tool
    "pub.dev/packages/google_multimodal",
    "daily-demos/daily-flutter",
]

# Map mobile bookmarks to AI subfolder categories
MOBILE_RULES = [
    ("GPU & CUDA", [
        "cuda", "gpu", "triton", "kernel", "leetgpu",
    ]),
    ("RL & Alignment", [
        "reinforcement learn", "rl:", "rl foundation",
        "state of reinforcement",
    ]),
    ("Agents & MCP", [
        "agent", "mcp", "langchain",
    ]),
    ("Diffusion Models", [
        "diffusion", "variational autoencoder", "latent variable",
    ]),
    ("Multimodal Models", [
        "multimodal", "magma", "llava",
    ]),
    ("Memory & Context", [
        "memory", "rag",
    ]),
    ("Research Papers", [
        "arxiv", "alphaxiv", "paper", "paperfinder",
    ]),
    ("Books & PDFs", [
        "book", "bishopbook",
    ]),
    ("Blogs & People", [
        "blog", "substack", "newsletter", "yang song",
        "aman.ai", "raschka", "theaisummer",
    ]),
    ("MLOps & Deployment", [
        "production-machine-learning", "full stack deep learning",
        "fullstackdeeplearning", "storage",
    ]),
    ("Courses & Learning", [
        "course", "lesson", "lecture", "tutorial",
        "pyspur",
    ]),
    ("Tools & Repos", [
        "github.com", "huggingface", "grok.com",
        "awesome", "open source",
    ]),
    ("Prompt Engineering", [
        "prompt",
    ]),
    ("AI News & Newsletters", [
        "newsletter", "ai summer",
    ]),
    ("Podcasts & Videos", [
        "youtube.com",
    ]),
    ("System Design", [
        "system design", "recsys", "recommendation",
    ]),
]


def is_not_ai(url):
    url_lower = url.lower()
    for pattern in NOT_AI:
        if pattern.lower() in url_lower:
            return True
    return False


def categorize_mobile(title, url):
    text = (title + " " + url).lower()
    for folder_name, keywords in MOBILE_RULES:
        for kw in keywords:
            if kw in text:
                return folder_name
    return None


def find_folder(node, name):
    if node.get("type") == "folder" and node.get("name") == name:
        return node
    for child in node.get("children", []):
        result = find_folder(child, name)
        if result:
            return result
    return None


def main():
    dry_run = "--apply" not in sys.argv

    with open(CHROME_BOOKMARKS) as f:
        data = json.load(f)

    # Find Mobile Bookmarks
    mobile = None
    for key, val in data["roots"].items():
        if isinstance(val, dict) and val.get("name") == "Mobile Bookmarks":
            mobile = val
            break

    if not mobile:
        print("Mobile Bookmarks not found")
        sys.exit(1)

    # Find AI folder
    ai_folder = None
    for root in data["roots"].values():
        if isinstance(root, dict):
            ai_folder = find_folder(root, "AI")
            if ai_folder:
                break

    if not ai_folder:
        print("AI folder not found")
        sys.exit(1)

    # Build map of existing AI subfolders
    ai_subfolders = {}
    for child in ai_folder["children"]:
        if child["type"] == "folder":
            ai_subfolders[child["name"]] = child

    mobile_links = [c for c in mobile.get("children", []) if c["type"] == "url"]
    print(f"Mobile bookmarks: {len(mobile_links)}")

    move_to_ai = {}
    keep_in_mobile = []
    not_ai_links = []

    for link in mobile_links:
        if is_not_ai(link["url"]):
            not_ai_links.append(link)
            continue

        cat = categorize_mobile(link["name"], link["url"])
        if cat:
            move_to_ai.setdefault(cat, []).append(link)
        else:
            keep_in_mobile.append(link)

    # Print plan
    total_moved = 0
    for cat, links in sorted(move_to_ai.items()):
        exists = "exists" if cat in ai_subfolders else "NEW"
        print(f"\n  -> {cat} [{exists}] ({len(links)} links)")
        for link in links:
            print(f"     {link['name'][:75]}")
        total_moved += len(links)

    if not_ai_links:
        print(f"\n  Stays in Mobile (not AI) ({len(not_ai_links)} links)")
        for link in not_ai_links:
            print(f"     {link['name'][:75]}")

    if keep_in_mobile:
        print(f"\n  Stays in Mobile (uncategorized) ({len(keep_in_mobile)} links)")
        for link in keep_in_mobile:
            print(f"     {link['name'][:75]}")

    print(f"\n--- Summary ---")
    print(f"  {total_moved} moved to AI subfolders")
    print(f"  {len(not_ai_links)} non-AI kept in Mobile")
    print(f"  {len(keep_in_mobile)} uncategorized kept in Mobile")
    print(f"  {total_moved + len(not_ai_links) + len(keep_in_mobile)} total (0 lost)")

    if dry_run:
        print(f"\n  DRY RUN — run with --apply to modify bookmarks.")
        return

    # Backup
    backup_path = CHROME_BOOKMARKS + f".backup.mobile.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(CHROME_BOOKMARKS, backup_path)
    print(f"\nBackup: {backup_path}")

    # Move links to AI subfolders
    moved_urls = set()
    for cat, links in move_to_ai.items():
        if cat in ai_subfolders:
            ai_subfolders[cat]["children"].extend(links)
        else:
            print(f"  Warning: folder '{cat}' not found in AI — skipping")
            continue
        for link in links:
            moved_urls.add(link["url"])

    # Remove moved links from Mobile
    mobile["children"] = [
        c for c in mobile["children"]
        if c.get("type") != "url" or c.get("url") not in moved_urls
    ]

    with open(CHROME_BOOKMARKS, "w") as f:
        json.dump(data, f, indent=3)

    print(f"Done — {total_moved} mobile bookmarks moved to AI folder.")
    print("Restart Chrome to see changes.")


if __name__ == "__main__":
    main()
