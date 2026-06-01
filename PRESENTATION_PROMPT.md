# Prompt for Copilot — Create a PowerPoint Presentation

Create a professional PowerPoint presentation (10 slides) about my Cloud Computing university project. Use my provided template. The presentation should be designed for a 20-25 minute talk. Here are all the details:

---

## Project Info
- Course: Introduction to Cloud Computing (KICC)
- Lab Exercise: Tweet/Toot Crawler (Lab Exercise 03)
- Cloud Service Provider: Google Cloud Platform (GCP)
- Student: [my name]

---

## Slide 1: Title Slide
- Title: "Tweet/Toot Crawler"
- Subtitle: "Cloud-Based Hashtag Image Crawler using Mastodon API on Google Cloud Platform"
- Course: Introduction to Cloud Computing — Lab Exercise 03
- Author: [my name]
- Date: [date]

---

## Slide 2: Management Abstract
(This is required — a brief executive summary at the beginning)

- **Objective:** Build a cloud-based web application that crawls images from Mastodon posts based on user-provided hashtags
- **Approach:** Serverless architecture on Google Cloud Platform using 5 interconnected higher-level cloud services (no Virtual Machines)
- **Key services:** Cloud Functions, Cloud Storage, Pub/Sub, Cloud Scheduler, Cloud Logging
- **Result:** Fully functional, automated image crawler with parallel processing, persistent storage, and a thumbnail display website
- **Key achievement:** Parallel crawling across multiple function instances coordinated via Pub/Sub to avoid duplicate requests

---

## Slide 3: Task Requirements & Approach
The lab exercise requirements and how they were met:

| Requirement | Implementation |
|---|---|
| Website where users enter a hashtag | Cloud Function (HTTP-triggered) serves a web form |
| Download pictures from Mastodon for that hashtag | Crawler queries GET /api/v1/timelines/tag/:hashtag, extracts image URLs |
| Crawling on 2+ server instances simultaneously | Multiple Cloud Function instances consume from Pub/Sub in parallel |
| Coordination to avoid duplicate URL requests | Pub/Sub delivers each message to exactly one consumer + filename hashing |
| Pictures saved persistently | Cloud Storage bucket stores all downloaded images |
| Website displays saved pictures as thumbnails | Frontend function serves HTML page listing images from bucket |

---

## Slide 4: Architecture Overview
(Make this a visual diagram with boxes and arrows)

```
[User] --enters hashtag--> [Website / Cloud Function A (HTTP)]
                                    |
                                    v (queries Mastodon API, extracts image URLs)
                            [Mastodon API: /api/v1/timelines/tag/:hashtag]
                                    |
                                    v (publishes each image URL as a message)
                            [Pub/Sub Topic: crawl-tasks]
                                   / \
                                  v   v  (parallel consumption)
                    [Cloud Function B]   [Cloud Function C]
                    (crawler inst. 1)    (crawler inst. 2)
                          |                     |
                          v                     v
                    [Downloads image]     [Downloads image]
                          \                   /
                           v                 v
                      [Cloud Storage Bucket]
                      (persistent image store, deduplicated)
                                    |
                                    v
                      [Website displays thumbnails]

                   [Cloud Logging] <-- automatic from all functions
                   [Cloud Scheduler] --> periodic triggers via Pub/Sub
```

---

## Slide 5: Cloud Services Used (5 interconnected, all higher-level, no VMs)

| # | GCP Service | Type | Role in Architecture |
|---|---|---|---|
| 1 | **Cloud Functions** | Serverless Compute (higher-level) | Runs crawler code in parallel instances |
| 2 | **Cloud Storage** | Object Storage | Persistently stores downloaded images |
| 3 | **Cloud Pub/Sub** | Messaging / Datastream | Coordinates parallel crawlers, prevents duplicates |
| 4 | **Cloud Scheduler** | Managed Cron | Triggers periodic crawl jobs |
| 5 | **Cloud Logging** | Observability | Captures all execution logs |

**Bonus: No Virtual Machines used** — entire solution uses only higher-level/serverless services.

All 5 services are interconnected: Scheduler publishes to Pub/Sub, which triggers Functions, which write to Storage, and all activity is captured in Logging.

---

## Slide 6: How It Works — Technical Deep Dive
(Explain the crawling process with technical terms)

