# Research prompt for Gemini (paste everything below the line)

Use Gemini with Deep Research / web search turned on. Save the answer to a file and give it back to Claude for review.

---

## Role
You are a meticulous research analyst. Today's date is **30 October 2026**. Find *real, currently open or soon-to-open* opportunities and *reliable sources* for the candidate below. **Accuracy matters more than volume.** Every item must have a working URL you actually opened. If you cannot verify a deadline, eligibility rule or link, write `UNVERIFIED` instead of guessing. Never invent a program, deadline or URL.

## Candidate profile (no personal contact details on purpose)
- B.Sc. Computer Science, Najran University (Saudi Arabia), **expected graduation July 2027**.
- GPA **4.99 / 5.0**; Annual Academic Excellence Award three years in a row.
- Nationality: **Somali**. Resident in **Saudi Arabia**.
- Language of instruction: 100% English. Has a Medium-of-Instruction (MOI) letter. **No IELTS/TOEFL yet** (will take IELTS later). **No GRE/GMAT.**
- Research: co-author of a long-context LLM inference paper (arXiv:2610.04047, submitted to ICLR, under review), developed at KAUST. Completed the KAUST Academy AI Specializations Summer Program (June-Aug 2026).
- Skills: Python, TensorFlow/Keras, deep learning, computer vision, LLMs/retrieval, Arabic dialect NLP, competitive programming (national top-10 finalist).
- Leadership: AI Club technical committee lead (15 members).
- Wants: **(1)** fully funded MS/MSc or direct PhD / integrated MS-PhD in AI/ML/NLP/CV/Data Science/CS starting **2027** (tuition waiver + stipend). **(2)** Internships, co-op training and part-time roles in AI/CS (Saudi, UAE, GCC, remote, global). **(3)** Full-time graduate / entry-level AI/ML/Data/Software roles starting mid-2027 or later.

## Tasks

### Task A: Fully funded MS / PhD programs (target intake 2027)
Find **at least 30** programs. Include at minimum: KAUST, MBZUAI, KFUPM, HBKU, Khalifa University, and then Europe (DAAD, Erasmus Mundus, Swiss, Nordic, Dutch, Hungarian Stipendium Hungaricum), UK (Chevening, Commonwealth, others), North America, China (CSC), Japan (MEXT), Korea (GKS), Turkey (Turkiye Burslari), Malaysia, Australia, and any scholarship open to Somali nationals, African, OIC/IsDB, or developing-country applicants.
For each give: program/scholarship name, university, country, degree level, funding (tuition + stipend amount), **application open and deadline dates**, **accepts MOI instead of IELTS/TOEFL? (cite the page)**, **GRE required?**, **accepts a Bachelor's applicant who has not yet graduated (July 2027)?**, nationality restrictions (is a Somali citizen eligible?), required documents (recommendation letters count, research proposal, etc.), official URL.

### Task B: Internships / co-op / part-time (AI & CS)
Find **at least 25** real current openings or recurring programs (Saudi Arabia, UAE, GCC, remote-international). Include Saudi co-op training programs (Tamheer, Jadarat, company co-op programs), and employers such as Aramco, STC, SDAIA, NEOM, Elm, Lean, Mozn, Thiqah, G42, Core42, Careem, Noon, Google/Microsoft/Amazon student programs open to this profile. For each: role, company, location, paid/unpaid, deadline, eligibility, application URL, how the application is submitted (web form / email / login required).

### Task C: Full-time entry-level / graduate roles
Find **at least 25** graduate or entry-level AI Engineer, ML Engineer, Data Scientist, NLP/CV Engineer and Software Engineer roles or graduate programs starting from mid-2027. Same fields as Task B, plus whether visa sponsorship is offered for non-residents.

### Task D: Sources the daily agent should monitor (most important)
Return a list of **at least 80 sources**, grouped by type. Verify each was active in the **last 30 days**.
1. Scholarship / PhD aggregators and official portals (e.g. Euraxess, FindAPhD, FindAMasters, DAAD, scholarship-positions sites, university "open positions" pages, AI lab hiring pages).
2. Job boards and company career pages for Saudi/UAE/GCC (Bayt, GulfTalent, Naukrigulf, Wuzzuf, LinkedIn guest listings, Jadarat, Wellfound, HuggingFace jobs, etc.).
3. **Public Telegram channels** that post scholarships, Saudi/UAE jobs or co-op training. Give the handle and confirm that `https://t.me/s/<handle>` shows recent posts.
4. **X (Twitter) accounts** and useful search queries (English and Arabic) for PhD positions, scholarships, and Gulf hiring.
5. **YouTube channels** that regularly post funded scholarship / AI internship opportunities.
6. Newsletters, RSS feeds and public APIs.

For **every source** return these fields: `name`, `type`, `url`, `region`, `category` (scholarship / coop / fulltime), `update_frequency`, `access_method` (RSS / public API / static HTML / needs JavaScript / login required), `scraping_notes` (does robots.txt or the terms forbid automated access? is there an official API or feed instead?), `language`, `quality` (1-5), `last_checked`.

### Task E: Candidate-specific traps
List rules that would exclude or hurt this candidate and how to spot them in a posting: strict IELTS-before-application, mandatory GRE, nationality exclusions, "must be enrolled/graduated before X", age limits, minimum work experience, home-country-only funding, and scholarships that require a nomination or government endorsement. Also list the best-known scholarships that **waive IELTS with an MOI**.

## Output format
1. A short summary of what you found and any gaps.
2. Tasks A-C as **Markdown tables**.
3. Task D as **a single JSON array** in a code block (one object per source, fields above) so it can be dropped into a config file.
4. Task E as a bullet list.
5. A final section: `Items I could not verify` with reasons.

## Rules
- Open every URL; do not cite a page you did not read.
- Prefer official university/employer pages over aggregators; label aggregator links as such.
- Do not include expired opportunities. If a program reopens annually, say `expected to reopen` and give last year's dates labelled as such.
- Do not pad the list. Fewer, verified entries beat many guesses.
