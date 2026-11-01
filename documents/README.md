# Application documents: Abdallah Mohamud Ahmed

All files are Markdown, so you can edit them in VS Code. To get PDF and Word versions with your email and
phone filled in from `.env`, run:

```powershell
python main.py render-docs
```

The output goes to `documents/_output/` (not uploaded to GitHub).

| Folder | What | When to use |
|---|---|---|
| `1_resumes/CV_Masters_PhD.md` | 2-page academic CV | Master's, PhD and scholarship applications |
| `1_resumes/Resume_Job.md` | 1-page industry resume | Full-time AI/ML/software jobs |
| `1_resumes/Resume_Coop.md` | 1-page student resume | Co-op, internships, training programs |
| `2_statements/SOP_Masters.md` | Statement of Purpose | Master's applications (tailor the "Why this programme" paragraph each time) |
| `2_statements/Research_Statement_PhD.md` | Research statement | PhD / direct PhD / research-heavy MS (MBZUAI, KAUST) |
| `2_statements/Cover_Letter_Job.md` | Cover letter | Jobs |
| `2_statements/Cover_Letter_Coop.md` | Cover letter | Co-op / internships |
| `3_recommendations/` | 3 different letter drafts, brag sheet, request email, how-to | Give to recommenders |
| `4_other/Cold_Email_To_Professor.md` | Email to professors | 1–3 months before deadlines |
| `4_other/Answer_Bank.md` | Ready answers to common form questions | Portals |
| `4_other/Personal_History_Statement.md` | Optional background statement | US/Canada programmes that ask for it |
| `4_other/Short_Bio_and_LinkedIn.md` | Bio and LinkedIn text, plus fixes | Profiles and forms |
| `4_other/Document_Checklist.md` | Which certificates to attach, what to request | Before your first application |

**What an SOP is:** a 1–2 page essay explaining *what you want to study, why, what you have already done that
proves you can, and why this specific programme*. Committees read it to decide whether you will succeed in
research. It is not a life story; personal background goes in at most one or two sentences (or in the
separate Personal History statement).

**`[[...]]` markers** are things only you (or your recommender) can fill in, or facts I need you to confirm.
Search for `[[` before sending anything.

The agent's tailoring uses the same content: `vault/master_cv_research.md` (scholarships),
`vault/master_cv_coop.md` (co-op) and `vault/master_cv_industry.md` (jobs).
