from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, ValidationError, field_validator

BASE_URL = "https://books.toscrape.com"
USER_AGENT = "FlyRankInternshipA9/1.0 (https://github.com/your-handle)"
REQUEST_TIMEOUT_SECONDS = 10
REQUEST_DELAY_SECONDS = 0.5

def normalize_price(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned or cleaned.upper() == "N/A":
        return None
    match = re.search(r"[-+]?\d+(?:\.\d+)?", cleaned)
    if not match:
        return None
    return float(match.group(0))


def to_absolute_url(href: str, base_url: str) -> str:
    return str(requests.compat.urljoin(base_url, href))


def dedupe_urls(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            ordered.append(url)
    return ordered


def extract_description(html_text: str) -> str | None:
    soup = BeautifulSoup(html_text, "html.parser")
    description_block = soup.select_one("#product_description")
    if not description_block:
        return None
    sibling = description_block.find_next_sibling("p")
    if sibling is None:
        return None
    text = sibling.get_text(" ", strip=True)
    return text or None


def build_cache_path(url: str, repo_root: Path) -> Path:
    parsed = urlparse(url)
    file_name = parsed.path.strip("/") or "index"
    file_name = file_name.replace("/", "-")
    if file_name.endswith("-index.html"):
        file_name = file_name[:-len("-index.html")] + ".html"
    if not file_name.endswith(".html"):
        file_name = f"{file_name}.html"
    return repo_root / "cache" / file_name


def fetch_page(
    url: str,
    *,
    repo_root: Path,
    session: requests.Session,
    allow_cache: bool = True,
    delay_between_requests: bool = True,
    cache_hits: dict[str, int] | None = None,
) -> tuple[str, bool, int | None]:
    cache_dir = repo_root / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = build_cache_path(url, repo_root)

    if allow_cache and cache_path.exists():
        if cache_hits is not None:
            cache_hits["count"] = cache_hits.get("count", 0) + 1
        html_text = cache_path.read_text(encoding="utf-8")
        return html_text, True, cache_path.stat().st_size

    if delay_between_requests:
        time.sleep(REQUEST_DELAY_SECONDS)

    response = session.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    if response.status_code != 200:
        raise RuntimeError(f"Fetch failed for {url}: HTTP {response.status_code}")

    try:
        html_text = response.content.decode("utf-8")
    except UnicodeDecodeError:
        html_text = response.text

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(html_text, encoding="utf-8")
    return html_text, False, len(response.content)


class RawBookRecord(BaseModel):
    title: str
    product_url: str
    price_text: str
    availability_text: str
    rating_text: str
    description: str | None = None
    source_page: str
    fetched_at: str


class ValidatedBookRecord(BaseModel):
    title: str
    product_url: str
    price_text: str
    availability_text: str
    rating_text: str
    description: str | None = None
    source_page: str
    fetched_at: str
    price_gbp: float

    @field_validator("product_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("product_url must begin with https://")
        return value

    @field_validator("price_gbp")
    @classmethod
    def validate_positive_price(cls, value: float) -> float:
        if value is None or value <= 0:
            raise ValueError("price_gbp must be positive")
        return value


def discover_catalogue_pages(repo_root: Path, session: requests.Session) -> list[str]:
    first_page_url = f"{BASE_URL}/catalogue/page-1.html"
    first_page_html, _, _ = fetch_page(
        first_page_url,
        repo_root=repo_root,
        session=session,
        allow_cache=True,
        delay_between_requests=False,
    )
    first_page = BeautifulSoup(first_page_html, "html.parser")
    book_links = []

    for anchor in first_page.select("article.product_pod h3 a[href]"):
        href = anchor.get("href")
        if href:
            book_links.append(to_absolute_url(href, first_page_url))

    page_urls = [first_page_url]
    current_url = first_page_url
    while len(page_urls) < 3:
        soup = BeautifulSoup(fetch_page(current_url, repo_root=repo_root, session=session, allow_cache=True, delay_between_requests=False)[0], "html.parser")
        next_link = soup.select_one("li.next a[href]")
        if not next_link:
            break
        next_url = to_absolute_url(next_link.get("href", ""), current_url)
        if next_url in page_urls:
            break
        page_urls.append(next_url)
        current_url = next_url

    all_links: list[str] = []
    for page_url in page_urls:
        page_html, _, _ = fetch_page(page_url, repo_root=repo_root, session=session, allow_cache=True)
        page_soup = BeautifulSoup(page_html, "html.parser")
        for anchor in page_soup.select("article.product_pod h3 a[href]"):
            href = anchor.get("href")
            if href:
                all_links.append(to_absolute_url(href, page_url))

    unique_links = dedupe_urls(all_links)
    return unique_links


def extract_rating_text(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    rating_element = soup.select_one("p.star-rating")
    if not rating_element:
        return "Unknown"
    classes = rating_element.get("class", [])
    rating_name = next((item for item in classes if item != "star-rating"), "Unknown")
    mapping = {
        "One": "One",
        "Two": "Two",
        "Three": "Three",
        "Four": "Four",
        "Five": "Five",
    }
    return mapping.get(rating_name.title(), "Unknown")


def extract_detail_record(url: str, source_page: str, repo_root: Path, session: requests.Session) -> RawBookRecord:
    html_text, _, _ = fetch_page(url, repo_root=repo_root, session=session, allow_cache=True)
    soup = BeautifulSoup(html_text, "html.parser")

    title = (soup.select_one("h1") or "").get_text(strip=True)
    price_text = (soup.select_one("p.price_color") or "").get_text(strip=True)
    availability_text = (soup.select_one("p.availability") or "").get_text(" ", strip=True)
    rating_text = extract_rating_text(html_text)
    description = extract_description(html_text)

    if not title:
        raise ValueError(f"Missing title for {url}")

    if not price_text:
        raise ValueError(f"Missing price for {url}")

    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return RawBookRecord(
        title=title,
        product_url=url,
        price_text=price_text,
        availability_text=availability_text,
        rating_text=rating_text,
        description=description,
        source_page=source_page,
        fetched_at=fetched_at,
    )


def build_validated_record(raw: RawBookRecord) -> ValidatedBookRecord:
    price_gbp = normalize_price(raw.price_text)
    if price_gbp is None:
        raise ValueError(f"Could not normalize price for {raw.product_url}")

    payload = raw.model_dump()
    payload["price_gbp"] = price_gbp
    return ValidatedBookRecord.model_validate(payload)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_scraper(inject_fake_url: bool = False) -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[1]
    (repo_root / "cache").mkdir(parents=True, exist_ok=True)
    (repo_root / "output").mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    start_time = datetime.now(timezone.utc)
    cache_hits = {"count": 0}

    catalogue_urls = discover_catalogue_pages(repo_root, session)
    if inject_fake_url:
        catalogue_urls.append("https://books.toscrape.com/catalogue/fake-book-does-not-exist_99999/index.html")

    valid_records: list[dict[str, Any]] = []
    error_records: list[dict[str, Any]] = []
    seen_product_urls: set[str] = set()
    failed_pages = 0
    pages_fetched = 0

    for page_url in catalogue_urls:
        pages_fetched += 1
        try:
            raw_record = extract_detail_record(page_url, page_url, repo_root, session)
            validated = build_validated_record(raw_record)
            if validated.product_url in seen_product_urls:
                continue
            seen_product_urls.add(validated.product_url)
            valid_records.append(validated.model_dump())
        except Exception as exc:  # pragma: no cover - defensive fallback for broken pages
            failed_pages += 1
            error_records.append({"url": page_url, "reason": str(exc)})

    unique_valid_records = []
    ordered_urls: set[str] = set()
    for record in valid_records:
        if record["product_url"] not in ordered_urls:
            ordered_urls.add(record["product_url"])
            unique_valid_records.append(record)

    write_json(repo_root / "output" / "books.json", unique_valid_records)
    write_json(repo_root / "output" / "errors.json", error_records)

    end_time = datetime.now(timezone.utc)
    duration = round((end_time - start_time).total_seconds(), 2)
    report = {
        "start_time": start_time.isoformat().replace("+00:00", "Z"),
        "end_time": end_time.isoformat().replace("+00:00", "Z"),
        "duration_seconds": duration,
        "pages_fetched": pages_fetched,
        "cache_hits": cache_hits["count"],
        "valid_records": len(unique_valid_records),
        "invalid_records": len(error_records),
        "failed_pages": failed_pages,
    }
    write_json(repo_root / "output" / "run-report.json", report)
    print("catalogue_pages=3")
    print(f"discovered={len(catalogue_urls)}")
    print(f"unique_urls={len(dedupe_urls(catalogue_urls))}")
    print(f"detail_pages={pages_fetched}")
    print(f"valid_records={len(unique_valid_records)}")
    print(f"failed_pages={failed_pages}")
    return report


if __name__ == "__main__":
    run_scraper()
