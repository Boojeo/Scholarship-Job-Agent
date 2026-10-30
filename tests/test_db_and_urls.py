from src.database import db
from src.database.seed import load_seed
from src.settings import ROOT
from src.utils.urls import normalize_url, url_hash


def test_url_normalisation_dedupes():
    a = "HTTPS://Example.com/jobs/1/?utm_source=x#top"
    b = "https://example.com/jobs/1"
    assert normalize_url(a) == b
    assert url_hash(a) == url_hash(b)


def test_opportunity_dedupe():
    conn = db.connect(":memory:")
    kw = dict(category="CATEGORY_1_SCHOLARSHIP", title="MSc AI", direct_url="https://u.edu/msc")
    assert db.upsert_opportunity(conn, **kw) is True
    assert db.upsert_opportunity(conn, **{**kw, "direct_url": "https://U.edu/msc/"}) is False
    assert db.count(conn, "opportunities") == 1


def test_seed_loads_and_is_idempotent():
    conn = db.connect(":memory:")
    first = load_seed(conn, ROOT / "config" / "sources_seed.yaml")
    assert first >= 20
    assert load_seed(conn, ROOT / "config" / "sources_seed.yaml") == 0
    # login-only portals start disabled
    assert db.count(conn, "discovered_sources", "enabled = 0") >= 1
