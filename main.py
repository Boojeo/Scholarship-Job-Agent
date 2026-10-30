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
    r = sub.add_parser("research", help="run the web-grounded research bootstrap with your Gemini key")
    r.add_argument("--only", help="comma list of tasks, e.g. A,B,D1")
    r.add_argument("--force", action="store_true", help="ignore saved answers and ask again")
    r.add_argument("--dry-run", action="store_true", help="only collect raw answers, store nothing")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(message)s")
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
        elif args.cmd == "research":
            from src.research.bootstrap import ResearchBootstrap

            only = {k.strip().upper() for k in args.only.split(",")} if args.only else None
            stats = ResearchBootstrap(build_llm(settings, "gemini"), settings).run(only, args.force, args.dry_run)
            print(stats)
    except LLMError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
