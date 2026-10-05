from __future__ import annotations

import argparse

from scraper import run_scraper


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Polite Books to Scrape pipeline")
    parser.add_argument("--inject-fake-url", action="store_true", help="Add one broken detail URL to test failure handling.")
    args = parser.parse_args()
    run_scraper(inject_fake_url=args.inject_fake_url)
