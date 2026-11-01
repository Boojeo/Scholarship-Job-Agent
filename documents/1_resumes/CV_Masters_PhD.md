# Abdallah Mohamud Ahmed
{{EMAIL}} · {{PHONE}} · Najran, Saudi Arabia · linkedin.com/in/booje · github.com/Boojeo

**Research interests:** efficient and reliable large language models: long-context inference, LLM-based retrieval, verification in multi-agent LLM systems, and evaluation for low-resource Arabic dialects.

## Education
**B.Sc. in Computer Science**, Najran University, Saudi Arabia, Dec 2022 – expected Jun 2027 (preparatory year 2022–23; Computer Science major from Sep 2023)
- GPA **4.99 / 5.00** (general grade: Excellent), First Class Honors standing. **A+ in 42 of 44 courses** (A in the other two), 119 credit hours completed. Academic Excellence Award in three consecutive years.
- Programme taught, examined and assessed entirely in English (official Medium-of-Instruction certificate from the Dean).
- Coursework: Machine Learning, Artificial Intelligence, Algorithm Design and Analysis, Theory of Computation, Data Structures, Linear Algebra, Probability and Engineering Statistics, Numerical Methods, Calculus 2–3, Discrete Mathematics, Operating Systems, Computer Graphics (all A+). Current semester: Parallel and Distributed Systems, Simulation and Modelling.

**Secondary School Certificate, Advanced Stream**, Obadah Bin Al Samet School, Abu Dhabi, UAE, 2021
- Average **97.03%**: Mathematics 99.4, Physics (calculus-based) 99.7, Chemistry 99.7, English 98.0.

**KAUST Academy, AI Specialization track:** selected among the top 100 of 17,000+ applicants.
- AI Specialization Summer Program (KASP), held at King Khalid University, Abha, 28 Jun – 20 Aug 2026: 8-week, 320-hour intensive in deep learning, computer vision, NLP, Transformers, diffusion models, reinforcement learning, LLM fine-tuning and RAG (PyTorch).
- Advanced AI course (computer vision, 40 h), KAUST, Feb 2026, *with Distinction*. Introduction to AI course (40 h), University of Tabuk, Jan 2026, *with Distinction*.

## Publications and Preprints
1. M. Eltahir\*, A. Obayd\*, R. Rashid, A. Alghamdi, A. Mousa, **A. Ahmed**, T. Hussain, N. Khan. *Periscope: Extending Frozen Language Models Beyond Their Context Window.* Under review at ICLR. arXiv:2610.04047. Code: github.com/mohammad2012191/Periscope
2. **A. Mohamud**, M. Sabaa, A. Khanfor. *How Far Does a False Claim Travel? A Controlled Study of Error Propagation and Hand-off Checks in Multi-Agent Code Generation.* Manuscript in preparation for a Springer Nature journal, 2026.
3. **A. Ahmed** et al. Preprint on annotator-free evaluation of Gulf Arabic dialect generation (submitted, 2026).

## Research Experience
**Error Propagation in Multi-Agent Code Generation.** First author, advised by Dr. Abdullah Khanfor, Najran University, 2026 – 2027
- Designed a controlled study of how one hallucinated claim (a fake package, a wrong function signature, a deprecated API) spreads through a planner → implementer → reviewer pipeline of LLM agents: 37,800 runs over 7 claim types, 150 tasks (HumanEval + MBPP), 3 seeds and 3 open-weight model families.
- Showed that unchecked hallucinations reach the final code in up to 67% of runs. A deterministic tool check at the hand-off cut survival of hallucinated packages from 61% to 1.6% and of wrong signatures from 67% to 12%. LLM-based supervision was much weaker at catching signature errors.
- Confirmed at larger scale: all 9 pre-registered contrasts held on ClassEval (reductions of 34–47 pp, 95% CIs), and the tool check held for all three models on 60 SWE-bench Verified repository-level instances. Models' own hallucinated packages travel ~28 pp further than injected ones, so the headline figures are conservative.
- Pre-registered hypotheses, task-clustered bootstrap CIs, GEE robustness checks, and a full reproducibility check (2,844 of 2,844 identical re-runs). Built on about 30 free GPU-hours per account with quantized open-weight models.

