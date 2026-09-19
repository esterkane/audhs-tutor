# Adaptive learning, LxD and local fine-tuning — research summary (2026-09-19)

Full report is in the project chat artifact "Designing a Personal AI-Adaptive Learning System". Key points the codebase depends on:

## A. What existing systems teach
- Math Academy: prerequisite knowledge graph + individualized spaced repetition (FIRe: reviewing a topic implicitly reviews prerequisites) + interleaving; blocked practice gives a false sense of mastery.
- Duolingo Half-Life Regression (Settles & Meeder, ACL 2016) and FSRS (Anki ≥ 23.10; DSR model; defaults trained on ~727M reviews) — FSRS is the reusable scheduler.
- BKT (pyBKT), Elo/IRT are the right learner-model tools for n=1; DKT is data-hungry.
- Kestin et al. 2025 (Sci Rep 15:17458): AI tutor with brief, one-step, solution-grounded design ≈ doubled learning gains vs active-learning class in less time.
- Bastani et al. 2025 (PNAS 122(26)): unguarded GPT help → +48% practice but −17% unaided later; hint-scaffolded version avoided harm.
- LearnLM (Jurenka et al. 2024): five principles — manage cognitive load, inspire active learning, deepen metacognition, stimulate curiosity, adapt to learner — used as prompt scaffold and eval rubric.
- Bridge (Wang et al., NAACL 2024): conditioning on expert tutor decisions → +76% preference. Tutor CoPilot (Stanford 2024/25): +4–9 pp mastery.

## B. Learning-science rules built into the planner
Retrieval practice + spacing (strong); worked examples for novices then fading; expertise reversal; within-domain interleaving of confusable concepts (moderate); cross-domain interleaving is engagement/spacing, not encoding; productive failure only above mastery ≈ 0.6; confidence ratings before feedback (calibration); learning styles debunked → multiple representations; SDT autonomy support, gamification off by default; movement before encoding or immediately after (Loprinzi 2019; Roig 2013), never during; guitar = deliberate/variable practice + consolidation; language = comprehensible input + spaced vocab + voice practice.

## C. "A system that learns"
Log xAPI-style events from day one (docs/EVENT-SCHEMA.md). Ladder: prompt profile → RAG over history → contextual bandit (reward = delayed review outcome) → MLX LoRA/QLoRA SFT (Qwen/Gemma/Llama 7–14B) → ORPO/KTO on preference pairs. Risks: overfitting, sycophancy; never optimize for satisfaction.
Datasets/repos to reuse: MathDial (CC BY-SA), Bridge, SocraticLM/SocraTeach, EduChat, MathTutorBench, CIMA, TSCC.

## D. Voice (Apple Silicon, 2026)
STT: Whisper large-v3-turbo (whisper.cpp / MLX / WhisperKit) default; Parakeet-MLX for streaming English. TTS: Kokoro-82M default; Chatterbox for cloning; Piper fallback. Orchestration: Pipecat / LiveKit Agents; hosted realtime (OpenAI/Gemini Live) only for conversational language practice.

## E. Session template
0 movement 5–10 · 1 retrieval 5–10 · 2 new material 20–25 · 3 challenge 10 · 4 interleaved review 10 · 5 language/guitar 15–20 · 6 confidence-rated recap 5. Switch at block boundaries only.
