"""CLI tool to inspect, review, and edit golden dataset items for Cite RAG evaluation.

Usage:
    python scripts/review_golden_set.py --stats
    python scripts/review_golden_set.py --list [--split dev|test] [--unreviewed]
    python scripts/review_golden_set.py --view qa_001
    python scripts/review_golden_set.py --mark-reviewed qa_001 [--reviewer "Clinician Name"]
    python scripts/review_golden_set.py --edit-answer qa_001 --answer "Updated clinical ground truth"
"""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

GOLDEN_SET_PATH = Path("eval/golden_set/qa_golden_set.jsonl")


def load_dataset() -> list[dict[str, Any]]:
    if not GOLDEN_SET_PATH.exists():
        raise FileNotFoundError(f"Golden dataset not found at {GOLDEN_SET_PATH}")
    items: list[dict[str, Any]] = []
    with open(GOLDEN_SET_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def save_dataset(items: list[dict[str, Any]]) -> None:
    with open(GOLDEN_SET_PATH, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item) + "\n")


def print_stats(items: list[dict[str, Any]]) -> None:
    total = len(items)
    dev_items = [i for i in items if i.get("split") == "dev"]
    test_items = [i for i in items if i.get("split") == "test"]
    reviewed = [i for i in items if i.get("human_reviewed", False)]

    categories: dict[str, int] = {}
    for item in items:
        cat = item.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    print("=" * 60)
    print("GOLDEN DATASET STATISTICS")
    print("=" * 60)
    print(f"Total items:         {total}")
    print(f"Dev split:           {len(dev_items)} ({len(dev_items) / total * 100:.1f}%)")
    print(f"Held-out test split: {len(test_items)} ({len(test_items) / total * 100:.1f}%)")
    print(f"Human-reviewed:      {len(reviewed)}/{total} ({len(reviewed) / total * 100:.1f}%)")
    print("\nCategories breakdown:")
    for cat, count in sorted(categories.items()):
        print(f"  - {cat:<22}: {count:>3} ({count / total * 100:.1f}%)")
    print("=" * 60)


def list_items(items: list[dict[str, Any]], split: str | None, unreviewed_only: bool) -> None:
    filtered = items
    if split:
        filtered = [i for i in filtered if i.get("split") == split]
    if unreviewed_only:
        filtered = [i for i in filtered if not i.get("human_reviewed", False)]

    print(f"{'ID':<8} {'Split':<6} {'Category':<16} {'Rev?':<5} {'Query'}")
    print("-" * 80)
    for item in filtered:
        rev_status = "✓" if item.get("human_reviewed") else "✗"
        query = item.get("query", "")
        if len(query) > 45:
            query = query[:42] + "..."
        print(
            f"{item.get('id', ''):<8} {item.get('split', ''):<6} {item.get('category', ''):<16} {rev_status:<5} {query}"
        )
    print(f"\nTotal listed: {len(filtered)}")


def view_item(items: list[dict[str, Any]], item_id: str) -> None:
    for item in items:
        if item.get("id") == item_id:
            print("=" * 60)
            print(f"ITEM: {item_id}")
            print("=" * 60)
            print(json.dumps(item, indent=2))
            return
    print(f"Error: Item {item_id} not found.")


def mark_reviewed(items: list[dict[str, Any]], item_id: str, reviewer: str) -> None:
    found = False
    for item in items:
        if item.get("id") == item_id:
            item["human_reviewed"] = True
            item["reviewed_by"] = reviewer
            item["reviewed_at"] = datetime.now(UTC).isoformat()
            found = True
            break
    if found:
        save_dataset(items)
        print(f"Successfully marked {item_id} as reviewed by {reviewer}.")
    else:
        print(f"Error: Item {item_id} not found.")


def edit_item(items: list[dict[str, Any]], item_id: str, field: str, value: str) -> None:
    found = False
    for item in items:
        if item.get("id") == item_id:
            item[field] = value
            item["human_reviewed"] = True
            item["reviewed_at"] = datetime.now(UTC).isoformat()
            found = True
            break
    if found:
        save_dataset(items)
        print(f"Successfully updated {field} for {item_id}.")
    else:
        print(f"Error: Item {item_id} not found.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Review and manage Cite golden evaluation dataset."
    )
    parser.add_argument("--stats", action="store_true", help="Display dataset summary statistics")
    parser.add_argument("--list", action="store_true", help="List dataset items")
    parser.add_argument("--split", choices=["dev", "test"], help="Filter by split (dev or test)")
    parser.add_argument(
        "--unreviewed", action="store_true", help="Filter for unreviewed items only"
    )
    parser.add_argument("--view", type=str, help="View item details by ID")
    parser.add_argument("--mark-reviewed", type=str, help="Mark item ID as reviewed")
    parser.add_argument("--reviewer", type=str, default="ClinicalReviewer", help="Reviewer name")
    parser.add_argument("--edit-query", type=str, help="Item ID to edit query for")
    parser.add_argument("--query", type=str, help="New query text")
    parser.add_argument("--edit-answer", type=str, help="Item ID to edit answer for")
    parser.add_argument("--answer", type=str, help="New answer text")

    args = parser.parse_args()
    items = load_dataset()

    if args.stats:
        print_stats(items)
    elif args.list:
        list_items(items, args.split, args.unreviewed)
    elif args.view:
        view_item(items, args.view)
    elif args.mark_reviewed:
        mark_reviewed(items, args.mark_reviewed, args.reviewer)
    elif args.edit_query and args.query:
        edit_item(items, args.edit_query, "query", args.query)
    elif args.edit_answer and args.answer:
        edit_item(items, args.edit_answer, "expected_answer", args.answer)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
