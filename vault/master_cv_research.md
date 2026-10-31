# Abdallah Mohamud
{{EMAIL}} | {{PHONE}} | Najran, Saudi Arabia | linkedin.com/in/booje | github.com/Boojeo | arXiv:2610.04047

## Research Summary
Computer Science undergraduate (GPA 4.99/5.0) working on long-context language models and retrieval. Co-author of Periscope, a training-free inference method that extends frozen language models beyond their context window, submitted to ICML. Background in deep learning, computer vision, and competitive programming; selected for the KAUST Academy AI Specializations Summer Program (2026). Seeking an MS/PhD to continue research on efficient, reliable LLM inference.

## Education
**Najran University, College of Computer Science and Information Systems** — Najran, Saudi Arabia
B.Sc. in Computer Science, expected July 2027
- GPA: 4.99/5.0; Annual Academic Excellence Award, three consecutive years.
- Coursework: Artificial Intelligence, Linear Algebra, Calculus, Probability & Statistics, Data Structures and Algorithms, Discrete Mathematics, Software Engineering.

## Research & Publications
**Periscope: Extending Frozen Language Models Beyond Their Context Window** — Submitted to ICML, under review
M. Eltahir*, A. Obayd*, R. Rashid, A. Alghamdi, A. Mousa, A. Mahmoud, T. Hussain, N. Khan. KAUST. *Equal contribution. arXiv:2610.04047
- Co-developed a training-free inference method that factorizes a long read into small probes: the N chunks of a text are arranged on a K×K grid (K = ⌈√N⌉), and a frozen model answers the same question over K local spans and K strided spans, scoring each answer by its log-odds at a single token.
- Scoring every chunk by its two spans yields an evidence map at no extra cost; its peak locates the chunk behind the answer.
- LongBench v2: reading only the 9k tokens of the top-ranked chunks matches the same model's best full-window read across windows from 32k to 1M tokens.
- InfiniteBench (median context 150k tokens): outperforms the best window read by 5 points.
- BRIGHT: the evidence map ranks long-document corpora with the best NDCG@10 among six methods.
- Efficiency: a 27B model reads 4.5M-token contexts on one 80GB GPU, where a single pass would need 296GB of cache.

## Training
**KAUST Academy AI Specializations Summer Program (KASP)** — KAUST, Thuwal, Saudi Arabia, 28 Jun – 20 Aug 2026
- Eight-week intensive: computer vision (CNNs, Transformers, ViT, video), representation learning (SimCLR, I-JEPA/V-JEPA), generative models (VAEs, GANs, diffusion, normalizing flows), reinforcement learning (DQN, PPO, GRPO, SAC, RLHF/RLVR).
- NLP and LLMs: attention and Transformers, pretraining and scaling laws, fine-tuning (LoRA/QLoRA, RLHF), reasoning models trained with GRPO, quantization and distillation, multimodal NLP, agentic AI.
- Final project: Periscope (see Research & Publications).

## Projects
**Lahja** — Arabic Dialect NLP, team project
- Improved performance by 5–10% on four selected Arabic dialects: Saudi, Emirati, Moroccan, and Syrian.

**Handwritten Digit Recognition (Custom VGG16)** — Python, TensorFlow, Keras
- Engineered a VGG16 CNN from scratch with a data pipeline that resizes 28x28 inputs into 2x2 mosaics; used mixed precision and global average pooling to fit an RTX 4060; 99.64% validation accuracy, 0.9964 F1 on MNIST.

**HydroPulse** — MiyahThon Water Innovation Hackathon, Jubail (Finalist)
- Designed a water-network efficiency solution with a team and presented it to judges.

## Leadership & Experience
**AI Club, Technical Committee Lead** — Najran University, Jan 2026 – Present
- Lead a 15-member technical committee; built the club website and organized hands-on AI workshops for over 100 attendees.

**Competitive Programming Lead** — 3Cs Hackathon, University of Najran, April 2025
- Ran the Competitive Programming Contest track and mentored junior students.

## Honors & Awards
- Top 10 Finalist, 6th National Programming Competition (organized by Imam Abdulrahman Bin Faisal University).
- Finalist, MiyahThon Water Innovation Hackathon, Jubail.
- Annual Academic Excellence Award, University of Najran, three consecutive years.

## Skills
- Languages: Python (advanced), Java (competitive programming). English (degree taught entirely in English).
- LLMs & Retrieval: long-context inference, document and passage retrieval, Arabic dialect NLP, benchmark evaluation (LongBench v2, InfiniteBench, BRIGHT; NDCG@10), LoRA/QLoRA fine-tuning, GRPO.
- Deep Learning: TensorFlow, Keras, CNNs, computer vision, YOLO.
- Data Science: NumPy, Pandas, Scikit-Learn, data preprocessing, feature engineering, Matplotlib.

## Certifications
- Machine Learning Specialization, DeepLearning.AI / Stanford
- Introduction to Data Science in Python, University of Michigan
- Advanced Artificial Intelligence (Stage 3), KAUST Academy
- Introducing Generative AI with AWS, Amazon Web Services
