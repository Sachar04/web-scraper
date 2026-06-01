#!/bin/bash
# ══════════════════════════════════════════════════════════════════
# DEPLOY SCRIPT — Run this ENTIRELY in Google Cloud Shell
# Sets up 5 GCP resources for the web scraper pipeline:
#   1. Cloud Storage (GCS bucket)
#   2. Pub/Sub topic
#   3. Cloud Function (serverless scraper)
#   4. Cloud Scheduler (cron trigger)
#   5. Cloud Logging (automatic)
# ══════════════════════════════════════════════════════════════════

set -e

# ─── CONFIG (edit if needed) ─────────────────────────────────────
PROJECT_ID=$(gcloud config get-value project)
REGION="europe-west1"
BUCKET_NAME="${PROJECT_ID}-scraper-output"
TOPIC_NAME="scraper-trigger"
FUNCTION_NAME="mastodon-scraper"
SCHEDULER_NAME="scraper-schedule"

echo "═══════════════════════════════════════════"
echo "  Deploying Web Scraper to GCP"
echo "  Project: $PROJECT_ID"
echo "  Region:  $REGION"
echo "  Bucket:  $BUCKET_NAME"
echo "═══════════════════════════════════════════"
echo ""

# ─── 1. Enable required APIs ────────────────────────────────────
echo "[1/5] Enabling GCP APIs..."
gcloud services enable \
    cloudfunctions.googleapis.com \
    cloudscheduler.googleapis.com \
    pubsub.googleapis.com \
    storage.googleapis.com \
    cloudbuild.googleapis.com \
    logging.googleapis.com \
    --quiet

# ─── 2. Create Cloud Storage bucket ─────────────────────────────
echo "[2/5] Creating Cloud Storage bucket: $BUCKET_NAME"
gsutil mb -l $REGION gs://$BUCKET_NAME 2>/dev/null || echo "  Bucket already exists, continuing..."

# ─── 3. Create Pub/Sub topic ────────────────────────────────────
echo "[3/5] Creating Pub/Sub topic: $TOPIC_NAME"
gcloud pubsub topics create $TOPIC_NAME 2>/dev/null || echo "  Topic already exists, continuing..."

# ─── 4. Deploy Cloud Function ───────────────────────────────────
echo "[4/5] Deploying Cloud Function: $FUNCTION_NAME"
cd ~/web-scraper/cloud_function

gcloud functions deploy $FUNCTION_NAME \
    --runtime python311 \
    --trigger-topic $TOPIC_NAME \
    --entry-point scrape_mastodon \
    --region $REGION \
    --memory 256MB \
    --timeout 60s \
    --set-env-vars "MASTODON_INSTANCE=https://mastodon.social,GCS_BUCKET=$BUCKET_NAME,SCRAPE_LIMIT=1" \
    --quiet

echo "  Function deployed!"

# ─── 5. Create Cloud Scheduler job ──────────────────────────────
echo "[5/5] Creating Cloud Scheduler job: $SCHEDULER_NAME"

# Delete old job if exists
gcloud scheduler jobs delete $SCHEDULER_NAME --location=$REGION --quiet 2>/dev/null || true

gcloud scheduler jobs create pubsub $SCHEDULER_NAME \
    --location=$REGION \
    --schedule="*/10 * * * *" \
    --topic=$TOPIC_NAME \
    --message-body="scrape" \
    --description="Triggers Mastodon scraper every 10 minutes"

echo ""
echo "═══════════════════════════════════════════"
echo "  DEPLOYMENT COMPLETE!"
echo "═══════════════════════════════════════════"
echo ""
echo "  5 GCP Resources deployed:"
echo "    1. Cloud Function:  $FUNCTION_NAME"
echo "    2. Cloud Storage:   gs://$BUCKET_NAME"
echo "    3. Pub/Sub Topic:   $TOPIC_NAME"
echo "    4. Cloud Scheduler: $SCHEDULER_NAME (every 10 min)"
echo "    5. Cloud Logging:   automatic (see Logs Explorer)"
echo ""
echo "  ── Test it now ──"
echo "  gcloud pubsub topics publish $TOPIC_NAME --message='test'"
echo ""
echo "  ── Check output ──"
echo "  gsutil ls gs://$BUCKET_NAME/scrapes/"
echo "  gsutil cat gs://$BUCKET_NAME/scrapes/*.json"
echo ""
echo "  ── View logs ──"
echo "  gcloud functions logs read $FUNCTION_NAME --region=$REGION --limit=20"
echo ""
