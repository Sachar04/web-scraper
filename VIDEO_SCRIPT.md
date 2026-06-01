# Demo Video Recording Script

## Setup Before Recording
- Open Google Cloud Console in browser
- Open the website URL in another tab
- Have Cloud Shell ready
- Screen recorder running (OBS, Windows Game Bar `Win+G`, or similar)

---

## Video Structure (5-8 minutes recommended)

---

### Part 1: Introduction (30 seconds)

**SAY:**
> "This is my Tweet/Toot Crawler project. It's a web application deployed on Google Cloud Platform that crawls images from Mastodon based on hashtags. The architecture is fully serverless — no VMs — using 5 distinct GCP services working together."

---

### Part 2: Show the Website (1 minute)

**DO:**
1. Open the website URL
2. Type `#cats` in the input field
3. Click "Crawl Images" — images appear WITHOUT page reload
4. Type `#nature` — show that gallery clears and only new results show
5. Click "Download" on one of the images — shows it opens the full image

**SAY:**
> "Here's the web interface. Users can enter any hashtag. When I type 'cats' and click Crawl, the system queries the Mastodon API, finds images in posts tagged with that hashtag, and displays them as thumbnails. Notice there's no page reload — it uses AJAX. Each image has a download button. When I search a new tag, only the new results are shown."

---

### Part 3: Show GCP Services in Console (3-4 minutes)

#### Service 1: Cloud Functions
**DO:**
- Go to Cloud Console → Cloud Functions (make sure region is "All locations" or "europe-west1")
- Show both functions: `toot-crawler-frontend` and `toot-crawler-worker`
- Click on `toot-crawler-frontend` → show it's HTTP triggered
- Click on `toot-crawler-worker` → show it's Pub/Sub triggered

**SAY:**
> "Service 1 and 2: Cloud Functions. I have two functions. The frontend is HTTP-triggered — it serves the website and handles search requests. The crawler worker is triggered by Pub/Sub messages — it downloads images in parallel. The crawler can run up to 5 instances simultaneously, which fulfills the requirement of parallel crawling on multiple server instances."

#### Service 2: Cloud Storage
**DO:**
- Go to Cloud Console → Cloud Storage → Buckets
- Click on `[project-id]-scraper-output`
- Navigate into `images/` folder
- Show subfolders by hashtag (e.g., `images/cats/`, `images/nature/`)
- Click on an image to preview it

**SAY:**
> "Service 3: Cloud Storage. This is where all crawled images are persistently stored. They're organized by hashtag in folders. This bucket is publicly readable so the website can display the thumbnails directly. This fulfills the requirement of persistent storage."

#### Service 3: Pub/Sub
**DO:**
- Go to Cloud Console → Pub/Sub → Topics
- Show the `crawl-tasks` topic
- Click on it, show the subscription

**SAY:**
> "Service 4: Pub/Sub. This is the message queue that coordinates parallel crawling. When a user searches a hashtag, the frontend publishes one message per image URL to this topic. Each message is delivered to exactly one crawler instance — this prevents the same URL being downloaded twice, fulfilling the coordination requirement."

#### Service 4: Cloud Scheduler
**DO:**
- Go to Cloud Console → Cloud Scheduler
- Show the `crawler-schedule` job
- Show schedule: `0 */2 * * *` (every 2 hours)
- Click "Run Now" to trigger it manually

**SAY:**
> "Service 5: Cloud Scheduler. This is a managed cron job that automatically crawls the top 5 trending hashtags from Mastodon every 2 hours. It keeps the image database growing without any manual intervention."

#### Service 5: Cloud Logging
**DO:**
- Go to Cloud Console → Logging → Logs Explorer
- Filter: `resource.type="cloud_function"`
- Show log entries from both functions

**SAY:**
> "Service 6: Cloud Logging. All function executions are automatically logged. I can see exactly when crawls happen, how many images were found, and if there were any errors. This is built-in observability for the entire pipeline."

---

### Part 4: Architecture Explanation (1 minute)

**SAY:**
> "Let me explain how it all fits together:
> 1. The user visits the website, which is served by the Frontend Cloud Function.
> 2. They enter a hashtag. The frontend queries the Mastodon API and finds image URLs.
> 3. Each image URL is published as a message to Pub/Sub.
> 4. Multiple Crawler function instances pick up messages in parallel — each downloads one image and stores it in Cloud Storage.
> 5. The images are immediately available as thumbnails on the website.
> 6. Cloud Scheduler also triggers this flow automatically every 2 hours for trending topics.
> 
> This architecture is fully serverless, scales automatically, and uses 5 distinct GCP services as required."

---

### Part 5: Show Logs Proof of Parallel Execution (30 seconds)

**DO:**
- In Cloud Shell, run:
```bash
gcloud functions logs read toot-crawler-worker --region=europe-west1 --limit=20
```
- Show multiple log entries with overlapping timestamps (proves parallel execution)

**SAY:**
> "Here in the logs you can see multiple crawler instances processing different image URLs at the same time — the timestamps overlap, proving parallel execution across multiple server instances."

---

### Part 6: Conclusion (20 seconds)

**SAY:**
> "In summary: I built a fully serverless image crawler using Cloud Functions, Cloud Storage, Pub/Sub, Cloud Scheduler, and Cloud Logging — 5 GCP services, no VMs. It supports hashtag search, parallel crawling with deduplication, persistent storage, and a thumbnail website. Thank you."

---

## Quick Commands for Demo

```bash
# Show functions exist
gcloud functions list

# Show Pub/Sub topic
gcloud pubsub topics list

# Show scheduler
gcloud scheduler jobs list --location=europe-west1

# Show images in bucket
gcloud storage ls gs://$(gcloud config get-value project)-scraper-output/images/

# Show logs (parallel proof)
gcloud functions logs read toot-crawler-worker --region=europe-west1 --limit=20

# Manually trigger scheduler
gcloud scheduler jobs run crawler-schedule --location=europe-west1
```

---

## Lab Criteria Checklist (for your reference)

| Requirement | How We Meet It |
|---|---|
| Website for hashtag input | Frontend Cloud Function serves the web UI |
| Downloads pictures from Mastodon | Queries `/api/v1/timelines/tag/:hashtag`, extracts image URLs |
| Crawling on 2+ instances simultaneously | Crawler function with `max-instances=5`, Pub/Sub distributes work |
| Parallel crawling coordinated (no duplicates) | Pub/Sub delivers each message to exactly one consumer + filename=hash(URL) |
| Pictures saved persistently | Cloud Storage bucket with public access |
| Website displays thumbnails | Gallery shows Mastodon preview images + stored GCS images |
