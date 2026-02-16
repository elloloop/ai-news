#!/usr/bin/env python3
"""Build static HTML site from .md article files using Jinja2 templates."""

import shutil
from datetime import datetime, timezone
from pathlib import Path

import frontmatter
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content" / "articles"
TEMPLATES_DIR = ROOT / "templates"
STATIC_DIR = ROOT / "static"
OUTPUT_DIR = ROOT / "_site"

SITE_URL = "https://elloloop.github.io/ai-news"
SITE_TITLE = "AI News"
SITE_DESCRIPTION = "Curated AI and machine learning news from top sources"


def load_articles():
    articles = []
    for md_file in sorted(CONTENT_DIR.glob("*.md"), reverse=True):
        try:
            post = frontmatter.load(md_file)
            article = dict(post.metadata)
            article["body"] = post.content
            articles.append(article)
        except Exception as e:
            print(f"  Skipping {md_file.name}: {e}")
    # Sort by date descending
    articles.sort(key=lambda a: a.get("date", ""), reverse=True)
    return articles


def build_site():
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    env.globals["site_url"] = SITE_URL
    env.globals["site_title"] = SITE_TITLE
    env.globals["site_description"] = SITE_DESCRIPTION
    env.globals["now"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    articles = load_articles()
    print(f"Loaded {len(articles)} articles")

    # Clean and create output dir
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

    # Copy static assets
    static_out = OUTPUT_DIR / "static"
    if STATIC_DIR.exists():
        shutil.copytree(STATIC_DIR, static_out)

    # Group articles by category
    categories = {}
    for article in articles:
        cat = article.get("category", "general")
        categories.setdefault(cat, []).append(article)

    # Build index (latest 30 articles)
    index_tmpl = env.get_template("index.html")
    index_html = index_tmpl.render(articles=articles[:30], categories=categories)
    (OUTPUT_DIR / "index.html").write_text(index_html)
    print("Built: index.html")

    # Build individual article pages
    article_tmpl = env.get_template("article.html")
    articles_out = OUTPUT_DIR / "article"
    articles_out.mkdir()
    for article in articles:
        html = article_tmpl.render(article=article)
        slug = article.get("slug", "untitled")
        (articles_out / f"{slug}.html").write_text(html)
    print(f"Built: {len(articles)} article pages")

    # Build archive page
    archive_tmpl = env.get_template("archive.html")
    # Group by month
    months = {}
    for article in articles:
        date_str = article.get("date", "")
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            month_key = dt.strftime("%B %Y")
        except Exception:
            month_key = "Unknown"
        months.setdefault(month_key, []).append(article)
    archive_html = archive_tmpl.render(months=months, total=len(articles))
    (OUTPUT_DIR / "archive.html").write_text(archive_html)
    print("Built: archive.html")

    # Generate sitemap.xml
    sitemap_entries = [{"url": SITE_URL + "/", "priority": "1.0"}]
    sitemap_entries.append({"url": SITE_URL + "/archive.html", "priority": "0.8"})
    for article in articles:
        slug = article.get("slug", "")
        sitemap_entries.append(
            {"url": f"{SITE_URL}/article/{slug}.html", "priority": "0.6"}
        )
    sitemap_xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap_xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for entry in sitemap_entries:
        sitemap_xml += f'  <url>\n    <loc>{entry["url"]}</loc>\n'
        sitemap_xml += f'    <priority>{entry["priority"]}</priority>\n  </url>\n'
    sitemap_xml += "</urlset>\n"
    (OUTPUT_DIR / "sitemap.xml").write_text(sitemap_xml)
    print("Built: sitemap.xml")

    # Generate robots.txt
    robots = f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n"
    (OUTPUT_DIR / "robots.txt").write_text(robots)
    print("Built: robots.txt")

    print(f"\nSite built to {OUTPUT_DIR}")


if __name__ == "__main__":
    build_site()
