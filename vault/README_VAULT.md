# Document vault

- `master_cv_research.md`, `master_cv_industry.md`: your real CV content. **The agent only rephrases what is
  here.** Edit these files when something changes (new project, new award). `{{EMAIL}}` and `{{PHONE}}` are
  filled from `.env`.
- `attachments/`: drop your PDFs here (git-ignored, never uploaded anywhere except the application you approve).
  Use these names so the agent recognises them:

| File name contains | Meaning |
|---|---|
| `transcript` | Official transcript |
| `moi` | Medium of Instruction letter |
| `passport` | Passport copy |
| `iqama` or `residence` | Residence permit (KSA/UAE) |
| `recommendation` or `reference` | Recommendation letters |
| `degree` or `enrollment` | Enrollment / degree certificate |
| `ielts` | IELTS result (when you have it) |
| `writing_sample` | Writing sample (the Periscope arXiv PDF is downloaded automatically by `init-db`) |
| `certificates` | One combined PDF: KASP completion, competition, Excellence Awards, MiyahThon |
| `secondary` | UAE secondary school certificate (97.03%) |
| `honors` or `class_rank` | First Class Honors / class rank letter from the registrar |

You can also send files to the Telegram bot: it saves them here.