**Periscope (first developed as CorpusProbe): LLMs as Long-Context Readers and Retrievers.** KAUST Academy, with Prof. Naeemullah Khan, Jun 2026 – present
- Co-developed Periscope, a training-free, subquadratic (O(N^1.5)) method: a frozen LLM answers the same question over small local and strided spans of a long text and scores each answer by its log-odds at one token, producing an evidence map at no extra cost.
- Used as a retriever, the evidence map leads the BRIGHT benchmark with NDCG@10 of 0.526 and AUC of 0.967, ahead of BM25, embedding retrievers and full-context reading. Built OBLIQ-Bench to study "oblique" queries, whose relevance to a document is latent and barely visible in the surface text.
- Reading only the 9k tokens of the top-ranked chunks matches the same model's best full-window read on LongBench v2 (32k – 1M-token windows) and beats it by 5 points on InfiniteBench. A 27B model reads 4.5M-token contexts on one 80 GB GPU.
- Profiled latency, cost and TFLOPs on KAUST's IBEX cluster and T4 GPUs, diagnosed and fixed run failures, and contributed to the paper, reviews and poster.

**Lahja: Low-Resource Gulf Arabic Dialect LLM.** Graduation project, Najran University, 2026 – 2027
- Built and deployed a dialect-aware Arabic assistant for Emirati and Najdi by QLoRA fine-tuning of Jais on a single T4 / RTX 4060 budget. It reached +6.5 chrF over an MSA-copy baseline and 82% preference for dialectal forms on held-out real speech, against 55% for few-shot prompting.
- Designed a data pipeline with no paid corpora and no annotators: Whisper-vs-Cohere ASR consensus filtering of podcast speech (120K clean words kept), back-translation, reverse-instruction Q&A generation, and DPO preference pairs.
- Built a leakage-free evaluation suite: minimal-pair log-likelihood tests, a dialect classifier (AUC 0.97 vs MSA, 0.88 vs LLM-written fake dialect), meaning-preservation scoring and bootstrap CIs. Ran 18 controlled ablations and kept MCQ accuracy within 2 points of the base model.
- Released a public web demo (300 users, 2,500 queries) and submitted a preprint on annotator-free dialect evaluation.

## Leadership and Service
- **Member, Student Advisory Council**, College of Computer Science and Information Systems, Najran University, Oct 2026 – present.
- **Technical Committee Lead, AI Club**, Najran University, Jan 2026 – present. Lead a 15-member committee, built the club website, and delivered hands-on ML/DL workshops to 100+ students.
- **Programming Club**, Najran University: built the club's educational platform (certificates of appreciation from the club supervisor and the Dean).
- **Competitive Programming Lead, 3Cs Hackathon**, Najran University, Apr 2025. Designed the contest problems and mentored junior students.

## Honors and Competitions
- Academic Excellence Award, Najran University, three consecutive years.
- **UAE Golden Visa for outstanding students** (10-year residency, valid until 2032), awarded for a 97% final grade in UAE secondary school.
- Top 10 Finalist, 6th National Programming Competition (Imam Abdulrahman Bin Faisal University), May 2024.
- Programming Jam 10, national programming competition, Prince Sultan University, Apr 2025 (team Code Heroes).
- MiyahThon water-innovation hackathon (Saudi Water Innovation Center): advanced to the Prototyping Race (final stage) of the 3rd edition, finals Dec 2026; 2nd-edition bootcamp, Jubail, Nov 2025.
- BIG O's competitive programming contest, King Saud University, May 2024.

## Skills
- **Programming:** Python (advanced), Java.
- **ML and LLMs:** PyTorch, TensorFlow/Keras, QLoRA/LoRA fine-tuning, DPO, RAG, LLM agents, Whisper ASR, long-context inference and retrieval evaluation (BRIGHT, LongBench v2, InfiniteBench, HumanEval, MBPP, SWE-bench).
- **Research methods:** controlled ablations, pre-registration, bootstrap confidence intervals, GEE, reproducibility checks.
- **Compute:** KAUST IBEX cluster, T4 and RTX 4060 GPUs, quantized open-weight models.
- **Languages:** English (full professional; degree taught in English), Arabic (native), Somali.
