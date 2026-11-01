# Abdallah Mohamud Ahmed
AI / Machine Learning Engineer · {{EMAIL}} · {{PHONE}} · Najran, Saudi Arabia · linkedin.com/in/booje · github.com/Boojeo

## Summary
Computer Science student (GPA 4.99/5.00, First Class Honors standing, graduating Jun 2027) who builds and ships LLM systems on small budgets. I have deployed a fine-tuned Arabic-dialect assistant used by 300 people, built a 37,800-run evaluation pipeline for multi-agent code generation, and co-authored a KAUST paper on long-context LLM inference (under review at ICLR). Selected among the top 100 of 17,000+ applicants for KAUST Academy's AI program.

## Skills
- **ML and LLMs:** PyTorch, TensorFlow/Keras, QLoRA/LoRA, DPO, RAG, LLM agents, Whisper ASR, retrieval and evaluation.
- **Engineering:** Python (advanced), Java, web demo deployment, GPU-constrained training (T4, RTX 4060), HPC jobs (KAUST IBEX).
- **Data and evaluation:** data pipelines, ablation studies, statistical testing (bootstrap CIs, GEE), reproducible experiments.
- **Languages:** English (full professional), Arabic (native), Somali.

## Projects and Experience
**Lahja: Gulf Arabic Dialect LLM.** Graduation project, 2026 – 2027
- Fine-tuned Jais with QLoRA on a single T4 / RTX 4060 for Emirati and Najdi dialects: +6.5 chrF over the baseline, and 82% preference for dialectal forms against 55% for few-shot prompting.
- Built an annotator-free data pipeline (ASR consensus filtering of podcasts, 120K clean words, back-translation, DPO pairs) and a leakage-free evaluation suite (dialect classifier AUC 0.97).
- Deployed a public web demo: 300 users, 2,500 queries.

**Multi-Agent Code Generation Reliability Study.** First author, Najran University, 2026 – 2027
- Built a planner → implementer → reviewer LLM pipeline and ran 37,800 controlled runs over HumanEval, MBPP, ClassEval and SWE-bench Verified on quantized open-weight models.
- Showed that a deterministic tool check at agent hand-offs cuts hallucinated packages reaching the final code from 61% to 1.6%. Every re-run reproduced exactly (2,844 of 2,844).

**CorpusProbe and Periscope: Long-Context LLM Retrieval.** KAUST Academy, 2026
- Developed a training-free O(N^1.5) LLM-based retriever: NDCG@10 of 0.526 on BRIGHT, ahead of BM25 and embedding models. Co-author of Periscope (arXiv:2610.04047, under review at ICLR), which lets a 27B model read 4.5M-token contexts on one 80 GB GPU.

**OBLIQ-Bench: Cost-Efficient LLM Retrieval.** 2026 – present
- Benchmarking latency, cost and TFLOPs of LLM-based retrieval on the IBEX cluster and T4 GPUs, aiming for full-LLM quality at a fraction of the compute.

## Education
**B.Sc. Computer Science**, Najran University, Sep 2023 – Jun 2027 (expected). GPA 4.99/5.00, First Class Honors standing, Academic Excellence Award three years running. Taught entirely in English.

**KAUST Academy AI Specialization**, 2026: Summer Program (8 weeks, PyTorch), Advanced AI course *with Distinction*, Intro to AI course *with Distinction*.

## Leadership and Awards
- Student Council member. Technical Committee Lead, AI Club (15 members, workshops for 100+ students). Built the Programming Club's educational platform.
- Top 10 Finalist, 6th National Programming Competition. Programming Jam 10 (national, Prince Sultan University). MiyahThon hackathon finalist.
