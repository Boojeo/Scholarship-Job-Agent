"""career-autopilot-agent command line. Telegram bot and scheduler are added in later phases."""
from __future__ import annotations

import argparse
import logging
import sys

from src.database import db
from src.llm.base import LLMError
from src.llm.factory import build_llm
from src.settings import Settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="career-autopilot")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-db", help="create the SQLite database")
    sub.add_parser("models", help="list models your Gemini key can use")
    pr = sub.add_parser("probe", help="test which Gemini models really work (plain and with web search)")
    pr.add_argument("names", nargs="*", help="model names; default: your .env models plus common candidates")
    r = sub.add_parser("research", help="run the web-grounded research bootstrap with your Gemini key")
    r.add_argument("--only", help="comma list of tasks, e.g. A,B,D1")
    r.add_argument("--force", action="store_true", help="ignore saved answers and ask again")
    r.add_argument("--grounded", action="store_true",
                   help="use Gemini's built-in Google Search instead of the free web route (needs a paid plan)")
    r.add_argument("--pages", type=int, default=24, help="max pages downloaded per task (default 24)")
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
                added = load_seed(conn, ROOT / "config" / "sources_seed.yaml")
            print(f"database ready at {settings.db_path} ({added} seed sources added)")
        elif args.cmd == "models":
            llm = build_llm(settings, "gemini")
            print("\n".join(llm.list_models()))
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
            boot = ResearchBootstrap(build_llm(settings, "gemini"), settings,
                                     mode="grounded" if args.grounded else "web", pages_per_task=args.pages)
            stats = boot.run(only, args.force, args.dry_run)
            print(stats)
    except LLMError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
