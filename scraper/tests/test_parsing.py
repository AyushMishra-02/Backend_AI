from src.scraper import (
    dedupe_urls,
    extract_description,
    normalize_price,
    to_absolute_url,
)


def test_normalize_price_basic():
    assert normalize_price("£51.77") == 51.77


def test_absolute_url_from_relative():
    result = to_absolute_url(
        "../book-name/index.html",
        "https://books.toscrape.com/catalogue/page-1.html",
    )
    assert result == "https://books.toscrape.com/book-name/index.html"


def test_missing_description_returns_none():
    html = "<html><body><div class='product_page'></div></body></html>"
    assert extract_description(html) is None


def test_dedupe_urls_keeps_unique_values():
    urls = [
        "https://books.toscrape.com/catalogue/a_1/index.html",
        "https://books.toscrape.com/catalogue/a_1/index.html",
        "https://books.toscrape.com/catalogue/b_2/index.html",
    ]
    assert dedupe_urls(urls) == [
        "https://books.toscrape.com/catalogue/a_1/index.html",
        "https://books.toscrape.com/catalogue/b_2/index.html",
    ]


def test_price_rejects_missing_value():
    assert normalize_price("N/A") is None
