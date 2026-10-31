"""career-autopilot-agent command line. Telegram bot and scheduler are added in later phases."""
from __future__ import annotations

import argparse
import logging
import sys

from src.database import db
from src.llm.base import LLMError
from src.llm.factory import build_llm, build_role_llm
from src.settings import Settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="career-autopilot")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-db", help="create the SQLite database")
    sub.add_parser("run", help="start the Telegram bot with the daily digest (keep this running)")
    m = sub.add_parser("monitor", help="check all sources once and store new opportunities")
    m.add_argument("--category", choices=["scholarship", "coop", "fulltime"])
    m.add_argument("--no-fallback", action="store_true", help="do not run web search when a category is thin")
    sub.add_parser("list", help="show the best opportunities waiting in the database")
    k = sub.add_parser("kit", help="tailor documents and build the PC kit for one opportunity id")
    k.add_argument("id", type=int)
    sub.add_parser("check-sources", help="test every enabled source and report how many posts each returns")
    sub.add_parser("purge-research", help="delete opportunities and sources that research added (keeps seed sources)")
    sub.add_parser("models", help="list models your Gemini key can use")
    pr = sub.add_parser("probe", help="test which Gemini models really work (plain and with web search)")
    pr.add_argument("names", nargs="*", help="model names; default: your .env models plus common candidates")
    r = sub.add_parser("research", help="run the web-grounded research bootstrap with your Gemini key")
    r.add_argument("--only", help="comma list of tasks, e.g. A,B,D1")
    r.add_argument("--force", action="store_true", help="ignore saved answers and ask again")
    r.add_argument("--grounded", action="store_true",
                   help="use Gemini's built-in Google Search instead of the free web route (needs a paid plan)")
    r.add_argument("--pages", type=int, default=24, help="max pages downloaded per task (default 24)")
    r.add_argument("--resume", action="store_true",
                   help="reuse the newest data/research/<run> folder (saved pages) instead of searching again")
    r.add_argument("--dry-run", action="store_true", help="only collect raw answers, store nothing")
    args = parser.parse_args(argv)
    # Only our own messages at INFO; third-party libraries (search engines, HTTP) stay quiet unless they warn.
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    logging.getLogger("src").setLevel(logging.DEBUG if args.verbose else logging.INFO)
    settings = Settings.from_env()

    try:
        if args.cmd == "init-db":
            from src.database.seed import load_seed
            from src.settings import ROOT

            with db.session(settings.db_path) as conn:
                added = sum(load_seed(conn, ROOT / "config" / f) for f in ("sources.yaml", "sources_seed.yaml"))
            print(f"database ready at {settings.db_path} ({added} seed sources added)")
            from src.applicator.kit import ensure_paper

            paper = ensure_paper(settings)
            print(f"writing sample: {paper}" if paper else "could not download the arXiv paper (try again later)")
        elif args.cmd == "models":
            llm = build_llm(settings, "gemini")
            print("\n".join(llm.list_models()))
        elif args.cmd == "run":
            from src.bot.telegram_bot import build_app

            logging.getLogger("telegram").setLevel(logging.INFO)  # show connection problems
            print("Connecting to Telegram... (press Ctrl+C to stop)")
            build_app(settings).run_polling()
        elif args.cmd == "monitor":
            from src.monitor.run import Monitor

            cats = {"scholarship": "CATEGORY_1_SCHOLARSHIP", "coop": "CATEGORY_2_COOP_PARTTIME",
                    "fulltime": "CATEGORY_3_FULLTIME"}
            rep = Monitor(build_role_llm(settings, "screen"), settings, fallback=not args.no_fallback).run(cats.get(args.category))
            print(rep.summary())
        elif args.cmd == "list":
            with db.session(settings.db_path) as conn:
                rows = conn.execute("SELECT id, category, match_score, title, organization, deadline FROM opportunities "
                                    "WHERE status IN ('new','sent') ORDER BY match_score DESC LIMIT 30").fetchall()
            for r in rows:
                print(f"#{r['id']:<4} {r['match_score'] or '-':>3}  {r['category'][9:21]:<12} {r['title'][:70]} "
                      f"| {r['organization'] or '-'} | {r['deadline'] or '-'}")
        elif args.cmd == "kit":
            from src.applicator.kit import build_kit, open_folder
            from src.tailor.tailor import tailor

            with db.session(settings.db_path) as conn:
                row = conn.execute("SELECT * FROM opportunities WHERE id = ?", (args.id,)).fetchone()
            if not row:
                print("no opportunity with that id (see `python main.py list`)")
                return 1
            result = tailor(build_role_llm(settings, "write"), settings, dict(row))
            folder = build_kit(settings, dict(row), result)
            print(f"kit ready: {folder}")
            if result.unsupported:
                print("fabrication check flagged:", *result.unsupported, sep="\n - ")
            open_folder(folder)
        elif args.cmd == "check-sources":
            import asyncio

            from src.monitor.readers import new_client, read_source
            from src.monitor.run import load_sources

            async def _check(sources):
                async with new_client() as client:
                    return await asyncio.gather(*(read_source(client, s) for s in sources))

            with db.session(settings.db_path) as conn:
                sources = load_sources(conn)
            for src, items in zip(sources, asyncio.run(_check(sources))):
                print(f"{'OK ' if items else 'XX '} {len(items):>3} posts  {src.type:<9} {src.name}")
        elif args.cmd == "purge-research":
            with db.session(settings.db_path) as conn:
                a = conn.execute("DELETE FROM opportunities WHERE source LIKE 'research:%'").rowcount
                b = conn.execute("DELETE FROM discovered_sources WHERE origin = 'research'").rowcount
            print(f"removed {a} opportunities and {b} sources added by research")
        elif args.cmd == "probe":
            llm = build_llm(settings, "gemini")
            names = args.names or list(dict.fromkeys([
                settings.gemini_model_fast, settings.gemini_model_smart, settings.gemini_model_research,
                "gemini-flash-latest", "gemini-flash-lite-latest", "gemini-pro-latest", "gemini-3.8-flash",
                "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.1-flash-lite",
                "gemini-2.5-flash-lite"]))
            for name in names:
                print(f"{name:34} plain: {llm.probe(name, False)}")
                print(f"{'':34} search: {llm.probe(name, True)}")
        elif args.cmd == "research":
            from src.research.bootstrap import ResearchBootstrap

            only = {k.strip().upper() for k in args.only.split(",")} if args.only else None
            run_dir = None
            if args.resume:
                runs = sorted(p for p in (settings.data_dir / "research").glob("*") if p.is_dir())
                run_dir = runs[-1] if runs else None
                print(f"resuming from {run_dir}" if run_dir else "no saved run found; starting fresh")
            boot = ResearchBootstrap(build_llm(settings, "gemini") if args.grounded else build_role_llm(settings, "screen"), settings, run_dir=run_dir,
                                     mode="grounded" if args.grounded else "web", pages_per_task=args.pages)
            stats = boot.run(only, args.force, args.dry_run)
            print(stats)
    except LLMError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
