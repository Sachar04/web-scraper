#!/bin/bash
# ══════════════════════════════════════════════════════════════════
# DEPLOY SCRIPT — Tweet/Toot Crawler
# Run this ENTIRELY in Google Cloud Shell
#
# Deploys the full architecture:
#   1. Cloud Storage (GCS bucket — stores downloaded images)
#   2. Pub/Sub topic (crawl-tasks — coordinates parallel crawlers)
#   3. Cloud Function: frontend (HTTP — web UI for hashtag input)
#   4. Cloud Function: crawler (Pub/Sub — downloads images in parallel)
#   5. Cloud Scheduler (periodic trigger)
#   6. Cloud Logging (automatic with all Cloud Functions)
# ══════════════════════════════════════════════════════════════════

set -e

# ─── CONFIG ──────────────────────────────────────────────────────
PROJECT_ID=$(gcloud config get-value project)
REGION="europe-west1"
BUCKET_NAME="${PROJECT_ID}-scraper-output"
TOPIC_NAME="crawl-tasks"
FRONTEND_FUNCTION="toot-crawler-frontend"
CRAWLER_FUNCTION="toot-crawler-worker"
SCHEDULER_NAME="crawler-schedule"

echo "═══════════════════════════════════════════════════"
echo "  Tweet/Toot Crawler — Full Deployment"
echo "  Project: $PROJECT_ID"
echo "  Region:  $REGION"
echo "  Bucket:  $BUCKET_NAME"
echo "═══════════════════════════════════════════════════"
echo ""

# ─── 1. Enable required APIs ────────────────────────────────────
echo "[1/6] Enabling GCP APIs..."
gcloud services enable \
    cloudfunctions.googleapis.com \
    cloudscheduler.googleapis.com \
    pubsub.googleapis.com \
    storage.googleapis.com \
    cloudbuild.googleapis.com \
    logging.googleapis.com \
    run.googleapis.com \
    eventarc.googleapis.com \
    --quiet
echo "  APIs enabled."

# ─── 2. Create Cloud Storage bucket ─────────────────────────────
echo "[2/6] Creating Cloud Storage bucket: $BUCKET_NAME"
gcloud storage buckets create gs://$BUCKET_NAME --location=$REGION 2>/dev/null || echo "  Bucket already exists."
# Make bucket publicly readable (so thumbnails can be displayed)
gcloud storage buckets add-iam-policy-binding gs://$BUCKET_NAME \
    --member=allUsers \
    --role=roles/storage.objectViewer \
    --quiet 2>/dev/null || echo "  Public access already set."
echo "  Bucket ready."

# ─── 3. Create Pub/Sub topic ────────────────────────────────────
echo "[3/6] Creating Pub/Sub topic: $TOPIC_NAME"
gcloud pubsub topics create $TOPIC_NAME 2>/dev/null || echo "  Topic already exists."
echo "  Topic ready."

# ─── 4. Deploy Crawler Cloud Function (Pub/Sub triggered) ───────
echo "[4/6] Deploying Crawler Function: $CRAWLER_FUNCTION"
cd ~/web-scraper/cloud_function/crawler

gcloud functions deploy $CRAWLER_FUNCTION \
    --no-gen2 \
    --runtime python311 \
    --trigger-topic $TOPIC_NAME \
    --entry-point download_image \
    --region $REGION \
    --memory 256MB \
    --timeout 120s \
    --max-instances 5 \
    --set-env-vars "GCS_BUCKET=$BUCKET_NAME" \
    --quiet

echo "  Crawler function deployed! (max 5 parallel instances)"

# ─── 5. Deploy Frontend Cloud Function (HTTP triggered) ─────────
echo "[5/6] Deploying Frontend Function: $FRONTEND_FUNCTION"
cd ~/web-scraper/cloud_function/frontend

gcloud functions deploy $FRONTEND_FUNCTION \
    --no-gen2 \
    --runtime python311 \
    --trigger-http \
    --allow-unauthenticated \
    --entry-point handle_request \
    --region $REGION \
    --memory 256MB \
    --timeout 60s \
    --set-env-vars "MASTODON_INSTANCE=https://mastodon.social,GCS_BUCKET=$BUCKET_NAME,PUBSUB_TOPIC=$TOPIC_NAME,GCP_PROJECT=$PROJECT_ID" \
    --quiet

# Get the function URL
FRONTEND_URL=$(gcloud functions describe $FRONTEND_FUNCTION --region=$REGION --format="value(httpsTrigger.url)")
echo "  Frontend deployed!"

# ─── 6. Create Cloud Scheduler job ──────────────────────────────
echo "[6/6] Creating Cloud Scheduler job: $SCHEDULER_NAME"
gcloud scheduler jobs delete $SCHEDULER_NAME --location=$REGION --quiet 2>/dev/null || true

gcloud scheduler jobs create http $SCHEDULER_NAME \
    --location=$REGION \
    --schedule="*/10 * * * *" \
    --uri="$FRONTEND_URL" \
    --http-method=POST \
    --headers="Content-Type=application/x-www-form-urlencoded" \
    --body="hashtag=cats" \
    --description="Auto-crawls #cats every 10 minutes" \
    --quiet 2>/dev/null || echo "  Scheduler created (or already exists)."

echo "  Scheduler ready."

echo ""
echo "═══════════════════════════════════════════════════"
echo "  DEPLOYMENT COMPLETE!"
echo "═══════════════════════════════════════════════════"
echo ""
echo "  GCP Resources deployed:"
echo "    1. Cloud Function (Frontend): $FRONTEND_FUNCTION"
echo "    2. Cloud Function (Crawler):  $CRAWLER_FUNCTION (parallel)"
echo "    3. Cloud Storage:             gs://$BUCKET_NAME"
echo "    4. Pub/Sub Topic:             $TOPIC_NAME"
echo "    5. Cloud Scheduler:           $SCHEDULER_NAME (every 10 min)"
echo "    6. Cloud Logging:             automatic (Logs Explorer)"
echo ""
echo "  ╔═══════════════════════════════════════════════╗"
echo "  ║  WEBSITE URL:                                 ║"
echo "  ║  $FRONTEND_URL"
echo "  ╚═══════════════════════════════════════════════╝"
echo ""
echo "  Open the URL above in your browser to use the crawler!"
echo ""
echo "  ── Manual test ──"
echo "  curl -X POST '$FRONTEND_URL' -d 'hashtag=cats'"
echo ""
echo "  ── Check stored images ──"
echo "  gcloud storage ls gs://$BUCKET_NAME/images/"
echo ""
echo "  ── View logs ──"
echo "  gcloud functions logs read $CRAWLER_FUNCTION --region=$REGION --limit=10"
echo "  gcloud functions logs read $FRONTEND_FUNCTION --region=$REGION --limit=10"
echo ""
