"""
Frontend Cloud Function — Tweet/Toot Crawler Web Interface
HTTP-triggered. Serves a web page where users can:
  1. Enter a hashtag to crawl images from Mastodon
  2. View crawled images as thumbnails (only for the searched hashtag)
  3. Download images directly by clicking them

GCP Resources:
  - This function (Cloud Functions - serverless compute)
  - Pub/Sub (publishes crawl tasks for image URLs)
  - Cloud Storage (stores and serves downloaded images)
"""

import json
import os
import hashlib
import traceback
from datetime import datetime

import requests

try:
    from google.cloud import storage
except ImportError:
    storage = None

try:
    from google.cloud import pubsub_v1
except ImportError:
    pubsub_v1 = None

try:
    import functions_framework
except ImportError:
    functions_framework = None


# ─── Configuration ────────────────────────────────────────────
MASTODON_INSTANCE = os.environ.get("MASTODON_INSTANCE", "https://mastodon.social")
BUCKET_NAME = os.environ.get("GCS_BUCKET", "")
PUBSUB_TOPIC = os.environ.get("PUBSUB_TOPIC", "crawl-tasks")
PROJECT_ID = os.environ.get("GCP_PROJECT", "")


# ─── HTML Page (Single Page App with JavaScript fetch) ────────
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
        #hashtag-input {
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
        #hashtag-input:focus { border-color: #7b2ff7; }
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
        button:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .status {
            text-align: center;
            padding: 1rem;
            margin-bottom: 1.5rem;
            border-radius: 8px;
        }
        .status.success { background: rgba(0, 210, 255, 0.1); border: 1px solid rgba(0, 210, 255, 0.3); }
        .status.error { background: rgba(255, 50, 50, 0.1); border: 1px solid rgba(255, 50, 50, 0.3); }
        .status.loading { background: rgba(123, 47, 247, 0.1); border: 1px solid rgba(123, 47, 247, 0.3); }
        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
            gap: 1.2rem;
            margin-top: 1rem;
        }
        .gallery-item {
            position: relative;
            border-radius: 10px;
            overflow: hidden;
            border: 2px solid #333;
            transition: transform 0.3s, border-color 0.3s;
        }
        .gallery-item:hover { transform: scale(1.03); border-color: #7b2ff7; }
        .gallery-item img {
            width: 100%;
            height: 200px;
            object-fit: cover;
            display: block;
        }
        .gallery-item .overlay {
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            padding: 8px;
            background: linear-gradient(transparent, rgba(0,0,0,0.8));
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .gallery-item .overlay .tag {
            font-size: 0.75rem;
            color: #ccc;
        }
        .gallery-item .overlay .download-btn {
            padding: 4px 10px;
            font-size: 0.7rem;
            border-radius: 4px;
            background: rgba(0,210,255,0.8);
            color: #fff;
            text-decoration: none;
            border: none;
            cursor: pointer;
        }
        .gallery-item .overlay .download-btn:hover { background: rgba(0,210,255,1); }
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
            color: #555;
            font-size: 0.85rem;
        }
        .spinner {
            display: inline-block;
            width: 18px; height: 18px;
            border: 3px solid rgba(255,255,255,0.3);
            border-top-color: #00d2ff;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            vertical-align: middle;
            margin-right: 8px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="container">
        <h1>Tweet/Toot Crawler</h1>
        <p class="subtitle">Enter a hashtag to crawl images from Mastodon</p>

        <div class="search-box">
            <input type="text" id="hashtag-input" placeholder="#cats, #nature, #art..." autocomplete="off">
            <button id="crawl-btn" onclick="crawlImages()">Crawl Images</button>
        </div>

        <div id="status"></div>

        <h2 id="gallery-title" style="margin-bottom: 0.5rem; color: #aaa; display: none;"></h2>
        <div id="gallery" class="gallery"></div>
        <div id="empty-state" class="empty-state">Enter a hashtag above and click "Crawl Images" to start!</div>

        <div class="info">
            <p>Powered by Mastodon API | Images stored in Google Cloud Storage</p>
            <p>Parallel crawling via Cloud Functions + Pub/Sub</p>
        </div>
    </div>

    <script>
        const input = document.getElementById('hashtag-input');
        const btn = document.getElementById('crawl-btn');
        const statusEl = document.getElementById('status');
        const gallery = document.getElementById('gallery');
        const galleryTitle = document.getElementById('gallery-title');
        const emptyState = document.getElementById('empty-state');

        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') { e.preventDefault(); crawlImages(); }
        });

        async function crawlImages() {
            const hashtag = input.value.trim();
            if (!hashtag) {
                statusEl.innerHTML = '<div class="status error">Please enter a hashtag.</div>';
                return;
            }

            btn.disabled = true;
            btn.textContent = 'Crawling...';
            statusEl.innerHTML = '<div class="status loading"><span class="spinner"></span> Searching Mastodon for #' + hashtag.replace('#','') + '...</div>';
            gallery.innerHTML = '';
            galleryTitle.style.display = 'none';
            emptyState.style.display = 'none';

            try {
                const resp = await fetch('?action=crawl&hashtag=' + encodeURIComponent(hashtag));
                const data = await resp.json();

                if (data.error) {
                    statusEl.innerHTML = '<div class="status error">' + data.error + '</div>';
                    emptyState.style.display = 'block';
                    emptyState.textContent = 'No images found. Try another hashtag.';
                } else {
                    const count = data.images ? data.images.length : 0;
                    statusEl.innerHTML = '<div class="status success">Found ' + count + ' images for #' + data.hashtag + '. ' + (data.published || 0) + ' crawl tasks published to parallel workers.</div>';

                    if (data.images && data.images.length > 0) {
                        galleryTitle.textContent = 'Images for #' + data.hashtag;
                        galleryTitle.style.display = 'block';
                        data.images.forEach(function(img) {
                            const item = document.createElement('div');
                            item.className = 'gallery-item';
                            item.innerHTML = '<img src="' + img.preview + '" alt="#' + data.hashtag + '" loading="lazy">' +
                                '<div class="overlay">' +
                                '<span class="tag">#' + data.hashtag + '</span>' +
                                '<a class="download-btn" href="' + img.url + '" target="_blank" download>Download</a>' +
                                '</div>';
                            gallery.appendChild(item);
                        });
                    } else {
                        emptyState.style.display = 'block';
                        emptyState.textContent = 'No images found for this hashtag.';
                    }
                }
            } catch (err) {
                statusEl.innerHTML = '<div class="status error">Request failed: ' + err.message + '</div>';
            }

            btn.disabled = false;
            btn.textContent = 'Crawl Images';
        }
    </script>
