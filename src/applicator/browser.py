"""Open the application page in a real (visible) browser, fill the obvious fields, upload the CV, and stop.

The agent never presses the final submit button: you review the filled form and submit it yourself.
Logins you make in this browser are kept in ./browser_profile, so you only sign in once per site.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from src.profile import load_profile
from src.settings import ROOT, Settings

log = logging.getLogger(__name__)
PROFILE_DIR = ROOT / "browser_profile"


def field_values(settings: Settings) -> list[tuple[re.Pattern, str]]:
    c = load_profile()["candidate"]
    pairs = [
        (r"first.?name|given.?name|fname", c.get("given_name", c["name"].split()[0])),
        (r"middle.?name", c.get("middle_name", "")),
        (r"last.?name|family.?name|surname|lname", c.get("family_name", c["name"].split()[-1])),
        (r"full.?name|^name$|your.?name", c["name"]),
        (r"e-?mail", settings.candidate_email),
        (r"phone|mobile|tel", settings.candidate_phone),
        (r"linkedin", "https://www.linkedin.com/in/booje/"),
        (r"github", "https://github.com/Boojeo"),
        (r"university|school|institution", "Najran University"),
        (r"gpa|grade", "4.99 / 5.00"),
        (r"degree|major|field.?of.?study", "B.Sc. Computer Science"),
        (r"graduation", "June 2027"),
        (r"nationality|citizenship", c["nationality"]),
        (r"city|location", "Najran, Saudi Arabia"),
        (r"country", "Saudi Arabia"),
    ]
    return [(re.compile(p, re.I), v) for p, v in pairs if v]


async def assist(settings: Settings, url: str, cv_pdf: Path | None, screenshot: Path) -> dict:
    """Returns {"filled": [...], "uploaded": bool, "screenshot": path}. Leaves the browser open."""
    from playwright.async_api import async_playwright

    values = field_values(settings)
    pw = await async_playwright().start()
    ctx = await pw.chromium.launch_persistent_context(str(PROFILE_DIR), headless=False)
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()
    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(2500)
    filled, uploaded = [], False
    for el in await page.query_selector_all("input, textarea"):
        try:
            kind = (await el.get_attribute("type") or "text").lower()
            if kind == "file":
                if cv_pdf and not uploaded:
                    await el.set_input_files(str(cv_pdf))
                    uploaded = True
                continue
            if kind not in ("text", "email", "tel", "url", "") or not await el.is_visible():
                continue
            if (await el.input_value()).strip():
                continue
            hint = " ".join(filter(None, [await el.get_attribute(a) for a in
                                          ("name", "id", "placeholder", "aria-label", "autocomplete")]))
            for pattern, value in values:
                if pattern.search(hint):
                    await el.fill(value)
                    filled.append(hint[:40])
                    break
        except Exception as exc:  # odd widgets: skip, never crash the session
            log.debug("skipped a field: %s", exc)
    await page.screenshot(path=str(screenshot), full_page=True)
    # Intentionally not closing: the user reviews and submits in this window.
    return {"filled": filled, "uploaded": uploaded, "screenshot": screenshot}
