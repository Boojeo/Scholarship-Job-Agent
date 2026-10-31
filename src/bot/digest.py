"""Pure helpers that turn database rows into Telegram messages (kept separate so they are easy to test)."""
from __future__ import annotations

import html
import json

HEADERS = {
    "CATEGORY_1_SCHOLARSHIP": "1️⃣ <b>Master's / PhD scholarships</b>",
    "CATEGORY_2_COOP_PARTTIME": "2️⃣ <b>Internships, co-op &amp; part-time</b>",
    "CATEGORY_3_FULLTIME": "3️⃣ <b>Full-time jobs</b>",
}
PER_CATEGORY = 6


def pending_for_digest(conn, threshold: int) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for cat in HEADERS:
        rows = conn.execute(
            "SELECT * FROM opportunities WHERE status = 'new' AND category = ? AND COALESCE(match_score, 0) >= ? "
            "ORDER BY match_score DESC, id DESC LIMIT ?", (cat, threshold, PER_CATEGORY)).fetchall()
        out[cat] = [dict(r) for r in rows]
    return out


def card(o: dict) -> str:
    e = html.escape
    lang = {"yes": "✅ MOI/English waiver accepted", "no": "❌ needs IELTS/TOEFL", "unknown": "❔ English test: check"}
    english = "⚠️ [Requires IELTS Upfront]" if o.get("ielts_upfront") else lang.get(o.get("moi_accepted") or "unknown")
    gre = " · ⚠️ GRE required" if o.get("gre_required") == "yes" else ""
    missing = json.loads(o.get("missing_documents") or "[]")
    miss = f"\n📎 Missing: {e(', '.join(missing))}" if missing else ""
    return (f"<b>{e(o['title'])}</b>\n🏛 {e(o.get('organization') or '-')} · 📍 {e(o.get('location') or '-')}\n"
            f"🎯 Match {o.get('match_score') or '?'} / 100 · ⏰ {e(o.get('deadline') or 'no deadline given')}\n"
            f"{english}{gre}\n💡 {e(o.get('why_it_matches') or '')}{miss}")