</body>
</html>
"""


# ─── Helper Functions ─────────────────────────────────────────
def get_images_from_bucket(hashtag=None):
    """List images in the Cloud Storage bucket, optionally filtered by hashtag."""
    if not storage or not BUCKET_NAME:
        print("[Frontend] Cloud Storage not available or BUCKET_NAME not set")
        return []
    try:
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        prefix = f"images/{hashtag}/" if hashtag else "images/"
        blobs = list(bucket.list_blobs(prefix=prefix))
        images = []
        for blob in blobs:
            if blob.name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob.name}"
                images.append({
                    "name": blob.name,
                    "url": public_url,
                    "preview": public_url,
                    "hashtag": blob.name.split("/")[1] if len(blob.name.split("/")) > 1 else "unknown",
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
                preview_url = attachment.get("preview_url", img_url)
                if img_url:
                    image_urls.append({"url": img_url, "preview": preview_url})

    print(f"[Frontend] Found {len(image_urls)} images for #{hashtag_clean}")
    return image_urls


def publish_crawl_tasks(hashtag, image_urls):
    """Publish each image URL to Pub/Sub for parallel crawling."""
    if not pubsub_v1 or not PROJECT_ID:
        print("[Frontend] Pub/Sub not available or PROJECT_ID not set")
        return 0
    try:
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(PROJECT_ID, PUBSUB_TOPIC)

        published = 0
        for img in image_urls:
            message_data = json.dumps({
                "hashtag": hashtag.strip().lstrip("#"),
                "image_url": img["url"],
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }).encode("utf-8")

            future = publisher.publish(topic_path, message_data)
            future.result()
            published += 1

        print(f"[Frontend] Published {published} crawl tasks to Pub/Sub")
        return published
    except Exception as e:
        print(f"[Frontend] Pub/Sub error: {e}")
        return 0


# ─── Scheduled Crawl (trending topics) ───────────────────────
def crawl_trending_topics():
    """Fetch top 5 trending hashtags from Mastodon and crawl images for each."""
    print("[Scheduler] Fetching trending hashtags from Mastodon...")

    try:
        resp = requests.get(f"{MASTODON_INSTANCE}/api/v1/trends/tags", params={"limit": 5}, timeout=15)
        resp.raise_for_status()
        tags = resp.json()
    except Exception as e:
        print(f"[Scheduler] Error fetching trending tags: {e}")
        return {"error": str(e), "tags_crawled": 0}

    results = []
    total_published = 0
    for tag in tags[:5]:
        tag_name = tag.get("name", "")
        if not tag_name:
            continue

        print(f"[Scheduler] Crawling trending tag: #{tag_name}")
        image_urls = fetch_mastodon_hashtag_images(tag_name, limit=10)

        if image_urls:
            published = publish_crawl_tasks(tag_name, image_urls)
            total_published += published
            results.append({"tag": tag_name, "images_found": len(image_urls), "published": published})
        else:
            results.append({"tag": tag_name, "images_found": 0, "published": 0})

    print(f"[Scheduler] Done. Crawled {len(results)} trending tags, published {total_published} tasks.")
    return {"tags_crawled": len(results), "total_published": total_published, "results": results}


# ─── Cloud Function Entry Point ──────────────────────────────
def handle_request(request):
    """HTTP Cloud Function entry point."""
    try:
        # API endpoint: AJAX crawl request
        action = request.args.get("action", "")

        if action == "crawl":
            hashtag = request.args.get("hashtag", "").strip().lstrip("#")
            if not hashtag:
                return json.dumps({"error": "Please enter a hashtag."}), 200, {"Content-Type": "application/json"}

            print(f"[Frontend] Crawl request for: #{hashtag}")

            # Query Mastodon for image URLs
            image_urls = fetch_mastodon_hashtag_images(hashtag)

            if not image_urls:
                return json.dumps({"error": f"No images found for #{hashtag}. Try a different hashtag.", "hashtag": hashtag}), 200, {"Content-Type": "application/json"}

            # Publish to Pub/Sub for parallel crawling
            published = publish_crawl_tasks(hashtag, image_urls)

            # Return image URLs immediately (previews from Mastodon)
            response = {
                "hashtag": hashtag,
                "images": image_urls[:50],
                "published": published,
                "total_found": len(image_urls),
            }
            return json.dumps(response), 200, {"Content-Type": "application/json"}

        # Scheduled crawl: triggered by Cloud Scheduler every 2 hours
        if action == "scheduled":
            result = crawl_trending_topics()
            return json.dumps(result), 200, {"Content-Type": "application/json"}

        # Default: serve the HTML page
        return HTML_PAGE, 200, {"Content-Type": "text/html"}

    except Exception as e:
        error_msg = traceback.format_exc()
        print(f"[Frontend] ERROR: {error_msg}")
        return json.dumps({"error": f"Server error: {str(e)}"}), 500, {"Content-Type": "application/json"}