1. **HTTP Trigger**: User submits hashtag via web form → Cloud Function A receives the HTTP request
2. **API Call**: Function calls Mastodon REST API endpoint: `GET /api/v1/timelines/tag/{hashtag}` — returns JSON array of Status entities
3. **Media Extraction**: Parses `media_attachments` array from each Status — extracts image URLs (JPG, PNG, WebP)
4. **Message Publishing**: Each unique image URL is published as a Pub/Sub message to the `crawl-tasks` topic
5. **Parallel Consumption**: Cloud Functions B and C are Pub/Sub-triggered — GCP automatically distributes messages across instances (fan-out pattern)
6. **Image Download**: Each function instance downloads its assigned image via HTTP GET
7. **Persistent Storage**: Image saved to Cloud Storage with filename = `SHA256(url).extension` — ensures idempotent writes (deduplication)
8. **Thumbnail Display**: Frontend function lists objects in the bucket and renders an HTML page with `<img>` thumbnails

**Key technical terms:** REST API, serverless, fan-out pattern, idempotent writes, event-driven architecture, horizontal scaling

---

## Slide 7: Parallel Crawling & Coordination
(This addresses the key requirement of parallel, coordinated crawling)

- **Parallelism**: Cloud Functions auto-scales — when multiple messages are in Pub/Sub, GCP spawns multiple function instances simultaneously
- **Coordination mechanism**: Pub/Sub uses a pull/push subscription model where each message is acknowledged by exactly one consumer
- **No duplicate requests**: Once a message (image URL) is acknowledged by one crawler instance, it is removed from the queue — the other instance never sees it
- **Additional deduplication**: Cloud Storage filename = hash(URL) — even in edge cases with redelivery, the same file is overwritten, not duplicated
- **Example**: 10 image URLs published → 2 crawler instances each process ~5 URLs in parallel → total time halved compared to sequential

---

## Slide 8: Practical Demonstration
(Screenshots or video description — what was demonstrated)

- Entered hashtag "#cats" on the website
- System queried Mastodon, found posts with images
- Two Cloud Function instances processed image URLs in parallel (visible in Cloud Logging)
- Images appeared in Cloud Storage bucket within seconds
- Thumbnail website displayed the crawled cat images
- Cloud Logging showed both crawler instances working simultaneously
- Repeated the same hashtag — no duplicate downloads (deduplication working)

---

## Slide 9: Summary & Lessons Learned

**Summary:**
- Successfully implemented a Tweet/Toot Crawler on GCP
- Uses 5 interconnected higher-level cloud services (no VMs)
- Parallel, coordinated crawling eliminates duplicate requests
- Images persistently stored and displayed as thumbnails

**Lessons Learned:**
- Serverless (Cloud Functions) removes infrastructure management overhead
- Pub/Sub is ideal for coordinating parallel workers (fan-out pattern)
- Cloud Storage is simple yet powerful for persistent binary data
- Mastodon's public API is freely accessible — ideal for learning projects
- Event-driven architecture scales naturally with workload
- Deploying via scripts (Infrastructure as Code) saves time and ensures reproducibility

---

## Slide 10: Conclusion & Outlook

**Conclusion:**
- All lab exercise requirements fulfilled
- Fully serverless, no VMs — leverages only higher-level cloud services
- Automated pipeline that runs without human intervention
- Clean separation of concerns via messaging (Pub/Sub)

**Outlook / Possible Extensions:**
- Add support for video/audio media downloads
- Implement a database (Firestore) to track crawl history and avoid re-crawling
- Add user authentication to the website
- Scale to multiple Mastodon instances (federated crawling)
- Add image classification using Cloud Vision AI
- Integrate with Twitter/X API if API access is available

**References:**
- Mastodon API Documentation: https://docs.joinmastodon.org/
- Google Cloud Functions: https://cloud.google.com/functions/docs
- Google Cloud Pub/Sub: https://cloud.google.com/pubsub/docs
- Google Cloud Storage: https://cloud.google.com/storage/docs
- Google Cloud Scheduler: https://cloud.google.com/scheduler/docs
- Project Source Code: https://github.com/Sachar04/web-scraper

---

## Design & Format Instructions
- Keep it clean, professional, and visually attractive
- Use the template's color scheme consistently
- Slide 4 (architecture) should be a proper diagram with boxes, arrows, and icons — not just text
- Use cloud service icons where possible (GCP icons)
- Bullet points should be concise, not long paragraphs
- Add slide numbers on all slides
- Total: exactly 10 slides (within the 8-12 target range)
- Designed for 20-25 minutes of presentation time
- Include references/sources on the final slide (required for grading)
- The management abstract on slide 2 is mandatory
- Summary/Lessons Learned is mandatory
- Conclusion/Outlook is mandatory
