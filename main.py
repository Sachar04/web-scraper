"""
Web Scraper Tool - Entry Point
Run this file to launch the application.
"""

import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper.app import WebScraperApp


def main():
    app = WebScraperApp()
    app.run()


if __name__ == "__main__":
    main()
