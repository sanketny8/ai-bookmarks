#!/usr/bin/env python3
"""
Organizes the entire AI bookmark folder in Chrome — top-level AND subfolders.
Merges everything, re-categorizes, creates clean folder structure.

Usage:
    python organize_bookmarks.py          # dry run
    python organize_bookmarks.py --apply  # modify Chrome bookmarks (backup created)
"""

import json
import os
import re
import shutil
import sys
from datetime import datetime

CHROME_BOOKMARKS = os.path.expanduser(
    "~/Library/Application Support/Google/Chrome/Default/Bookmarks"
)

# Category rules: (folder_name, keywords_in_title_or_url)
# First match wins. More specific rules go first.
RULES = [
    # --- Junk / Non-AI (separate so you can see them) ---
    ("Non-AI / Personal", [
        "harmonshirt", "super sale", "netmirror", "movies and series",
        "instagram.com", "manji mali", "firebase studio", "matchguard",
        "spotyy", "uplers", "zscaler", "internet security",
        "new tab", "google search",
    ]),

    # --- GPU & CUDA ---
    ("GPU & CUDA", [
        "gpu", "cuda", "kernel", "leetgpu", "mojo puzzle",
        "modal.com", "accelerated-computing", "nvidia",
        "matmul", "compute-first", "unet.cu", "tpu deep dive",
        "domain specific architectures for ai inference",
    ]),

    # --- Robotics & Embodied AI ---
    ("Robotics & Embodied AI", [
        "robot", "embodied", "lerobot", "gradient robotics",
        "cheaprobotarm",
    ]),

    # --- RL & Alignment ---
    ("RL & Alignment", [
        "reinforcement learn", "rl for reasoning", "rlhf", "dpo",
        "alignment", "reward", "deep rl", "10-703",
        "self-improving", "constitutional ai", "post-training 101",
        "avatarl", "parallel-r1", "parathinker",
    ]),

    # --- Interpretability ---
    ("Interpretability", [
        "monosemantic", "mechanistic", "interpretab",
        "activation atlas", "transformer circuits", "distill",
        "feature visual", "superposition",
    ]),

    # --- 1-bit & Quantization ---
    ("1-bit & Quantization", [
        "1-bit", "1.58 bit", "bitnet", "quantiz",
        "sampler",
    ]),

    # --- Inference & Serving ---
    ("Inference & Serving", [
        "vllm", "inference", "serving", "pagedattention",
        "paged attention", "prompt caching", "throughput",
        "latency", "bloom inference", "llm-numbers",
        "tensor parallelism", "kv cache", "tgi", "triton",
        "onnx", "tensorrt", "nondeterminism",
        "how to scale your model", "attention sink",
        "streaming", "memory decoder",
    ]),

    # --- Agents & MCP ---
    ("Agents & MCP", [
        "agent", "mcp", "langchain", "langgraph", "orchestr",
        "agentic", "tool use", "crewai", "maestro",
        "agentic design pattern", "google-agentic",
    ]),

    # --- World Models ---
    ("World Models", [
        "world model",
    ]),

    # --- Diffusion Models ---
    ("Diffusion Models", [
        "diffusion", "latent diffusion", "audioldm",
        "flow matching", "generative modelling in latent",
        "text-to-audio", "text-to-image", "vit backbone",
    ]),

    # --- Transformers & Attention ---
    ("Transformers & Attention", [
        "illustrated transformer", "transformer",
        "attention variant", "from scratch.*peter",
        "atlas.*memorize", "competition and attraction",
    ]),

    # --- Information Retrieval & RAG ---
    ("Information Retrieval & RAG", [
        "information retrieval", "retrieval", "search engine",
        "rag", "embedding",
    ]),

    # --- LLM Training & Fine-tuning ---
    ("LLM Training & Fine-tuning", [
        "fine-tun", "fine tun", "training playbook",
        "lora", "qlora", "peft", "deepspeed",
        "model fusion",
    ]),

    # --- Research Papers (arxiv by ID) ---
    ("Research Papers", [
        "arxiv.org/abs", "arxiv.org/pdf", "arxiv.org/html",
        r"\d{4}\.\d{4,5}", "alphaXiv",
        "tech_report", "technical report",
        "reading list",
    ]),

    # --- Books & PDFs ---
    ("Books & PDFs", [
        "book", ".pdf", "goodfellow", "drive.google.com/drive",
        "d2l-en", "d2l.ai", "ml-engineering", "tech-books-library",
        "udlbook", "chapters - deep learning",
        "harvard-edge/cs249r",
    ]),

    # --- Courses & Learning ---
    ("Courses & Learning", [
        "course", "roadmap", "tutorial", "lesson",
        "zero to mastery", "beginner", "100days", "100-days",
        "deep-ml", "sigmoidit", "quickstart", "introduction",
        "cs294", "cs329", "internship", "assignments",
        "from scratch", "learn", "cheatsheet",
        "practical deep learning", "pytorch in one hour",
        "how i got a job", "career advice",
    ]),

    # --- Blogs & People ---
    ("Blogs & People", [
        "blog", "substack", "weblog", "lil'log", "lillog",
        "newsletter", "gordic", "willison", "raschka",
        "kipply", "kalomaze", "ezyang", "sanglard",
        "bearblog", "jeremyjordan", "suvash", "ziming liu",
        "sander.ai", "sander dieleman", "weers",
        "yacine", "charapko", "fchollet", "beauty of saas",
        "aleksa", "tokens for thoughts",
    ]),

    # --- Tools & Repos ---
    ("Tools & Repos", [
        "github.com", "huggingface", "spaces",
        "ml resources", "awesome-", "curated list",
        "petals", "turbopuffer", "hydradb",
        "modal-jazz", "microgpt", "genai-processors",
        "gpt-oss", "qwen", "kimi-k2", "deepseek",
        "openai", "anthropic", "advancing ai",
    ]),
]


