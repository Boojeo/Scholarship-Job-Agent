# Research Statement
**Abdallah Mohamud Ahmed**, applicant to the [[PhD / integrated MS–PhD programme]] at [[UNIVERSITY]]

## Overview
Large language models are increasingly used as components: they retrieve documents, read long contexts, and pass work to other models. My research asks two questions about these components. **What does it cost to use them, and how do we know their outputs are true?** As an undergraduate I have studied both questions through three projects: training-free long-context retrieval (KAUST), error propagation in multi-agent code generation (first author), and annotator-free evaluation for low-resource Arabic dialects (graduation project).

## Past work
**1. Efficient long-context reading and retrieval.** *Periscope* (arXiv:2610.04047, under review at ICLR) factorises a long read into small probes. A frozen model answers the same question over K local and K strided spans arranged on a √N × √N grid, and each answer is scored by its log-odds at a single token. This yields an evidence map at no extra cost. I worked on CorpusProbe [[CONFIRM]], the retrieval side of this idea: a training-free, O(N^1.5) LLM-based retriever that reaches NDCG@10 of 0.526 and AUC of 0.967 on BRIGHT, outperforming BM25, embedding models and full-context reading. In the follow-up project, OBLIQ-Bench, I study *oblique* queries, whose relevance to a document is latent rather than lexical. I measure accuracy together with latency, dollar cost and TFLOPs on IBEX and T4 hardware, because a retriever that needs a full LLM per document is rarely deployable.

**2. Verification inside multi-agent pipelines.** In *How Far Does a False Claim Travel?* (first author, with Dr. A. Khanfor), I measured how one hallucinated claim spreads through a planner → implementer → reviewer pipeline. The study covered 37,800 runs over 7 claim types, 150 HumanEval and MBPP tasks, 3 seeds and 3 model families. Unchecked claims survived in up to 67% of runs. A deterministic tool check at the hand-off reduced hallucinated packages from 61% to 1.6% and wrong signatures from 67% to 12%, while LLM-based review was much weaker on signatures. The effect held on ClassEval (all 9 pre-registered contrasts, +34 to +47 pp) and on 60 SWE-bench Verified repositories. Models' self-generated hallucinations travelled about 28 pp further than injected ones, so these figures are conservative. Every run was reproduced exactly (2,844 of 2,844).

**3. Evaluation without annotators for low-resource dialects.** *Lahja* adapts Jais to Emirati and Najdi Arabic with QLoRA on one GPU. Its main contribution is evaluation: minimal-pair log-likelihood tests, a dialect classifier that separates real dialect from MSA (AUC 0.97) and from LLM-written imitation dialect (AUC 0.88), meaning-preservation scoring, and bootstrap CIs. The fine-tuned model is preferred for dialectal form 82% of the time, against 55% for few-shot prompting. A preprint on this evaluation method is submitted.

## Proposed directions
1. **Cheap, verifiable hand-offs.** Generalise deterministic hand-off checks from code (packages, signatures) to claims that tools can partially verify, such as citations, retrieved facts and numerical results. Then learn *when* a check is worth its cost, treating verification as a budget allocation problem.
2. **Retrieval that scales with relevance, not length.** Combine Periscope-style probing with lightweight first-stage retrievers so that the expensive LLM reads only where evidence is likely, and characterise exactly which oblique queries need the expensive path.
3. **Trustworthy evaluation where labels are scarce.** Extend annotator-free evaluation to other Arabic dialects and low-resource languages, and test when automatic judges can be trusted, connecting back to the verification question.

## Why [[UNIVERSITY]]
[[TAILOR: 2–3 faculty whose work matches directions 1–3, one sentence each on the concrete link. Mention compute or lab resources that matter for this work.]]

I bring a habit of pre-registered, reproducible experiments built under tight compute budgets, and I want to spend a PhD on making language models both cheaper to run and easier to trust.
