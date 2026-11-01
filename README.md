# career-autopilot-agent

A personal agent that watches ~55 trusted scholarship, internship and job sources every day, keeps only what fits
the candidate profile, sends a Telegram digest with buttons, and on request writes a tailored CV + SOP/cover
letter + email and builds a ready-to-apply folder on your PC. It can open the application page and pre-fill the
form; **you always press the final submit yourself.**

```
sources.yaml ──> monitor (Telegram previews, RSS, JSON feeds, pages) ──> new posts only
   ──> free keyword filter ──> Claude screening + 0-100 score ──> SQLite
   ──> Telegram digest (3 categories) ──> 🚀 Tailor & Apply ──> CV/SOP/letter (fabrication-checked)
   ──> ready_to_apply/<date>_<Category>_<Org>_<Role>/ ──> optional browser autofill ──> you submit
```

## 1. Install (Windows, once)

```powershell
git clone -b claude/great-babbage-0sktyw https://github.com/Boojeo/Scholarship-Job-Agent.git
cd Scholarship-Job-Agent
python -m pip install -r requirements.txt
python -m playwright install chromium
copy .env.example .env
notepad .env
```

Fill in `.env`:

| Setting | Where to get it |
|---|---|
| `LLM_PROVIDER` | keep `claude_code`: uses your Claude Pro plan through Claude Code, no API key. Install Claude Code, run `claude` once and log in. (`gemini` still works with `GEMINI_API_KEYS`.) |
| `TELEGRAM_BOT_TOKEN` | Telegram → @BotFather → `/newbot` → copy the token |
| `CANDIDATE_PHONE` | your phone number (stays on your PC) |
| `CLAUDE_CODE_MODEL_FAST/SMART` | keep `haiku` (screening, light on your plan limits) and `sonnet` (documents) |

Then:

```powershell
python main.py init-db        # loads config/sources.yaml (and older seed list)
python main.py check-sources  # optional: shows which sources answer from your PC
```

Put your documents in `vault/attachments/` (see `vault/README_VAULT.md` for names: transcript, moi, passport…),
or send them to the bot later.

## 2. Run

```powershell
python main.py run
```

Open your bot in Telegram and send `/start` (the first person to do this becomes the only allowed user).
By default it searches every time you start it (`SEARCH_ON_START=yes`, skipped if the last search was under 6 hours ago) and whenever you send `/search_now`; there is no daily timer unless you set `DIGEST_TIME=09:00`. To start it automatically at login:
press `Win+R`, type `shell:startup`, and put a shortcut to `start_agent.bat` there.

### Telegram commands
- `/search_now` (or `/search_now scholarship|coop|fulltime`): check every source now and send the digest
- `/digest`: resend waiting opportunities · `/status`: last run, stats, vault checklist · `/vault`: documents
- Send any PDF to the bot to save it in the vault.

### Buttons on each opportunity
- **🚀 Tailor & Apply**: writes the CV + SOP/cover letter + email, checks every claim against your master CV,
  sends you the PDFs, builds the PC folder. Then **✅ Looks good – open & autofill** opens the page in a browser on
  your PC, fills name/email/phone/education/links and uploads the CV, and sends you a screenshot. You check the
  form, handle logins/CAPTCHAs, and submit. Tap **🎉 I submitted it** afterwards.
- **💻 PC Kit only**: same documents and folder, no browser.
- **✏️ Regenerate with feedback**: reply with what to change.
- **❌ Ignore**: never show it again.

## 3. Command line (without Telegram)

```powershell
python main.py monitor            # check all sources once
python main.py list               # best waiting opportunities with their ids
python main.py kit 12             # build the ready-to-apply folder for id 12 and open it
python main.py research --only A  # optional weekly web search for new sources (DuckDuckGo, free)
```

## How it decides

- **Sources:** `config/sources.yaml`, checked 2026-10-31 (Telegram channels, RSS feeds, SimplifyJobs/RemoteOK/
  Arbeitnow feeds, program pages). Add or remove lines freely, then run `init-db` again.
- **New only:** every post is remembered (`seen_items`), so the model never sees the same post twice.
- **Screening:** a free keyword filter (drops senior roles, spam), then Claude (Haiku, via Claude Code) scores batches of 20 posts against
  `config/candidate_profile.yaml`: funded, open to Somali nationals, MOI accepted / IELTS upfront, GRE, deadline
  not passed, work authorization. Only items scoring `MATCH_THRESHOLD` (default 60) reach the digest.
- **Never empty:** if a category gets fewer than 3 matches, a small free web search fills it.
- **Documents:** written only from `vault/master_cv_research.md` (scholarships) or `master_cv_industry.md`
  (jobs). Claude Sonnet writes them; a second call lists any claim not supported by your CV; the draft is regenerated once and any
  remaining flag is shown to you. Edit the master CVs whenever something changes.

## Claude plan usage

Recommended `.env`: `SCREEN_PROVIDER=gemini` (free Gemini keys do the daily screening) and
`WRITE_PROVIDER=claude_code` (Claude writes your documents). If one fails (quota, outage), the other takes over
for that call automatically. `/status` shows which is used for what.

Every model call counts toward your Claude Pro limits (they reset every few hours). The first `/search_now`
screens ~500 posts in ~25 Haiku calls; daily runs only see new posts. One tailored application is 2-4 Sonnet
calls. If a limit is hit, the bot tells you and the next run continues where it stopped.

## Limits (on purpose)

- The agent never creates accounts, pays fees, answers legal/visa declarations, sends emails, or presses submit.
- Bayt, GulfTalent, Naukrigulf, Wuzzuf, Indeed and Jadarat block automated reading; they are listed but disabled.
- Third-party channels repost other people's listings: always check the official page before applying.

## Tests

```powershell
python -m pytest
```