def categorize(title, url):
    """Return the category for a bookmark based on title and URL."""
    text = (title + " " + url).lower()
    for folder_name, keywords in RULES:
        for kw in keywords:
            if kw.startswith("r\\") or "\\" in kw:
                if re.search(kw, text):
                    return folder_name
            elif kw.lower() in text:
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


def collect_all_links(node):
    """Recursively collect ALL url bookmarks from a folder tree."""
    links = []
    for child in node.get("children", []):
        if child["type"] == "url":
            links.append(child)
        elif child["type"] == "folder":
            links.extend(collect_all_links(child))
    return links


def make_folder(name):
    return {
        "children": [],
        "date_added": str(int(datetime.now().timestamp() * 1e6)),
        "date_last_used": "0",
        "date_modified": str(int(datetime.now().timestamp() * 1e6)),
        "guid": "",
        "id": "999",
        "name": name,
        "type": "folder",
    }


def dedup_links(links):
    """Remove duplicate URLs, keep first occurrence."""
    seen = set()
    unique = []
    for link in links:
        url = link["url"]
        if url not in seen:
            seen.add(url)
            unique.append(link)
    return unique


def main():
    dry_run = "--apply" not in sys.argv

    with open(CHROME_BOOKMARKS) as f:
        data = json.load(f)

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

    # Collect ALL links from AI folder and all subfolders
    all_links = collect_all_links(ai_folder)
    all_links = dedup_links(all_links)
    print(f"Total links found (deduplicated): {len(all_links)}")
    print()

    # Categorize everything
    categories = {}
    uncategorized = []
    for link in all_links:
        cat = categorize(link["name"], link["url"])
        if cat:
            categories.setdefault(cat, []).append(link)
        else:
            uncategorized.append(link)

    # Print plan
    total_sorted = 0
    for cat, links in sorted(categories.items()):
        print(f"\n{'='*60}")
        print(f"  {cat} ({len(links)} links)")
        print(f"{'='*60}")
        for link in links:
            print(f"   {link['name'][:80]}")
        total_sorted += len(links)

    if uncategorized:
        print(f"\n{'='*60}")
        print(f"  Uncategorized — stays in top level ({len(uncategorized)} links)")
        print(f"{'='*60}")
        for link in uncategorized:
            print(f"   {link['name'][:80]}")

    print(f"\n--- Summary ---")
    print(f"  {len(categories)} folders")
    print(f"  {total_sorted} categorized")
    print(f"  {len(uncategorized)} uncategorized")
    print(f"  {total_sorted + len(uncategorized)} total (0 lost)")

    if dry_run:
        print(f"\n  DRY RUN — no changes made. Run with --apply to modify bookmarks.")
        return

    # Backup
    backup_path = CHROME_BOOKMARKS + f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(CHROME_BOOKMARKS, backup_path)
    print(f"\nBackup saved to: {backup_path}")

    # Pre-created empty folders for future bookmarks
    EMPTY_FOLDERS = [
        "Computer Vision",
        "MLOps & Deployment",
        "Math & Theory",
        "Multimodal Models",
        "NLP & Text",
        "Audio & Speech",
        "System Design",
        "Datasets & Benchmarks",
        "Security & Safety",
        "AI News & Newsletters",
        "Podcasts & Videos",
        "Open Source Models",
        "Prompt Engineering",
        "AI Startups & Products",
        "Distributed Training",
        "Memory & Context",
        "Code Generation",
        "AI Hardware",
    ]

    # Build new children list for AI folder
    new_children = []

    all_folder_names = set()
    for cat, links in sorted(categories.items()):
        folder = make_folder(cat)
        folder["children"] = links
        new_children.append(folder)
        all_folder_names.add(cat)

    # Add empty folders that don't already exist
    for name in sorted(EMPTY_FOLDERS):
        if name not in all_folder_names:
            new_children.append(make_folder(name))
            all_folder_names.add(name)

    # Sort all folders alphabetically, uncategorized links at the end
    new_children.sort(key=lambda x: (x["type"] != "folder", x.get("name", "")))

    # Uncategorized stay as top-level links
    new_children.extend(uncategorized)

    ai_folder["children"] = new_children

    with open(CHROME_BOOKMARKS, "w") as f:
        json.dump(data, f, indent=3)

    total_folders = sum(1 for c in new_children if c["type"] == "folder")
    empty_count = sum(1 for c in new_children if c["type"] == "folder" and not c["children"])
    print(f"Bookmarks updated — {total_folders} folders ({empty_count} empty, ready for future use).")
    print("Open a new Chrome tab to see changes.")


if __name__ == "__main__":
    main()
