# career-autopilot-agent

Personal agent that finds fully funded MS/PhD programs, co-op/internships and graduate jobs, scores them against
the candidate profile, and (in later phases) tailors documents and applies with a mandatory pre-submit check.

**Status: Phase 1 in progress.** Done: project skeleton, config, SQLite, provider-neutral LLM layer
(Gemini / Claude / Ollama, multi-key failover), and the **automated research bootstrap**.
Next: scrapers + matcher + Telegram digest, then document tailoring, then the browser agent.

## Setup on Windows (PowerShell)

```powershell
git clone https://github.com/Boojeo/Scholarship-Job-Agent.git
cd Scholarship-Job-Agent
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
notepad .env        # paste your Gemini key(s) into GEMINI_API_KEYS=key1,key2
```

Keys go only in `.env` (git-ignored). Never paste them into chat or commit them.

## First run: let Gemini do the research for you

```powershell
python main.py init-db            # creates the database and loads config/sources_seed.yaml
python main.py models             # lists Gemini models your key can use; copy names into .env if needed
python main.py research           # sends docs/gemini_research_prompt.md to Gemini with Google Search grounding
```

What `research` does, step by step (free route, no paid Google features):

1. For each task (scholarships, co-op, jobs, source groups) it runs the search queries in `src/research/queries.py`
   on DuckDuckGo and downloads the top pages (`--pages N`, default 24 per task).
2. Saves the downloaded text under `data/research/<timestamp>/` so a stopped run resumes without redoing work
   (`--force` to redo, `--only A,B` to run some tasks, `--dry-run` to only collect pages).
3. Gemini reads the pages in small batches and extracts structured rows. URLs come from pages that were really
   downloaded, not from the model's memory.
4. **Checks every URL over HTTP.** Dead links and live pages that do not mention the program are dropped.
5. Stores survivors in SQLite and `config/sources_discovered.yaml`. X accounts and login-only sources start disabled.

`python main.py research --grounded` uses Gemini's built-in Google Search instead. That feature returned
quota errors on a free key, so it is optional and needs a paid plan.

`python main.py probe` tests which Gemini models work with your key (old ones close to new accounts).

## Tests

```powershell
pytest
```

Tests use mocks only; no API key or network is needed.

## Rules built into the design

- Documents may be reordered, reworded and keyword-matched, but never contain invented skills, jobs, papers or grades.
- Every submit passes a pre-submit gate (field read-back, fabrication check, document check, review-page check).
- The first application always waits for the user's approval of the documents.
- Account creation, payments and legal declarations are never automated.
