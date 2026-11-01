# Abdallah Mohamud Ahmed
{{EMAIL}} · {{PHONE}} · Najran, Saudi Arabia · linkedin.com/in/booje · github.com/Boojeo

**Research interests:** efficient and reliable large language models: long-context inference, LLM-based retrieval, verification in multi-agent LLM systems, and evaluation for low-resource Arabic dialects.

## Education
**B.Sc. in Computer Science**, Najran University, Saudi Arabia, Sep 2023 – expected Jun 2027 [[CONFIRM: June or July]]
- GPA **4.99 / 5.00**, First Class Honors standing; Academic Excellence Award in three consecutive years.
- Programme taught, examined and assessed entirely in English (official Medium-of-Instruction certificate from the Dean).
- Coursework: Artificial Intelligence, Linear Algebra, Calculus, Probability & Statistics, Data Structures & Algorithms, Discrete Mathematics, Software Engineering.

**KAUST Academy, AI Specialization track:** selected among the top 100 of 17,000+ applicants.
- AI Summer Program (KASP), KAUST, Jun – Aug 2026: 8-week intensive in deep learning, computer vision, NLP, Transformers, diffusion models, reinforcement learning, LLM fine-tuning and RAG (PyTorch).
- Advanced AI course (computer vision, 40 h), KAUST, Feb 2026, *with Distinction*. Introduction to AI course (40 h), University of Tabuk, Jan 2026, *with Distinction*.

## Publications and Preprints (published as Abdallah Ahmed)
1. M. Eltahir\*, A. Obayd\*, R. Rashid, A. Alghamdi, A. Mousa, **A. Ahmed**, T. Hussain, N. Khan. *Periscope: Extending Frozen Language Models Beyond Their Context Window.* Under review at ICLR. arXiv:2610.04047. Code: github.com/mohammad2012191/Periscope
2. **A. Ahmed**, M. Sabaa, A. Khanfor. *How Far Does a False Claim Travel? Error Propagation and Hand-off Checks in Multi-Agent Code Generation.* [[CONFIRM: "Under review at JOURNAL NAME" and arXiv ID]]
3. **A. Ahmed** et al. *[[CONFIRM: title]]* (annotator-free evaluation of Arabic dialect generation). Preprint, 2026.

## Research Experience
**Error Propagation in Multi-Agent Code Generation.** First author, advised by Dr. A. Khanfor, Najran University, 2026 – 2027
- Designed a controlled study of how one hallucinated claim (a fake package, a wrong function signature, a deprecated API) spreads through a planner → implementer → reviewer pipeline of LLM agents: 37,800 runs over 7 claim types, 150 tasks (HumanEval + MBPP), 3 seeds and 3 open-weight model families.
- Showed that unchecked hallucinations reach the final code in up to 67% of runs. A deterministic tool check at the hand-off cut survival of hallucinated packages from 61% to 1.6% and of wrong signatures from 67% to 12%. LLM-based supervision was much weaker at catching signature errors.
- Confirmed at larger scale: all 9 pre-registered contrasts held on ClassEval (reductions of 34–47 pp, 95% CIs), and the tool check held for all three models on 60 SWE-bench Verified repository-level instances. Models' own hallucinated packages travel ~28 pp further than injected ones, so the headline figures are conservative.
- Pre-registered hypotheses, task-clustered bootstrap CIs, GEE robustness checks, and a full reproducibility check (2,844 of 2,844 identical re-runs). Built on about 30 free GPU-hours per account with quantized open-weight models. [[CONFIRM: code/data link]]

**Periscope and CorpusProbe: Training-Free Long-Context Reading and Retrieval.** KAUST Academy, with Prof. Naeemullah Khan, 2026
- Developed CorpusProbe, a training-free, subquadratic (O(N^1.5)) LLM-based retrieval method that leads the BRIGHT benchmark with NDCG@10 of 0.526 and AUC of 0.967, ahead of BM25, embedding retrievers and full-context reading. [[CONFIRM: CorpusProbe is your part of Periscope]]
- Periscope reads only the 9k tokens of the top-ranked chunks yet matches the same model's best full-window read on LongBench v2 (32k – 1M-token windows), beats it by 5 points on InfiniteBench, and lets a 27B model read 4.5M-token contexts on one 80 GB GPU.

