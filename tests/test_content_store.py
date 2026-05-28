import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from y_client.content_store import (
    ensure_website,
    get_recent_articles_for_feed,
    get_website,
    initialize_content_store,
    reset_content_db,
    save_article,
)


def test_content_store_initializes_separate_client_db_and_persists_feed_cache(tmp_path):
    data_base_path = tmp_path / "experiment"
    data_base_path.mkdir()

    session, engine, _base = initialize_content_store(
        data_base_path=str(data_base_path),
        experiment_name="demo",
    )

    assert session is not None
    assert engine is not None
    assert (data_base_path / "client_content.db").exists()

    reset_content_db()

    website = ensure_website(
        name="example",
        rss="https://example.org/rss",
        country="IT",
        language="en",
        leaning="center",
        category="general",
        last_fetched=20260327,
    )
    assert website is not None
    assert get_website(name="example", rss="https://example.org/rss") is not None

    article = save_article(
        website_name="example",
        rss="https://example.org/rss",
        title="Title",
        summary="Summary text",
        published=20260327,
        link="https://example.org/article",
        image_url="https://example.org/image.jpg",
    )
    assert article is not None

    recent = get_recent_articles_for_feed("example", "https://example.org/rss", limit=5)
    assert len(recent) == 1
    assert recent[0].link == "https://example.org/article"
