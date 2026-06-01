"""
Frontend Cloud Function — Tweet/Toot Crawler Web Interface
HTTP-triggered. Serves a web page where users can:
  1. Enter a hashtag to crawl images from Mastodon
  2. View previously crawled images as thumbnails

GCP Resources:
  - This function (Cloud Functions - serverless compute)
  - Pub/Sub (publishes crawl tasks for image URLs)
  - Cloud Storage (reads stored images for thumbnail display)
"""

import json
import os
import hashlib
from datetime import datetime

import requests
from google.cloud import storage, pubsub_v1
import functions_framework


# ─── Configuration ────────────────────────────────────────────
MASTODON_INSTANCE = os.environ.get("MASTODON_INSTANCE", "https://mastodon.social")
BUCKET_NAME = os.environ.get("GCS_BUCKET", "")
PUBSUB_TOPIC = os.environ.get("PUBSUB_TOPIC", "crawl-tasks")
PROJECT_ID = os.environ.get("GCP_PROJECT", "")


# ─── HTML Templates ──────────────────────────────────────────
HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tweet/Toot Crawler</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            color: #e0e0e0;
            padding: 2rem;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 {
            text-align: center;
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(90deg, #00d2ff, #7b2ff7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle {
            text-align: center;
            color: #888;
            margin-bottom: 2rem;
            font-size: 1.1rem;
        }
        .search-box {
            display: flex;
            justify-content: center;
            gap: 1rem;
            margin-bottom: 2rem;
            flex-wrap: wrap;
        }
        input[type="text"] {
            padding: 0.8rem 1.5rem;
            font-size: 1.1rem;
            border: 2px solid #333;
            border-radius: 8px;
            background: rgba(255,255,255,0.05);
            color: #fff;
            width: 300px;
            outline: none;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus { border-color: #7b2ff7; }
        button {
            padding: 0.8rem 2rem;
            font-size: 1.1rem;
            border: none;
            border-radius: 8px;
            background: linear-gradient(135deg, #7b2ff7, #00d2ff);
            color: #fff;
            cursor: pointer;
            font-weight: bold;
            transition: transform 0.2s, opacity 0.2s;
        }
        button:hover { transform: scale(1.05); opacity: 0.9; }
        .status {
            text-align: center;
            padding: 1rem;
            margin-bottom: 1.5rem;
            border-radius: 8px;
            background: rgba(123, 47, 247, 0.1);
            border: 1px solid rgba(123, 47, 247, 0.3);
        }
        .status.success { background: rgba(0, 210, 255, 0.1); border-color: rgba(0, 210, 255, 0.3); }
        .status.error { background: rgba(255, 50, 50, 0.1); border-color: rgba(255, 50, 50, 0.3); }
        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 1rem;
        }
        .gallery img {
            width: 100%;
            height: 200px;
            object-fit: cover;
            border-radius: 8px;
            border: 2px solid #333;
            transition: transform 0.3s, border-color 0.3s;
        }
        .gallery img:hover { transform: scale(1.05); border-color: #7b2ff7; }
        .gallery-item {
            position: relative;
        }
        .gallery-item .label {
            position: absolute;
            bottom: 8px;
            left: 8px;
            background: rgba(0,0,0,0.7);
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            color: #ccc;
        }
        .empty-state {
            text-align: center;
            padding: 3rem;
            color: #666;
            font-size: 1.2rem;
        }
        .info {
            text-align: center;
            margin-top: 2rem;
            padding: 1rem;
            color: #666;
            font-size: 0.85rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Tweet/Toot Crawler</h1>
        <p class="subtitle">Enter a hashtag to crawl images from Mastodon</p>

        <form method="POST" class="search-box">
            <input type="text" name="hashtag" placeholder="#cats, #nature, #art..." value="{hashtag_value}" required>
            <button type="submit">Crawl Images</button>
        </form>

        {status_html}

        <h2 style="margin-bottom: 1rem; color: #aaa;">Crawled Images</h2>
        <div class="gallery">
            {gallery_html}
        </div>

        {empty_state}

        <div class="info">
            <p>Powered by Mastodon API | Images stored in Google Cloud Storage</p>
            <p>Parallel crawling via Cloud Functions + Pub/Sub</p>
        </div>
    </div>
</body>
</html>
"""


# ─── Helper Functions ─────────────────────────────────────────
def get_images_from_bucket():
    """List all images in the Cloud Storage bucket."""
    try:
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        blobs = list(bucket.list_blobs(prefix="images/"))
        images = []
        for blob in blobs:
            if blob.name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                images.append({
                    "name": blob.name,
                    "url": blob.public_url,
                    "hashtag": blob.name.split("/")[1] if "/" in blob.name else "unknown",
                })
        return images
    except Exception as e:
        print(f"[Frontend] Error listing images: {e}")
        return []


def fetch_mastodon_hashtag_images(hashtag, limit=20):
    """Query Mastodon API for posts with given hashtag, extract image URLs."""
    hashtag_clean = hashtag.strip().lstrip("#")
    url = f"{MASTODON_INSTANCE}/api/v1/timelines/tag/{hashtag_clean}"

    try:
        resp = requests.get(url, params={"limit": limit}, timeout=15)
        resp.raise_for_status()
        statuses = resp.json()
    except Exception as e:
        print(f"[Frontend] Mastodon API error: {e}")
        return []

    image_urls = []
    for status in statuses:
        for attachment in status.get("media_attachments", []):
            if attachment.get("type") == "image":
                img_url = attachment.get("url", "")
                if img_url:
                    image_urls.append(img_url)

    print(f"[Frontend] Found {len(image_urls)} images for #{hashtag_clean}")
    return image_urls


def publish_crawl_tasks(hashtag, image_urls):
    """Publish each image URL to Pub/Sub for parallel crawling."""
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(PROJECT_ID, PUBSUB_TOPIC)

    published = 0
    for img_url in image_urls:
        message_data = json.dumps({
            "hashtag": hashtag.strip().lstrip("#"),
            "image_url": img_url,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }).encode("utf-8")

        future = publisher.publish(topic_path, message_data)
        future.result()  # wait for publish confirmation
        published += 1

    print(f"[Frontend] Published {published} crawl tasks to Pub/Sub")
    return published


# ─── Cloud Function Entry Point ──────────────────────────────
@functions_framework.http
def handle_request(request):
    """HTTP Cloud Function entry point. Serves the web UI and handles crawl requests."""

    hashtag_value = ""
    status_html = ""
    status_class = ""

    if request.method == "POST":
        hashtag = request.form.get("hashtag", "").strip()
        hashtag_value = hashtag

        if hashtag:
            print(f"[Frontend] Crawl request for: {hashtag}")

            # Step 1: Query Mastodon for image URLs
            image_urls = fetch_mastodon_hashtag_images(hashtag)

            if image_urls:
                # Step 2: Publish URLs to Pub/Sub for parallel crawling
                count = publish_crawl_tasks(hashtag, image_urls)
                status_html = f'<div class="status success">Found {len(image_urls)} images for #{hashtag.lstrip("#")}. Published {count} crawl tasks. Images will appear below shortly (refresh in ~10 seconds).</div>'
            else:
                status_html = f'<div class="status error">No images found for #{hashtag.lstrip("#")}. Try a different hashtag.</div>'
        else:
            status_html = '<div class="status error">Please enter a hashtag.</div>'

    # Get existing images from bucket
    images = get_images_from_bucket()

    # Build gallery HTML
    if images:
        gallery_items = []
        for img in images[-50:]:  # show latest 50
            gallery_items.append(
                f'<div class="gallery-item">'
                f'<img src="{img["url"]}" alt="{img["name"]}" loading="lazy">'
                f'<span class="label">#{img["hashtag"]}</span>'
                f'</div>'
            )
        gallery_html = "\n".join(gallery_items)
        empty_state = ""
    else:
        gallery_html = ""
        empty_state = '<div class="empty-state">No images crawled yet. Enter a hashtag above to start!</div>'

    html = HTML_PAGE.format(
        hashtag_value=hashtag_value,
        status_html=status_html,
        gallery_html=gallery_html,
        empty_state=empty_state,
    )

    return html, 200, {"Content-Type": "text/html"}
