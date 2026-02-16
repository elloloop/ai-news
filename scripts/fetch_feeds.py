#!/usr/bin/env python3
"""Fetch RSS feeds and write articles as .md files with frontmatter."""

import hashlib
import os
import re
import ssl
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path

import certifi
import feedparser
import frontmatter
import yaml
from dateutil import parser as dateparser

# Fix SSL certificate verification
if hasattr(ssl, "_create_default_https_context"):
    ssl._create_default_https_context = lambda: ssl.create_default_context(
        cafile=certifi.where()
    )

# Optional: Claude API for summarization
try:
    import anthropic

    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content" / "articles"
FEEDS_FILE = ROOT / "feeds.yml"


def load_feeds():
    with open(FEEDS_FILE) as f:
        return yaml.safe_load(f)["feeds"]


def slugify(text):
    text = unescape(text)
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    return text[:80]


def article_id(url):
    return hashlib.md5(url.encode()).hexdigest()[:12]


def strip_html(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def get_existing_urls():
    urls = set()
    for md_file in CONTENT_DIR.glob("*.md"):
        try:
            post = frontmatter.load(md_file)
            if "url" in post.metadata:
                urls.add(post.metadata["url"])
        except Exception:
            continue
    return urls


def summarize_with_claude(title, description, source):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or not HAS_ANTHROPIC:
        return None
    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-5-20250514",
            max_tokens=200,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Summarize this AI news article in 1-2 concise sentences "
                        f"for a news aggregator. Be factual and specific.\n\n"
                        f"Title: {title}\nSource: {source}\n"
                        f"Description: {description[:1000]}"
                    ),
                }
            ],
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"  Claude API error: {e}", file=sys.stderr)
        return None


def truncate_description(text, max_chars=300):
    text = strip_html(text)
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars].rsplit(" ", 1)[0]
    return truncated + "..."


def fetch_feed(feed_config, existing_urls, cutoff_date):
    name = feed_config["name"]
    url = feed_config["url"]
    category = feed_config.get("category", "general")

    print(f"Fetching: {name}")
    try:
        parsed = feedparser.parse(url)
    except Exception as e:
        print(f"  Error parsing {name}: {e}", file=sys.stderr)
        return []

    if parsed.bozo and not parsed.entries:
        print(f"  Warning: feed error for {name}: {parsed.bozo_exception}", file=sys.stderr)
        return []

    articles = []
    for entry in parsed.entries:
        link = entry.get("link", "")
        if not link or link in existing_urls:
            continue

        # Parse date
        date_str = entry.get("published") or entry.get("updated")
        if date_str:
            try:
                pub_date = dateparser.parse(date_str)
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
                if pub_date < cutoff_date:
                    continue
            except Exception:
                pub_date = datetime.now(timezone.utc)
        else:
            pub_date = datetime.now(timezone.utc)

        title = strip_html(entry.get("title", "Untitled"))
        description = entry.get("summary") or entry.get("description") or ""
        description_clean = truncate_description(description)

        # Try Claude summarization, fall back to description
        summary = summarize_with_claude(title, description_clean, name)
        if not summary:
            summary = description_clean

        aid = article_id(link)
        slug = f"{pub_date.strftime('%Y-%m-%d')}-{slugify(title)}-{aid}"

        article = {
            "title": title,
            "url": link,
            "source": name,
            "category": category,
            "date": pub_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "summary": summary,
            "slug": slug,
        }
        articles.append(article)
        existing_urls.add(link)

    print(f"  Found {len(articles)} new articles")
    return articles


def write_article(article):
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    filepath = CONTENT_DIR / f"{article['slug']}.md"

    post = frontmatter.Post(
        content=article["summary"],
        title=article["title"],
        url=article["url"],
        source=article["source"],
        category=article["category"],
        date=article["date"],
        slug=article["slug"],
    )
    filepath.write_text(frontmatter.dumps(post))
    return filepath


def main():
    feeds = load_feeds()
    existing_urls = get_existing_urls()
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)

    total_new = 0
    for feed_config in feeds:
        articles = fetch_feed(feed_config, existing_urls, cutoff_date)
        for article in articles:
            path = write_article(article)
            print(f"  Wrote: {path.name}")
            total_new += 1

    print(f"\nDone. {total_new} new articles fetched.")
    return total_new


if __name__ == "__main__":
    main()
