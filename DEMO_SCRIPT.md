# Demo Recording Script — Cloud Computing Web Scraper

**Total duration: ~3-4 minutes**

---

## PART 1: Show the Project Structure (30 sec)

**What to show:** Open VS Code / your IDE with the project open.

**Narration:**
> "This is my cloud computing web scraper project. It's built in Python with a modular architecture — we have the scraper engine, API scraper module supporting Mastodon, an export system, and a Tkinter GUI. For cloud deployment, I use a headless pipeline script that runs without a GUI."

**What to click:**
1. Show the file tree (expand `scraper/` folder)
2. Briefly scroll through `pipeline.py` to show it exists
3. Show `cloud_function/main.py` briefly

---

## PART 2: Run the Local Pipeline (30 sec)

**What to show:** Open a terminal in the project folder.

**Narration:**
> "Let me first demonstrate the pipeline locally. It fetches trending posts from the Mastodon public API — no authentication required."

**What to type in terminal:**
```
python pipeline.py --instance https://mastodon.social --action trends_statuses --limit 1 --format json
```

**Then show the output:**
```
cat output\scrape_*.json
```

Or just scroll through the terminal output showing the scraped post.

---

## PART 3: Show the Google Cloud Deployment (1.5 min)

**What to show:** Switch to browser → Google Cloud Console.

**Narration:**
> "Now I'll show the same scraper deployed across 5 distinct GCP resources — no virtual machines."

### Show each resource in the GCP Console:

1. **Cloud Functions** → Navigate to Cloud Functions, show `mastodon-scraper` function
   > "Resource 1: Cloud Functions — this is the serverless compute that runs my scraper code."

2. **Cloud Storage** → Navigate to Cloud Storage, show the bucket and the `scrapes/` folder with JSON files
   > "Resource 2: Cloud Storage — the scraped data gets stored here as JSON files."

3. **Pub/Sub** → Navigate to Pub/Sub, show the `scraper-trigger` topic
   > "Resource 3: Pub/Sub — this is the event messaging system that triggers the function."

4. **Cloud Scheduler** → Navigate to Cloud Scheduler, show the `scraper-schedule` job
   > "Resource 4: Cloud Scheduler — this cron job publishes to Pub/Sub every 10 minutes."

5. **Cloud Logging** → Navigate to Logging → Logs Explorer, filter by the function name
   > "Resource 5: Cloud Logging — all pipeline output is captured here automatically."

---

## PART 4: Trigger and Show Live Execution (1 min)

**What to show:** Open Cloud Shell (click `>_` icon in GCP Console).

**Narration:**
> "Let me trigger a live scrape and show the data flowing through the pipeline."

**What to type:**
```bash
gcloud pubsub topics publish scraper-trigger --message="demo"
```

**Wait 15 seconds, then:**
```bash
gcloud functions logs read mastodon-scraper --region=europe-west1 --limit=5
```

**Then show the stored output:**
```bash
gcloud storage cat gs://tweet-troot-webscraper-g-cloud-scraper-output/scrapes/*.json | head -30
```

**Narration:**
> "As you can see, the function executed, scraped one trending Mastodon post, and stored it in Cloud Storage. The entire pipeline runs serverlessly with no VMs."

---

## PART 5: Quick Architecture Summary (30 sec)

**Narration:**
> "To summarize: Cloud Scheduler triggers every 10 minutes, publishes a message to Pub/Sub, which triggers the Cloud Function. The function scrapes the Mastodon API, stores the result in Cloud Storage, and all logs go to Cloud Logging. Five distinct resources, zero VMs, fully automated."

**End recording.**

---

## Architecture Flow:
```
Cloud Scheduler → Pub/Sub → Cloud Function → Mastodon API
                                    ↓
                              Cloud Storage (JSON output)
                                    ↓
                              Cloud Logging (automatic)
```
