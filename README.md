# Web Scraper Tool

A modular, configurable Python web scraper with a modern glassmorphism Tkinter UI.

## Features

- **Page Overview / Constructor** — Enter any URL, fetch the page, and see a full breakdown of every element (meta tags, headings, links, images, tables, forms, paragraphs, lists, scripts, styles). Each section is collapsible and shows item counts.
- **Selective Scraping** — Check exactly which data categories you want to scrape. Optionally add a CSS selector for custom extraction.
- **API Scraping** — Generic REST API support (GET/POST with headers, auth tokens, params) plus a dedicated Twitter/X panel using Tweepy.
- **Multiple Export Formats** — Export scraped data as **JSON**, **TXT**, **HTML** (styled report), or **BIN** (binary/pickle).
- **Modern UI** — Dark glassmorphism theme with translucent cards, accent colors, smooth hover effects, and a clean layout.

## Installation

```bash
pip install -r requirements.txt
```

### Dependencies

| Package         | Purpose                        |
|-----------------|--------------------------------|
| `requests`      | HTTP requests                  |
| `beautifulsoup4`| HTML parsing                   |
| `lxml`          | Fast HTML/XML parser backend   |
| `Pillow`        | Image handling (optional)      |
| `tweepy`        | Twitter/X API (optional)       |

> **Note:** `tkinter` is included with standard Python on Windows. On Linux you may need `sudo apt install python3-tk`.

## Usage

```bash
python main.py
```

### Web Scraper Tab
1. Enter a URL in the **Target URL** field and click **Analyze Page**.
2. The left panel shows the full page structure — click any section header to expand/collapse.
3. On the right, check the data categories you want, optionally enter a CSS selector.
4. Pick an export format (JSON / TXT / HTML / BIN).
5. Click **Scrape & Export** — results appear in the Results tab, and the file is saved to the `output/` folder.

### API Scraper Tab
- **REST API**: Configure base URL, HTTP method, auth token, headers, and body. Click Fetch.
- **Twitter/X**: Enter your Bearer Token, pick an action (search / user tweets / user info), and fetch.

### Output
All exports are saved to the `output/` directory with timestamped filenames.

## Project Structure

```
web-scraper/
├── main.py                  # Entry point
├── requirements.txt         # Dependencies
├── README.md
├── output/                  # Exported files (auto-created)
└── scraper/
    ├── __init__.py
    ├── app.py               # Main Tkinter application & UI
    ├── engine.py            # Scraping engine, page analyzer, data extractor
    ├── exporters.py         # TXT, HTML, JSON, BIN export modules
    ├── api_scraper.py       # REST API & Twitter/X scraper
    └── ui_theme.py          # Glassmorphism theme & styled widget factories
```

## Twitter API Setup

To use the Twitter scraper, you need a [Twitter Developer](https://developer.twitter.com/) account and a Bearer Token. Enter it in the Twitter/X tab — credentials are never stored.
