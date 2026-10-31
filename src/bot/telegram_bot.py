"""Telegram command center: daily digest, buttons, tailoring, PC kits and browser autofill."""
from __future__ import annotations

import asyncio
import datetime as dt
import logging
from pathlib import Path
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler,
                          filters)

from src.applicator.kit import build_kit, open_folder, vault_files
from src.bot.digest import HEADERS, card, pending_for_digest
from src.database import db
from src.llm.base import LLMError
from src.llm.factory import build_role_llm
from src.monitor.run import Monitor
from src.settings import Settings
from src.tailor.tailor import tailor

log = logging.getLogger(__name__)
CAT_ARGS = {"scholarship": "CATEGORY_1_SCHOLARSHIP", "coop": "CATEGORY_2_COOP_PARTTIME",
            "fulltime": "CATEGORY_3_FULLTIME"}
VAULT_EXPECTED = ["Transcript", "MOI_Certificate", "Passport", "Residence_Permit", "Recommendation"]


class Bot:
    def __init__(self, settings: Settings):
        self.s = settings
        self.screen_llm = build_role_llm(settings, "screen")
        self.write_llm = build_role_llm(settings, "write")
        self.busy = asyncio.Lock()

    # ------------------------------------------------------------------ access control
    def owner_id(self) -> int | None:
        if self.s.telegram_owner_id:
            return self.s.telegram_owner_id
        with db.session(self.s.db_path) as conn:
            v = db.get_kv(conn, "telegram_owner_id")
        return int(v) if v else None

    async def _guard(self, update: Update) -> bool:
        owner = self.owner_id()
        uid = update.effective_user.id if update.effective_user else None
        log.info("message from user id %s (owner %s)", uid, owner)
        if owner is None and uid is not None:
            with db.session(self.s.db_path) as conn:
                db.set_kv(conn, "telegram_owner_id", str(uid))
            return True
        if uid != owner:
            if update.effective_message:
                await update.effective_message.reply_text("This is a private bot.")
            return False
        return True

    def _opp(self, opp_id: int) -> dict | None:
        with db.session(self.s.db_path) as conn:
            row = conn.execute("SELECT * FROM opportunities WHERE id = ?", (opp_id,)).fetchone()
        return dict(row) if row else None

    def _kit_path(self, opp_id: int) -> Path | None:
        with db.session(self.s.db_path) as conn:
            row = conn.execute("SELECT pc_kit_path FROM applications WHERE opportunity_id = ? ORDER BY id DESC LIMIT 1",
                               (opp_id,)).fetchone()
        return Path(row[0]) if row and row[0] and Path(row[0]).exists() else None

    def _set_status(self, opp_id: int, status: str) -> None:
        with db.session(self.s.db_path) as conn:
            conn.execute("UPDATE opportunities SET status = ? WHERE id = ?", (status, opp_id))

    # ------------------------------------------------------------------ commands
    async def start(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._guard(update):
            return
        await update.message.reply_text(
            "👋 Career Autopilot is running.\n\n"
            f"Daily digest at {self.s.digest_time} ({self.s.timezone}).\n"
            "/search_now [scholarship|coop|fulltime] – check all sources now\n"
            "/digest – send waiting opportunities\n/status – health and stats\n"
            "/vault – your documents (send a PDF here to add one)")

    async def status(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._guard(update):
            return
        with db.session(self.s.db_path) as conn:
            last = db.get_kv(conn, "last_monitor_run", "never")
            summary = db.get_kv(conn, "last_monitor_summary", "-")
            n_src = db.count(conn, "discovered_sources", "enabled = 1")
            n_new = db.count(conn, "opportunities", "status = 'new' AND COALESCE(match_score,0) >= ?",
                             (self.s.match_threshold,))
            n_applied = db.count(conn, "opportunities", "status = 'applied'")
        have = set(vault_files(self.s))
        vault = "\n".join(f"{'✅' if k in have else '❌'} {k}" for k in VAULT_EXPECTED)
        await update.message.reply_text(
            f"🩺 Last check: {last}\n{summary}\n\n📡 Enabled sources: {n_src}\n📬 Waiting for digest: {n_new}\n"
            f"✅ Marked applied: {n_applied}\n🤖 Screening: {self.screen_llm.name}\n✍️ Writing: {self.write_llm.name}\n\n🗂 Vault:\n{vault}")

    async def vault(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._guard(update):
            return
        files = vault_files(self.s)
        lines = [f"✅ {k}: {', '.join(p.name for p in v)}" for k, v in files.items()]
        lines += [f"❌ {k}" for k in VAULT_EXPECTED if k not in files]
        await update.message.reply_text("🗂 Vault (vault/attachments):\n" + "\n".join(lines) +
                                        "\n\nSend a PDF with a clear name (e.g. transcript.pdf, moi.pdf) to add it.")

    async def save_document(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._guard(update):
            return
        doc = update.message.document
        folder = self.s.vault_dir / "attachments"
        folder.mkdir(parents=True, exist_ok=True)
        name = Path(doc.file_name or f"file_{doc.file_unique_id}").name
        file = await doc.get_file()
        await file.download_to_drive(folder / name)
        await update.message.reply_text(f"📥 Saved to vault: {name}")

    async def search_now(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._guard(update):
            return
        cat = CAT_ARGS.get((ctx.args or [""])[0].lower())
        await update.message.reply_text("🔎 Checking all sources… this takes a few minutes.")
        await self.run_monitor_and_digest(ctx, update.effective_chat.id, cat)

    async def digest_cmd(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._guard(update):
            return
        await self.send_digest(ctx, update.effective_chat.id)

    # ------------------------------------------------------------------ monitor + digest
    async def run_monitor_and_digest(self, ctx, chat_id: int, category: str | None = None) -> None:
        if self.busy.locked():
            await ctx.bot.send_message(chat_id, "⏳ A search is already running.")
            return
        async with self.busy:
            try:
                rep = await asyncio.to_thread(Monitor(self.screen_llm, self.s).run, category)
                await ctx.bot.send_message(chat_id, f"✅ {rep.summary()}")
            except Exception as exc:
                log.exception("monitor failed")
                await ctx.bot.send_message(chat_id, f"⚠️ Search failed: {exc}")
                return
        await self.send_digest(ctx, chat_id)

    async def send_digest(self, ctx, chat_id: int) -> None:
        with db.session(self.s.db_path) as conn:
            groups = pending_for_digest(conn, self.s.match_threshold)
        if not any(groups.values()):
            await ctx.bot.send_message(chat_id, "📭 Nothing new above your match threshold today.")
            return
        await ctx.bot.send_message(chat_id, f"📬 <b>Daily digest – {dt.date.today()}</b>", parse_mode=ParseMode.HTML)
        for cat, items in groups.items():
            await ctx.bot.send_message(chat_id, HEADERS[cat] + ("" if items else "\n<i>nothing new today</i>"),
                                       parse_mode=ParseMode.HTML)
            for o in items:
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚀 Tailor & Apply", callback_data=f"tailor:{o['id']}"),
                     InlineKeyboardButton("💻 PC Kit only", callback_data=f"kit:{o['id']}")],
                    [InlineKeyboardButton("🔗 Open Link", url=o["direct_url"]),
                     InlineKeyboardButton("❌ Ignore", callback_data=f"ignore:{o['id']}")],
                ])
                await ctx.bot.send_message(chat_id, card(o), parse_mode=ParseMode.HTML, reply_markup=kb,
                                           disable_web_page_preview=True)
                self._set_status(o["id"], "sent")

    async def daily_job(self, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        owner = self.owner_id()
        if owner:
            await self.run_monitor_and_digest(ctx, owner)

    # ------------------------------------------------------------------ buttons
    async def on_button(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._guard(update):
            return
        q = update.callback_query
        await q.answer()
        action, _, raw_id = (q.data or "").partition(":")
        opp_id = int(raw_id) if raw_id.isdigit() else 0
        chat = q.message.chat_id
        if action == "ignore":
            self._set_status(opp_id, "ignored")
            await q.edit_message_reply_markup(None)
            await ctx.bot.send_message(chat, "🗑 Ignored.")
        elif action in ("tailor", "kit"):
            await self.make_kit(ctx, chat, opp_id, autofill=action == "tailor")
        elif action == "regen":
            ctx.user_data["regen_for"] = opp_id
            await ctx.bot.send_message(chat, "✏️ What should change? Reply with your feedback.")
        elif action == "open":
            path = self._kit_path(opp_id)
            if path:
                open_folder(path)
                await ctx.bot.send_message(chat, f"📂 Opened {path}")
        elif action == "assist":
            await self.autofill(ctx, chat, opp_id)
        elif action == "submitted":
            self._set_status(opp_id, "applied")
            with db.session(self.s.db_path) as conn:
                conn.execute("UPDATE applications SET status='submitted', submitted_at=CURRENT_TIMESTAMP "
                             "WHERE opportunity_id = ?", (opp_id,))
            await ctx.bot.send_message(chat, "🎉 Marked as applied. Good luck!")

    async def on_text(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._guard(update):
            return
        opp_id = ctx.user_data.pop("regen_for", None)
        if opp_id:
            await self.make_kit(ctx, update.effective_chat.id, opp_id, autofill=True, feedback=update.message.text)

    # ------------------------------------------------------------------ tailoring + kit
    async def make_kit(self, ctx, chat: int, opp_id: int, autofill: bool, feedback: str = "") -> None:
        opp = self._opp(opp_id)
        if not opp:
            await ctx.bot.send_message(chat, "Opportunity not found.")
            return
        await ctx.bot.send_message(chat, f"✍️ Tailoring documents for <b>{opp['title'][:80]}</b>…",
                                   parse_mode=ParseMode.HTML)
        self._set_status(opp_id, "tailoring")
        try:
            result = await asyncio.to_thread(tailor, self.write_llm, self.s, opp, feedback)
            folder = await asyncio.to_thread(build_kit, self.s, opp, result)
        except (LLMError, Exception) as exc:  # noqa: BLE001 - report every failure to the user
            log.exception("tailoring failed")
            await ctx.bot.send_message(chat, f"⚠️ Tailoring failed: {exc}")
            return
        with db.session(self.s.db_path) as conn:
            conn.execute("INSERT INTO applications(opportunity_id, status, pc_kit_path) VALUES (?, ?, ?)",
                         (opp_id, "awaiting_approval", str(folder)))
            for kind, name in (("cv", "01_Tailored_CV.pdf"), ("letter", next(folder.glob("02_*.pdf")).name)):
                conn.execute("INSERT INTO tailored_docs(opportunity_id, kind, path) VALUES (?, ?, ?)",
                             (opp_id, kind, str(folder / name)))
        for pdf in sorted(folder.glob("0[12]_*.pdf")):
            with open(pdf, "rb") as fh:
                await ctx.bot.send_document(chat, fh, filename=pdf.name)
        warn = ("\n\n⚠️ Fabrication check flagged:\n• " + "\n• ".join(result.unsupported)) if result.unsupported else \
            "\n\n✅ Fabrication check passed: every claim matches your master CV."
        missing = [line for line in (folder / "00_APPLICATION_INSTRUCTIONS.md").read_text(encoding="utf-8")
                   .split("NOT in your vault", 1)[1].split("## Steps")[0].strip().splitlines() if line.strip()]
        rows = [[InlineKeyboardButton("✏️ Regenerate with feedback", callback_data=f"regen:{opp_id}"),
                 InlineKeyboardButton("📂 Open folder on PC", callback_data=f"open:{opp_id}")]]
        if autofill:
            rows.insert(0, [InlineKeyboardButton("✅ Looks good – open & autofill", callback_data=f"assist:{opp_id}")])
        rows.append([InlineKeyboardButton("🎉 I submitted it", callback_data=f"submitted:{opp_id}")])
        await ctx.bot.send_message(
            chat, f"📁 Kit ready: {folder}{warn}\n\n📎 Missing documents:\n" + "\n".join(missing),
            reply_markup=InlineKeyboardMarkup(rows))

    async def autofill(self, ctx, chat: int, opp_id: int) -> None:
        opp, folder = self._opp(opp_id), self._kit_path(opp_id)
        if not opp or not folder:
            await ctx.bot.send_message(chat, "Make the kit first.")
            return
        from src.applicator.browser import assist

        await ctx.bot.send_message(chat, "🌐 Opening the application page on your PC…")
        try:
            shot = folder / "autofill_screenshot.png"
            res = await assist(self.s, opp["direct_url"], folder / "01_Tailored_CV.pdf", shot)
        except Exception as exc:  # noqa: BLE001
            log.exception("autofill failed")
            await ctx.bot.send_message(chat, f"⚠️ Could not open the browser: {exc}\nUse the PC kit folder instead.")
            return
        with open(shot, "rb") as fh:
            await ctx.bot.send_photo(chat, fh, caption=(
                f"Filled {len(res['filled'])} fields, CV uploaded: {'yes' if res['uploaded'] else 'no'}.\n"
                "👀 Check every field in the browser window, add anything missing (logins, CAPTCHA, extra "
                "uploads), and press the portal's submit button yourself. Then tap 🎉 I submitted it."))


def build_app(settings: Settings) -> Application:
    if not settings.telegram_token:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in .env (create a bot with @BotFather).")
    bot = Bot(settings)
    async def on_error(update: object, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        log.error("bot error: %s", ctx.error, exc_info=ctx.error)
        if isinstance(update, Update) and update.effective_chat:
            await ctx.bot.send_message(update.effective_chat.id, f"⚠️ Error: {ctx.error}")

    async def announce(application: Application) -> None:
        me = await application.bot.get_me()
        print(f"Connected to Telegram as @{me.username}. Send /start to https://t.me/{me.username}", flush=True)
        owner = bot.owner_id()
        print(f"Owner: {owner if owner else 'not set yet (the first person to send /start becomes the owner)'}",
              flush=True)

    # concurrent updates: tailoring one item (a few minutes) must not freeze the other buttons
    app = Application.builder().token(settings.telegram_token).concurrent_updates(True).post_init(announce).build()
    app.add_handler(CommandHandler("start", bot.start))
    app.add_handler(CommandHandler("status", bot.status))
    app.add_handler(CommandHandler("vault", bot.vault))
    app.add_handler(CommandHandler("my_vault", bot.vault))
    app.add_handler(CommandHandler("search_now", bot.search_now))
    app.add_handler(CommandHandler("digest", bot.digest_cmd))
    app.add_handler(CallbackQueryHandler(bot.on_button))
    app.add_handler(MessageHandler(filters.Document.ALL, bot.save_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.on_text))
    app.add_error_handler(on_error)
    hh, mm = (int(x) for x in settings.digest_time.split(":"))
    app.job_queue.run_daily(bot.daily_job, time=dt.time(hh, mm, tzinfo=ZoneInfo(settings.timezone)),
                            name="daily-digest")
    return app
