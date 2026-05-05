"""
API Scraper module - supports scraping from REST APIs and social platforms.
Includes generic REST API support and Twitter/X integration via Tweepy.
"""

import json
import requests
from urllib.parse import urlencode


class GenericAPIScraper:
    """Scrape data from any REST API endpoint."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "WebScraperTool/1.0",
            "Accept": "application/json",
        })

    def configure(self, base_url, headers=None, auth_token=None, auth_type="Bearer"):
        """Configure API connection."""
        self.base_url = base_url.rstrip("/")
        if headers:
            self.session.headers.update(headers)
        if auth_token:
            self.session.headers["Authorization"] = f"{auth_type} {auth_token}"

    def get(self, endpoint="", params=None):
        """Make a GET request to the API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}" if endpoint else self.base_url
        resp = self.session.get(url, params=params, timeout=15)
        resp.raise_for_status()
        return self._parse_response(resp)

    def post(self, endpoint="", data=None, json_data=None):
        """Make a POST request to the API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}" if endpoint else self.base_url
        resp = self.session.post(url, data=data, json=json_data, timeout=15)
        resp.raise_for_status()
        return self._parse_response(resp)

    def paginated_get(self, endpoint="", params=None, page_key="page",
                      max_pages=10, results_key=None):
        """Fetch paginated API results."""
        all_results = []
        params = params or {}
        page = 1

        for _ in range(max_pages):
            params[page_key] = page
            result = self.get(endpoint, params)

            if results_key and isinstance(result, dict):
                items = result.get(results_key, [])
            elif isinstance(result, list):
                items = result
            else:
                items = [result]

            if not items:
                break

            all_results.extend(items)
            page += 1

        return all_results

    def _parse_response(self, resp):
        content_type = resp.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return resp.json()
        elif "text/" in content_type:
            return {"text": resp.text, "content_type": content_type}
        else:
            return {
                "binary_size": len(resp.content),
                "content_type": content_type,
                "data": resp.content.hex()[:200] + "...",
            }


class TwitterScraper:
    """Twitter/X API scraper using Tweepy (v2 API)."""

    def __init__(self):
        self.client = None
        self.configured = False

    def configure(self, bearer_token=None, api_key=None, api_secret=None,
                  access_token=None, access_token_secret=None):
        """Configure Twitter API credentials."""
        try:
            import tweepy
        except ImportError:
            raise ImportError(
                "Tweepy is required for Twitter scraping. "
                "Install it with: pip install tweepy"
            )

        if bearer_token:
            self.client = tweepy.Client(bearer_token=bearer_token)
        elif all([api_key, api_secret, access_token, access_token_secret]):
            self.client = tweepy.Client(
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_token_secret,
            )
        else:
            raise ValueError("Provide either bearer_token or all four OAuth credentials.")

        self.configured = True

    def search_tweets(self, query, max_results=10):
        """Search recent tweets."""
        if not self.configured:
            raise RuntimeError("Twitter API not configured. Call configure() first.")

        resp = self.client.search_recent_tweets(
            query=query,
            max_results=min(max_results, 100),
            tweet_fields=["created_at", "public_metrics", "author_id", "lang"],
        )

        tweets = []
        if resp.data:
            for tweet in resp.data:
                tweets.append({
                    "id": str(tweet.id),
                    "text": tweet.text,
                    "created_at": str(tweet.created_at) if tweet.created_at else "",
                    "author_id": str(tweet.author_id) if tweet.author_id else "",
                    "metrics": dict(tweet.public_metrics) if tweet.public_metrics else {},
                })
        return tweets

    def get_user_tweets(self, username, max_results=10):
        """Get tweets from a specific user."""
        if not self.configured:
            raise RuntimeError("Twitter API not configured. Call configure() first.")

        user_resp = self.client.get_user(username=username)
        if not user_resp.data:
            return []

        user_id = user_resp.data.id
        resp = self.client.get_users_tweets(
            id=user_id,
            max_results=min(max_results, 100),
            tweet_fields=["created_at", "public_metrics"],
        )

        tweets = []
        if resp.data:
            for tweet in resp.data:
                tweets.append({
                    "id": str(tweet.id),
                    "text": tweet.text,
                    "created_at": str(tweet.created_at) if tweet.created_at else "",
                    "metrics": dict(tweet.public_metrics) if tweet.public_metrics else {},
                })
        return tweets

    def get_user_info(self, username):
        """Get user profile information."""
        if not self.configured:
            raise RuntimeError("Twitter API not configured. Call configure() first.")

        resp = self.client.get_user(
            username=username,
            user_fields=["description", "public_metrics", "created_at", "profile_image_url"],
        )

        if resp.data:
            user = resp.data
            return {
                "id": str(user.id),
                "name": user.name,
                "username": user.username,
                "description": user.description or "",
                "metrics": dict(user.public_metrics) if user.public_metrics else {},
                "created_at": str(user.created_at) if user.created_at else "",
                "profile_image": user.profile_image_url or "",
            }
        return {}


class MastodonScraper:
    """
    Mastodon public API scraper.
    No authentication required for public endpoints.

    Mastodon public API lets you scrape:
      - Public/local/federated timelines (statuses with text, media URLs, polls)
      - Hashtag timelines
      - Public account profiles and their statuses
      - Individual statuses, their context (thread), boosts, favourites
      - Instance info (name, description, stats, rules, languages)
      - Trending statuses, tags, and links
      - Custom emoji list
      - Server directory of profiles

    Media attachments (images, video, audio) are returned as URLs in status
    objects.  You can download them as binary (jpg, png, mp4, mp3, etc.)
    using the download_media() helper.
    """

    RATE_LIMIT_DELAY = 1.0  # seconds between requests to respect servers

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "WebScraperTool/1.0 (compatible; bot; +https://github.com)",
            "Accept": "application/json",
        })
        self.instance_url = None

    def configure(self, instance_url):
        """Set the Mastodon instance base URL, e.g. https://mastodon.social"""
        self.instance_url = instance_url.rstrip("/")

    def _get(self, endpoint, params=None):
        """GET a Mastodon API endpoint with basic rate-limit respect."""
        import time
        url = f"{self.instance_url}{endpoint}"
        resp = self.session.get(url, params=params, timeout=15)
        resp.raise_for_status()
        time.sleep(self.RATE_LIMIT_DELAY)
        return resp.json()

    # ── Timelines ──────────────────────────────────────────

    def get_public_timeline(self, local=False, limit=20):
        """GET /api/v1/timelines/public — public or local timeline."""
        params = {"limit": min(limit, 40), "local": str(local).lower()}
        statuses = self._get("/api/v1/timelines/public", params)
        return [self._parse_status(s) for s in statuses]

    def get_hashtag_timeline(self, hashtag, limit=20):
        """GET /api/v1/timelines/tag/:hashtag"""
        tag = hashtag.lstrip("#")
        params = {"limit": min(limit, 40)}
        statuses = self._get(f"/api/v1/timelines/tag/{tag}", params)
        return [self._parse_status(s) for s in statuses]

    # ── Accounts ───────────────────────────────────────────

    def lookup_account(self, acct):
        """GET /api/v1/accounts/lookup?acct=username"""
        data = self._get("/api/v1/accounts/lookup", {"acct": acct})
        return self._parse_account(data)

    def get_account(self, account_id):
        """GET /api/v1/accounts/:id"""
        data = self._get(f"/api/v1/accounts/{account_id}")
        return self._parse_account(data)

    def get_account_statuses(self, account_id, limit=20, only_media=False,
                              exclude_replies=False):
        """GET /api/v1/accounts/:id/statuses"""
        params = {
            "limit": min(limit, 40),
            "only_media": str(only_media).lower(),
            "exclude_replies": str(exclude_replies).lower(),
        }
        statuses = self._get(f"/api/v1/accounts/{account_id}/statuses", params)
        return [self._parse_status(s) for s in statuses]

    # ── Statuses ───────────────────────────────────────────

    def get_status(self, status_id):
        """GET /api/v1/statuses/:id"""
        data = self._get(f"/api/v1/statuses/{status_id}")
        return self._parse_status(data)

    def get_status_context(self, status_id):
        """GET /api/v1/statuses/:id/context — ancestors & descendants."""
        data = self._get(f"/api/v1/statuses/{status_id}/context")
        return {
            "ancestors": [self._parse_status(s) for s in data.get("ancestors", [])],
            "descendants": [self._parse_status(s) for s in data.get("descendants", [])],
        }

    def get_status_boosted_by(self, status_id, limit=40):
        """GET /api/v1/statuses/:id/reblogged_by"""
        accounts = self._get(f"/api/v1/statuses/{status_id}/reblogged_by",
                             {"limit": min(limit, 80)})
        return [self._parse_account(a) for a in accounts]

    def get_status_favourited_by(self, status_id, limit=40):
        """GET /api/v1/statuses/:id/favourited_by"""
        accounts = self._get(f"/api/v1/statuses/{status_id}/favourited_by",
                             {"limit": min(limit, 80)})
        return [self._parse_account(a) for a in accounts]

    # ── Instance / Trends ──────────────────────────────────

    def get_instance_info(self):
        """GET /api/v2/instance — server metadata."""
        try:
            return self._get("/api/v2/instance")
        except Exception:
            return self._get("/api/v1/instance")

    def get_trends_statuses(self, limit=20):
        """GET /api/v1/trends/statuses"""
        statuses = self._get("/api/v1/trends/statuses", {"limit": min(limit, 40)})
        return [self._parse_status(s) for s in statuses]

    def get_trends_tags(self, limit=20):
        """GET /api/v1/trends/tags"""
        return self._get("/api/v1/trends/tags", {"limit": min(limit, 40)})

    def get_trends_links(self, limit=20):
        """GET /api/v1/trends/links"""
        return self._get("/api/v1/trends/links", {"limit": min(limit, 20)})

    def get_custom_emojis(self):
        """GET /api/v1/custom_emojis"""
        return self._get("/api/v1/custom_emojis")

    def get_directory(self, limit=40, order="active"):
        """GET /api/v1/directory — profile directory."""
        return self._get("/api/v1/directory",
                         {"limit": min(limit, 80), "order": order})

    # ── Media Download ─────────────────────────────────────

    def download_media(self, media_url, output_dir="output"):
        """
        Download a binary media file (image, video, audio) from its URL.
        Returns dict with filepath, size, and content_type.
        """
        import os
        import time
        from urllib.parse import urlparse

        os.makedirs(output_dir, exist_ok=True)

        resp = self.session.get(media_url, timeout=30, stream=True)
        resp.raise_for_status()

        # Derive filename from URL
        parsed = urlparse(media_url)
        filename = os.path.basename(parsed.path) or "media_file"
        filepath = os.path.join(output_dir, filename)

        # Avoid overwriting
        base, ext = os.path.splitext(filepath)
        counter = 1
        while os.path.exists(filepath):
            filepath = f"{base}_{counter}{ext}"
            counter += 1

        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        time.sleep(self.RATE_LIMIT_DELAY)

        return {
            "filepath": filepath,
            "size_bytes": os.path.getsize(filepath),
            "content_type": resp.headers.get("Content-Type", ""),
            "source_url": media_url,
        }

    # ── Parsers ────────────────────────────────────────────

    def _parse_status(self, s):
        """Extract key fields from a Status entity."""
        media = []
        for att in s.get("media_attachments", []):
            media.append({
                "id": att.get("id", ""),
                "type": att.get("type", ""),         # image, video, gifv, audio
                "url": att.get("url", ""),            # full-size URL (downloadable)
                "preview_url": att.get("preview_url", ""),
                "description": att.get("description", ""),
            })

        poll = None
        if s.get("poll"):
            p = s["poll"]
            poll = {
                "id": p.get("id", ""),
                "expires_at": p.get("expires_at", ""),
                "options": [
                    {"title": o.get("title", ""), "votes": o.get("votes_count", 0)}
                    for o in p.get("options", [])
                ],
                "votes_count": p.get("votes_count", 0),
            }

        account = s.get("account", {})
        return {
            "id": s.get("id", ""),
            "created_at": s.get("created_at", ""),
            "content": s.get("content", ""),          # HTML text
            "text": self._strip_html(s.get("content", "")),
            "visibility": s.get("visibility", ""),
            "url": s.get("url", ""),
            "reblogs_count": s.get("reblogs_count", 0),
            "favourites_count": s.get("favourites_count", 0),
            "replies_count": s.get("replies_count", 0),
            "language": s.get("language", ""),
            "account_username": account.get("username", ""),
            "account_display_name": account.get("display_name", ""),
            "account_url": account.get("url", ""),
            "media_attachments": media,
            "poll": poll,
            "tags": [t.get("name", "") for t in s.get("tags", [])],
            "sensitive": s.get("sensitive", False),
            "spoiler_text": s.get("spoiler_text", ""),
        }

    def _parse_account(self, a):
        """Extract key fields from an Account entity."""
        return {
            "id": a.get("id", ""),
            "username": a.get("username", ""),
            "acct": a.get("acct", ""),
            "display_name": a.get("display_name", ""),
            "bio": self._strip_html(a.get("note", "")),
            "bio_html": a.get("note", ""),
            "url": a.get("url", ""),
            "avatar": a.get("avatar", ""),            # downloadable image URL
            "header": a.get("header", ""),            # downloadable image URL
            "followers_count": a.get("followers_count", 0),
            "following_count": a.get("following_count", 0),
            "statuses_count": a.get("statuses_count", 0),
            "created_at": a.get("created_at", ""),
            "bot": a.get("bot", False),
            "fields": a.get("fields", []),
        }

    @staticmethod
    def _strip_html(html_text):
        """Crude HTML tag stripper for status content."""
        import re
        text = re.sub(r"<br\s*/?>", "\n", html_text)
        text = re.sub(r"</p>\s*<p>", "\n\n", text)
        text = re.sub(r"<[^>]+>", "", text)
        text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        text = text.replace("&quot;", '"').replace("&#39;", "'")
        return text.strip()


