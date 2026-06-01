"""
Auto-Demo Script — Runs the web scraper pipeline with visible output.
Use this while screen recording to show the project working live.

Usage: python demo_run.py
"""

import subprocess
import time
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))


def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")
    time.sleep(1)


def run_cmd(cmd, description):
    print(f">>> {description}")
    print(f"$ {cmd}\n")
    time.sleep(0.5)
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.returncode != 0 and result.stderr:
        print(f"[stderr] {result.stderr[:200]}")
    time.sleep(1)
    return result


def main():
    print_header("CLOUD COMPUTING WEB SCRAPER — LIVE DEMO")

    print("This demo shows the Mastodon web scraper pipeline in action.")
    print("The pipeline fetches real-time data from the Mastodon public API")
    print("and exports it to structured JSON format.\n")
    time.sleep(2)

    # ── Demo 1: Show project structure
    print_header("1. PROJECT STRUCTURE")
    run_cmd("dir /B scraper\\", "Showing scraper module files:")
    run_cmd("dir /B cloud_function\\", "Showing cloud function files:")

    # ── Demo 2: Fetch 1 trending post
    print_header("2. FETCH TRENDING MASTODON POST (limit=1)")
    run_cmd(
        'python pipeline.py --instance https://mastodon.social --action trends_statuses --limit 1 --format json',
        "Running pipeline: 1 trending status from mastodon.social"
    )

    time.sleep(1)

    # ── Demo 3: Fetch hashtag timeline
    print_header("3. FETCH HASHTAG TIMELINE (#python)")
    run_cmd(
        'python pipeline.py --instance https://mastodon.social --action hashtag_timeline --query python --limit 2 --format json',
        "Running pipeline: 2 posts tagged #python"
    )

    time.sleep(1)

    # ── Demo 4: Get instance info
    print_header("4. FETCH INSTANCE METADATA")
    run_cmd(
        'python pipeline.py --instance https://mastodon.social --action instance_info --format json',
        "Running pipeline: instance info from mastodon.social"
    )

    time.sleep(1)

    # ── Demo 5: Show output files
    print_header("5. OUTPUT FILES GENERATED")
    run_cmd("dir output\\", "Listing all exported files in output/ directory:")

    # ── Demo 6: Show content of latest file
    print_header("6. SAMPLE OUTPUT CONTENT")
    # Find latest json file
    import glob
    json_files = sorted(glob.glob("output/*.json"))
    if json_files:
        latest = json_files[-1]
        print(f"Showing content of: {latest}\n")
        with open(latest, "r", encoding="utf-8") as f:
            content = f.read()
        # Show first 1500 chars
        print(content[:1500])
        if len(content) > 1500:
            print("\n... (truncated for display)")
    else:
        print("No output files found.")

    time.sleep(1)

    # ── Summary
    print_header("DEMO COMPLETE")
    print("Pipeline demonstrated:")
    print("  - Fetched trending posts from Mastodon API")
    print("  - Fetched hashtag timeline (#python)")
    print("  - Retrieved instance metadata")
    print("  - All data exported as JSON to output/ folder")
    print("")
    print("In Google Cloud, this same logic runs as a Cloud Function")
    print("triggered by Cloud Scheduler via Pub/Sub, with output")
    print("stored in Cloud Storage and logs in Cloud Logging.")
    print("")
    print("5 GCP Resources (no VMs):")
    print("  1. Cloud Functions  — serverless compute")
    print("  2. Cloud Storage    — data persistence")
    print("  3. Pub/Sub          — event messaging")
    print("  4. Cloud Scheduler  — cron triggers")
    print("  5. Cloud Logging    — observability")
    print("")


if __name__ == "__main__":
    main()
