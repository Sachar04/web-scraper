"""
Image Crawler Cloud Function — Downloads images and stores them in Cloud Storage
Triggered by Pub/Sub messages containing image URLs.
Multiple instances of this function run in parallel for concurrent crawling.

GCP Resources:
  - This function (Cloud Functions - serverless compute, multiple instances)
  - Pub/Sub (receives crawl task messages)
  - Cloud Storage (stores downloaded images persistently)
  - Cloud Logging (automatic)
"""

import base64
import hashlib
import json
import os
from urllib.parse import urlparse

import requests
from google.cloud import storage


# ─── Configuration ────────────────────────────────────────────
BUCKET_NAME = os.environ.get("GCS_BUCKET", "")


# ─── Cloud Function Entry Point ──────────────────────────────
def download_image(event, context):
    """
    Cloud Function entry point. Triggered by Pub/Sub message.
    Each message contains one image URL to download.
    Multiple instances of this function run in parallel.
    """
    # Decode Pub/Sub message
    if "data" in event:
        message_data = base64.b64decode(event["data"]).decode("utf-8")
    else:
        print("[Crawler] No data in event")
        return "No data", 400

    try:
        task = json.loads(message_data)
    except json.JSONDecodeError as e:
        print(f"[Crawler] Invalid JSON: {e}")
        return "Invalid JSON", 400

    image_url = task.get("image_url", "")
    hashtag = task.get("hashtag", "unknown")

    if not image_url:
        print("[Crawler] No image_url in task")
        return "No URL", 400

    print(f"[Crawler] Processing: {image_url} (#{hashtag})")

    # Download the image
    try:
        resp = requests.get(image_url, timeout=30, stream=True)
        resp.raise_for_status()
        image_data = resp.content
        content_type = resp.headers.get("Content-Type", "image/jpeg")
    except Exception as e:
        print(f"[Crawler] Download failed for {image_url}: {e}")
        return f"Download failed: {e}", 500

    # Determine filename using URL hash (deduplication)
    url_hash = hashlib.sha256(image_url.encode()).hexdigest()[:16]
    parsed = urlparse(image_url)
    path = parsed.path
    ext = os.path.splitext(path)[1] or ".jpg"
    filename = f"{url_hash}{ext}"

    # Upload to Cloud Storage
    blob_path = f"images/{hashtag}/{filename}"

    try:
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(blob_path)

        # Skip if already exists (extra deduplication layer)
        if blob.exists():
            print(f"[Crawler] Already exists: gs://{BUCKET_NAME}/{blob_path}")
            return "Already exists", 200

        blob.upload_from_string(image_data, content_type=content_type)
        # Make publicly readable for the thumbnail website
        blob.make_public()

        print(f"[Crawler] Stored: gs://{BUCKET_NAME}/{blob_path} ({len(image_data)} bytes)")
    except Exception as e:
        print(f"[Crawler] Upload failed: {e}")
        return f"Upload failed: {e}", 500

    return f"OK - {blob_path}", 200
