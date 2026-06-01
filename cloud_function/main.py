"""
Google Cloud Function — Mastodon Web Scraper Pipeline
Triggered by Pub/Sub. Scrapes trending Mastodon posts and saves to GCS bucket.

GCP Resources used:
  1. Cloud Functions (this code - serverless compute)
  2. Cloud Storage (GCS bucket - stores scraped JSON output)
  3. Cloud Pub/Sub (trigger mechanism)
  4. Cloud Scheduler (cron job that publishes to Pub/Sub)
  5. Cloud Logging (automatic with Cloud Functions - logs all print statements)
"""

import json
import os
import re
import time
from datetime import datetime

import requests
from google.cloud import storage


# ─── Configuration ────────────────────────────────────────────
INSTANCE_URL = os.environ.get("MASTODON_INSTANCE", "https://mastodon.social")
BUCKET_NAME = os.environ.get("GCS_BUCKET", "web-scraper-output-bucket")
SCRAPE_LIMIT = int(os.environ.get("SCRAPE_LIMIT", "1"))


# ─── Mastodon Scraper (inline, no external deps beyond requests) ──
class MastodonScraper:
    def __init__(self, instance_url):
        self.instance_url = instance_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "CloudWebScraper/1.0",
            "Accept": "application/json",
        })

    def get_trends_statuses(self, limit=1):
        url = f"{self.instance_url}/api/v1/trends/statuses"
        resp = self.session.get(url, params={"limit": limit}, timeout=15)
        resp.raise_for_status()
        return [self._parse_status(s) for s in resp.json()]

    def get_public_timeline(self, limit=1):
        url = f"{self.instance_url}/api/v1/timelines/public"
        resp = self.session.get(url, params={"limit": limit}, timeout=15)
        resp.raise_for_status()
        return [self._parse_status(s) for s in resp.json()]

    def get_instance_info(self):
        url = f"{self.instance_url}/api/v2/instance"
        resp = self.session.get(url, timeout=15)
        if resp.status_code != 200:
            resp = self.session.get(f"{self.instance_url}/api/v1/instance", timeout=15)
        resp.raise_for_status()
        return resp.json()

    def _parse_status(self, s):
        account = s.get("account", {})
        media = []
        for att in s.get("media_attachments", []):
            media.append({
                "type": att.get("type", ""),
                "url": att.get("url", ""),
                "description": att.get("description", ""),
            })
        return {
            "id": s.get("id", ""),
            "created_at": s.get("created_at", ""),
            "text": self._strip_html(s.get("content", "")),
            "url": s.get("url", ""),
            "reblogs_count": s.get("reblogs_count", 0),
            "favourites_count": s.get("favourites_count", 0),
            "language": s.get("language", ""),
            "account_username": account.get("username", ""),
            "account_display_name": account.get("display_name", ""),
            "media_attachments": media,
            "tags": [t.get("name", "") for t in s.get("tags", [])],
        }

    @staticmethod
    def _strip_html(html):
        text = re.sub(r"<br\s*/?>", "\n", html)
        text = re.sub(r"</p>\s*<p>", "\n\n", text)
        text = re.sub(r"<[^>]+>", "", text)
        text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        return text.strip()


# ─── Cloud Function Entry Point ──────────────────────────────
def scrape_mastodon(event, context):
    """
    Cloud Function entry point. Triggered by Pub/Sub message.
    Scrapes Mastodon and uploads result to Cloud Storage.
    """
    print(f"[Pipeline] Function triggered at {datetime.utcnow().isoformat()}Z")
    print(f"[Pipeline] Instance: {INSTANCE_URL}")
    print(f"[Pipeline] Limit: {SCRAPE_LIMIT}")
    print(f"[Pipeline] Bucket: {BUCKET_NAME}")

    # 1. Scrape data
    scraper = MastodonScraper(INSTANCE_URL)

    try:
        result = scraper.get_trends_statuses(limit=SCRAPE_LIMIT)
        action = "trends_statuses"
    except Exception as e:
        print(f"[Pipeline] trends_statuses failed ({e}), trying instance_info...")
        result = scraper.get_instance_info()
        action = "instance_info"

    # 2. Build export payload
    payload = {
        "pipeline_run": datetime.utcnow().isoformat() + "Z",
        "mastodon_instance": INSTANCE_URL,
        "action": action,
        "result_count": len(result) if isinstance(result, list) else 1,
        "data": result,
    }

    json_output = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
    print(f"[Pipeline] Scraped {payload['result_count']} item(s)")

    # Preview first item
    if isinstance(result, list) and result:
        item = result[0]
        print(f"[Pipeline] First post by @{item.get('account_username', '?')}: "
              f"{item.get('text', '')[:100]}")

    # 3. Upload to Cloud Storage
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    blob_name = f"scrapes/mastodon_{action}_{timestamp}.json"

    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(json_output, content_type="application/json")

    print(f"[Pipeline] Uploaded to gs://{BUCKET_NAME}/{blob_name}")
    print(f"[Pipeline] Done.")

    return f"OK - scraped {payload['result_count']} items -> gs://{BUCKET_NAME}/{blob_name}"