class APIScrapeManager:
    """Manages API scraping across different platforms."""

    def __init__(self):
        self.generic = GenericAPIScraper()
        self.twitter = TwitterScraper()
        self.mastodon = MastodonScraper()

    def scrape_api(self, url, method="GET", headers=None, auth_token=None,
                   params=None, data=None):
        """Quick scrape from any API endpoint."""
        self.generic.configure(url, headers=headers, auth_token=auth_token)
        if method.upper() == "GET":
            return self.generic.get(params=params)
        elif method.upper() == "POST":
            return self.generic.post(json_data=data)
        else:
            raise ValueError(f"Unsupported method: {method}")

    def scrape_twitter(self, action, **kwargs):
        """Scrape from Twitter API."""
        if action == "search":
            return self.twitter.search_tweets(**kwargs)
        elif action == "user_tweets":
            return self.twitter.get_user_tweets(**kwargs)
        elif action == "user_info":
            return self.twitter.get_user_info(**kwargs)
        else:
            raise ValueError(f"Unknown Twitter action: {action}")

    def scrape_mastodon(self, action, **kwargs):
        """Scrape from Mastodon API."""
        actions = {
            "public_timeline": self.mastodon.get_public_timeline,
            "local_timeline": lambda **kw: self.mastodon.get_public_timeline(local=True, **kw),
            "hashtag_timeline": self.mastodon.get_hashtag_timeline,
            "lookup_account": self.mastodon.lookup_account,
            "account_statuses": self.mastodon.get_account_statuses,
            "get_status": self.mastodon.get_status,
            "status_context": self.mastodon.get_status_context,
            "instance_info": self.mastodon.get_instance_info,
            "trends_statuses": self.mastodon.get_trends_statuses,
            "trends_tags": self.mastodon.get_trends_tags,
            "trends_links": self.mastodon.get_trends_links,
            "custom_emojis": self.mastodon.get_custom_emojis,
            "directory": self.mastodon.get_directory,
            "download_media": self.mastodon.download_media,
        }
        if action not in actions:
            raise ValueError(f"Unknown Mastodon action: {action}. "
                             f"Available: {list(actions.keys())}")
        return actions[action](**kwargs)