**OBLIQ-Bench: LLMs as Retrievers for Oblique Queries.** [[CONFIRM: institution and your role]], 2026 – present
- Studying a specific failure of text retrieval: "oblique" queries whose relevance to a document is latent and leaves little trace on the surface text.
- Building the OBLIQ-Bench benchmark, measuring baselines on BRIGHT, and profiling latency, cost and TFLOPs on KAUST's IBEX cluster and T4 GPUs. Diagnosed and fixed run failures along the way.
- Goal: a lighter, faster, cheaper retriever that keeps quality close to full-LLM retrieval. Results written up as papers, reviews and a poster. [[CONFIRM: status]]

**Lahja: Low-Resource Gulf Arabic Dialect LLM.** Graduation project, Najran University, 2026 – 2027
- Built and deployed a dialect-aware Arabic assistant for Emirati and Najdi by QLoRA fine-tuning of Jais on a single T4 / RTX 4060 budget. It reached +6.5 chrF over an MSA-copy baseline and 82% preference for dialectal forms on held-out real speech, against 55% for few-shot prompting.
- Designed a data pipeline with no paid corpora and no annotators: Whisper-vs-Cohere ASR consensus filtering of podcast speech (120K clean words kept), back-translation, reverse-instruction Q&A generation, and DPO preference pairs.
- Built a leakage-free evaluation suite: minimal-pair log-likelihood tests, a dialect classifier (AUC 0.97 vs MSA, 0.88 vs LLM-written fake dialect), meaning-preservation scoring and bootstrap CIs. Ran 18 controlled ablations and kept MCQ accuracy within 2 points of the base model.
- Released a public web demo (300 users, 2,500 queries) and submitted a preprint on annotator-free dialect evaluation.

## Leadership and Service
- **Student Council member**, Najran University, [[CONFIRM: council name and start date]].
- **Technical Committee Lead, AI Club**, Najran University, Jan 2026 – present. Lead a 15-member committee, built the club website, and delivered hands-on ML/DL workshops to 100+ students.
- **Programming Club**, Najran University: built the club's educational platform (certificates of appreciation from the club supervisor and the Dean).
- **Competitive Programming Lead, 3Cs Hackathon**, Najran University, Apr 2025. Designed the contest problems and mentored junior students.

## Honors and Competitions
- Academic Excellence Award, Najran University, three consecutive years.
- Top 10 Finalist, 6th National Programming Competition (organised by Imam Abdulrahman Bin Faisal University). [[CONFIRM: year]]
- Programming Jam 10, national programming competition, Prince Sultan University, Apr 2025 (team Code Heroes).
- MiyahThon water-innovation hackathon, Saudi Water Innovation Center: Finalist, 2nd edition, Jubail, Nov 2025 [[CONFIRM: you have proof of "finalist"; your certificate says participation]]; 3rd-edition digital bootcamp, Sep 2026.
- BIG O's competitive programming contest, King Saud University, May 2024.

## Skills
- **Programming:** Python (advanced), Java.
- **ML and LLMs:** PyTorch, TensorFlow/Keras, QLoRA/LoRA fine-tuning, DPO, RAG, LLM agents, Whisper ASR, long-context inference and retrieval evaluation (BRIGHT, LongBench v2, InfiniteBench, HumanEval, MBPP, SWE-bench).
- **Research methods:** controlled ablations, pre-registration, bootstrap confidence intervals, GEE, reproducibility checks.
- **Compute:** KAUST IBEX cluster, T4 and RTX 4060 GPUs, quantized open-weight models.
- **Languages:** English (full professional; degree taught in English), Arabic (native), Somali. [[CONFIRM: Somali level]]
