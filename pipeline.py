"""
Cloud Pipeline Script — Headless Mastodon scraper for Google Cloud.
No GUI required. Fetches the latest post(s) from a Mastodon instance
and exports the result to the output/ directory.

Usage:
    python pipeline.py
    python pipeline.py --instance https://mastodon.social --limit 1 --format json
    python pipeline.py --action hashtag_timeline --query python --limit 5
"""

import argparse
import json
import os
import sys
from datetime import datetime

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper.api_scraper import MastodonScraper
from scraper.exporters import ExportManager


def main():
    parser = argparse.ArgumentParser(description="Mastodon Cloud Scrape Pipeline")
    parser.add_argument("--instance", default="https://mastodon.social",
                        help="Mastodon instance URL (default: https://mastodon.social)")
    parser.add_argument("--action", default="trends_statuses",
                        choices=[
                            "public_timeline", "local_timeline", "hashtag_timeline",
                            "lookup_account", "account_statuses",
                            "get_status", "status_context",
                            "instance_info",
                            "trends_statuses", "trends_tags", "trends_links",
                            "custom_emojis", "directory",
                        ],
                        help="API action to perform (default: public_timeline)")
    parser.add_argument("--query", default="",
                        help="Query / hashtag / username / status ID (depends on action)")
    parser.add_argument("--limit", type=int, default=1,
                        help="Max number of results (default: 1)")
    parser.add_argument("--format", dest="fmt", default="json",
                        choices=["json", "txt", "html", "bin"],
                        help="Export format (default: json)")
    parser.add_argument("--output-dir", default="output",
                        help="Output directory (default: output/)")

    args = parser.parse_args()

    print(f"[Pipeline] {datetime.now().isoformat()}")
    print(f"[Pipeline] Instance:  {args.instance}")
    print(f"[Pipeline] Action:    {args.action}")
    print(f"[Pipeline] Query:     {args.query or '(none)'}")
    print(f"[Pipeline] Limit:     {args.limit}")
    print(f"[Pipeline] Format:    {args.fmt}")
    print(f"[Pipeline] Output:    {args.output_dir}")
    print()

    # Set up scraper
    scraper = MastodonScraper()
    scraper.configure(args.instance)

    # Build kwargs
    kwargs = {}
    if args.action in ("public_timeline", "local_timeline",
                       "trends_statuses", "trends_tags", "trends_links",
                       "directory"):
        kwargs["limit"] = args.limit
    elif args.action == "hashtag_timeline":
        kwargs["hashtag"] = args.query
        kwargs["limit"] = args.limit
    elif args.action == "lookup_account":
        kwargs["acct"] = args.query
    elif args.action == "account_statuses":
        kwargs["account_id"] = args.query
        kwargs["limit"] = args.limit
    elif args.action == "get_status":
        kwargs["status_id"] = args.query
    elif args.action == "status_context":
        kwargs["status_id"] = args.query

    # Dispatch
    action_map = {
        "public_timeline":   scraper.get_public_timeline,
        "local_timeline":    lambda **kw: scraper.get_public_timeline(local=True, **kw),
        "hashtag_timeline":  scraper.get_hashtag_timeline,
        "lookup_account":    scraper.lookup_account,
        "account_statuses":  scraper.get_account_statuses,
        "get_status":        scraper.get_status,
        "status_context":    scraper.get_status_context,
        "instance_info":     scraper.get_instance_info,
        "trends_statuses":   scraper.get_trends_statuses,
        "trends_tags":       scraper.get_trends_tags,
        "trends_links":      scraper.get_trends_links,
        "custom_emojis":     scraper.get_custom_emojis,
        "directory":         scraper.get_directory,
    }

    print("[Pipeline] Fetching data...")
    result = action_map[args.action](**kwargs)

    # Wrap with metadata
    export_data = {
        "pipeline_run": datetime.now().isoformat(),
        "mastodon_instance": args.instance,
        "action": args.action,
        "query": args.query or None,
        "result_count": len(result) if isinstance(result, list) else 1,
        "data": result,
    }

    # Print summary
    if isinstance(result, list):
        print(f"[Pipeline] Fetched {len(result)} item(s)")
        for i, item in enumerate(result):
            if isinstance(item, dict):
                user = item.get("account_username", "?")
                text = item.get("text", "")[:80].replace("\n", " ")
                print(f"  [{i}] @{user}: {text}")
    elif isinstance(result, dict):
        print(f"[Pipeline] Fetched 1 item")
        print(f"  {json.dumps(result, indent=2, ensure_ascii=False, default=str)[:500]}")

    # Export
    exporter = ExportManager(output_dir=args.output_dir)
    filepath = exporter.export(export_data, args.fmt)
    print(f"\n[Pipeline] Exported to: {filepath}")
    print("[Pipeline] Done.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
