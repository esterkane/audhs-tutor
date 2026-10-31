# Learning methods: evidence and tutor mapping

Oct 31, 2026 · @saru

## Scope

This review covers six families of learning method and asks of each: what controlled studies show, for which kind of material, at what cost, and how it would appear in AuDHS-Tutor.

| Family | What it includes | Tutor touchpoint |
| --- | --- | --- |
| Predict before you read | Writing down title and subtitles, guessing the content, pretesting, generation effect, SQ3R / KWL | Session opener, explain-back, challenge modes |
| Visualizing | Dual coding, diagrams, concept maps, drawing-to-learn, mental imagery | Representation kinds: map, diagram |
| Sound and speech | Audio explanation, reading aloud, self-explanation, teach-back, narration vs text | Representation kind: audio; voice loop (Phase 4) |
| Breaking things and trying out | Productive failure, tinkering, deliberate errors, experimentation, inquiry | Code exercise, planted-error challenge mode |
| Dynamic data flows | Program visualization, tracing, notional machines, notebooks, animated ML diagrams | Pyodide exercises, diagram representation |
| Learner differences | Learning-styles myth, multiple representations, AuDHD attention / working memory / sensory load | Adaptation proposals, state modes |

Evidence is weighted by design: meta-analyses and replicated lab or classroom experiments first, single studies and practitioner reports marked as such. Research as of 31 October 2026; sources are listed at the end.

## Summary

The six method families collapse into one mechanism: the learner commits to something (a prediction, a trace, an explanation, a fix, a drawn map) and then gets a prompt, specific comparison against the truth. Where that commitment is present, plain text and paper match the fanciest tool; where it is absent, the medium (animation, audio, a playground) adds little.

**What works, with adult evidence****g**

- Pretesting / guessing before reading: g = 0.45–0.54 on the material guessed about, g = 0.65 when a guess is required vs 0.22 when the question is only read ([St. Hilaire et al. 2024](https://par.nsf.gov/servlets/purl/10511812)). Wrong guesses do not hurt.
- Prompted self-explanation: g = 0.55 across 64 studies, including computer science ([Bisra et al. 2018](https://www.clearinghouse.edu.tum.de/wp-content/uploads/2023/09/CHU-KR-25_ENG_Bisra_2018_Selbsterklaerungen.pdf)); oral explaining g = 0.34 vs written g = −0.07 ([Lachner et al. 2021](https://dspace.library.uu.nl/bitstream/handle/1874/413782/1_s2.0_S0959475220307337_main.pdf?sequence=1)).
- Retrieval practice with feedback: \~0.50 across 222 classroom studies; feedback roughly doubles it; helps lower working-memory students more ([Agarwal et al. 2017](https://profiles.wustl.edu/en/publications/benefits-from-retrieval-practice-are-greater-for-students-with-lo/)).
- Contrasting erroneous examples (buggy beside correct, explain and fix): never lost in 12 comparisons ([Dieterich et al. 2025](https://link.springer.com/article/10.1007/s10648-025-10071-x)).
- Integrated visuals: words and picture together d ≈ 1.35, text placed inside the picture g = 0.63–0.72 for adults; constructing a concept map g = 0.72 vs studying one g = 0.43.

**What does not work, or only conditionally**

- Unguided tinkering: d = −0.38 vs explicit instruction ([Alfieri et al. 2011](https://www.fisme.science.uu.nl/publicaties/literatuur/2011_alfieri_discovery_learning.pdf)); hints *during* a struggle g = −0.08.
- Passive animation: g ≈ 0.23, lowest for abstract content ([Berney & Bétrancourt 2016](https://tecfa.unige.ch/perso/sandra/pdf/Earli2016_berney_betrancourt_FINAL.pdf)); what the learner does with the visualization matters more than what it shows ([Hundhausen et al. 2002](https://www.academia.edu/15636659/A_Meta_Study_of_Algorithm_Visualization_Effectiveness)).
- Listening to dense technical content as first exposure; decorative or separated visuals (seductive details g = −0.33).
- Routing anyone by a "learning style": no crossover interaction in any adequately designed study ([Pashler et al. 2008](https://digitalcommons.usf.edu/psy_facpub/1765/)).

**AuDHD evidence** is thin and extrapolated: no controlled study of any of these techniques exists in diagnosed ADHD or autistic adults learning technical material. The closest proxies favour the same techniques, plus externalised structure, less decoration and no interruptions.

**Build first, in this order**

1. A predict-before-reveal primitive used everywhere: before reading a chunk, before stepping code, before running an ablation, before quiz feedback.
2. Oral explain-back and teach-back, offered beside text, with an interactive tutor-as-student.
3. Contrasting planted-error examples: syntactic and highlighted first, semantic later.
4. Lean overview map first, then a learner-completed map.
5. Externalised structure: visible plan, next cues, re-entry recap, no mid-task interruptions.

Everything else in the representation menu is a supporting rendering (diagram with in-place labels, adaptively faded worked example) or an opt-in n-of-1 experiment (audio recap, background noise, movement nudge).

## Predict before you read

Committing to a guess about a text before reading it reliably improves memory for the content guessed about, and wrong guesses do not hurt. The exact procedure (copy title and subheadings, write what you think the section says, then read) has no direct experimental test; the evidence comes from prequestions and pretesting, where the learner answers questions before studying.

**Evidence**

- Meta-analysis of 97 effects: g = 0.54 \[0.42, 0.66\] on prequestioned material, g = 0.45 after bias correction, g = 0.04 (n.s.) on non-questioned material ([St. Hilaire et al. 2024](https://par.nsf.gov/servlets/purl/10511812)). A required guess gives g = 0.65 vs 0.22 for merely reading the question; adults g = 0.62 vs children 0.22; short-answer final tests 0.67 vs multiple choice 0.42; factual prequestions 0.58 vs conceptual 0.28 (marginal).
- Independent re-analysis: pretesting subset g = 0.34 \[0.19, 0.50\], symmetric funnel plot; any lag between guess and reading eliminates the effect ([Boustani & Shanks 2022](https://discovery.ucl.ac.uk/id/eprint/10144434/1/Shanks_Heterogeneity%20and%20Publication%20Bias%20in%20Research%20on%20Test-Potentiated%20New%20Learning_VoR.pdf)).
- Expository prose with undergraduates: d = 0.45–1.1 even at 5 % pretest accuracy ([Richland, Kornell & Kao 2009](https://learninglab.uchicago.edu/Pre-Testing_files/RichlandKornellKao.pdf)); holds at under 8 % accuracy and a 24-hour delay, ηp² = 0.15–0.18 ([Kliegl & Bäuml 2025](https://link.springer.com/article/10.1007/s00426-024-02042-8)); stable from age 18 to 82 ([NSF PAR](https://par.nsf.gov/servlets/purl/10620821)).

**Boundary conditions**

- Length: a 22–24-minute lecture halved the effect relative to a 2-minute one, d ≈ 0.5 vs 1.0 ([Toftness et al. 2018](https://pure.royalholloway.ac.uk/files/30437641/JARMAC_Toftness_et_al.pdf)); the generation benefit for text holds at g = 0.63 for 301–600 words and vanishes above \~900 words, g = 0.05 ([Schindler & Richter 2023](https://link.springer.com/article/10.1007/s10648-023-09758-w)).
- Placement: non-predicted content is remembered better when it comes *before* the predicted content, as if attention closes once the target is found ([Sana & Carpenter 2023](https://pure.athabascau.ca/en/publications/broader-benefits-of-the-pretesting-effect-placement-matters/)).
- Revealing answers at pretest reduces the benefit; multiple guesses add nothing over one, and typed multiple wrong guesses with delayed feedback hurt ([Tanaka et al. 2019](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2019.00599/pdf)).
- For conceptual STEM understanding the better variant is attempting a problem or analysing contrasting cases before instruction: 43.8 % vs 14.6 % correct schema predictions, n = 36 ([Schwartz & Bransford 1998](https://www.wright.edu/sites/www.wright.edu/files/uploads/2017/Feb/event/Schwartz_Bransford_1998_TimeForTelling.pdf)).
- Motivation is the main hazard: learners rate the method as less effective even after it helps, and update only when shown their own predicted-vs-unpredicted gap, d = 0.41–0.85 ([Pan & Rivers 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC9839203)).
- SQ3R's Survey and Question steps have little empirical support; the evidence-based parts are the retrieval (3R) component and the committed answer attempt ([Learning Scientists 2021](https://www.learningscientists.org/blog/2021/3/4-1)). Advance organizers work when they tie new material to something already known ([Mahar 1992](https://www.ideals.illinois.edu/items/20405)).

**Tutor implication**

1. Split source material into 300–600-word sections keyed to headings; show title plus subheadings only.
2. Require a 2–4-sentence prediction naming at least one specific term or mechanism; optional confidence 0–100; time box 60–120 s; begin reading immediately, no reveal before reading.
3. After reading, show the prediction beside 1–3 extracted key points; the learner marks each confirmed / partly / wrong. This doubles as the feedback and recite step.
4. For conceptual LearningObjects add one bridge prompt: "which concept you already know is this most like, and how might it differ?"
5. Track prediction hit rate separately from delayed recall; after a few cycles show the predicted-vs-unpredicted retention gap. Tell the learner that 5–35 % prediction accuracy is normal.

## Visualizing

Adding a relevant, integrated graphic to words is one of the largest and most replicated effects in multimedia research. Constructing a representation beats viewing one, and decorative or separated visuals do measurable harm.

**Evidence**

- Mayer's own tallies: multimedia d = 1.35 (13/13 positive), coherence 0.86, spatial contiguity 0.82, pretraining 0.78, signaling 0.69, redundancy only 0.10 ([EdTechBooks](https://edtechbooks.org/docx/10349)). Independent meta-analyses run lower, so treat these as upper bounds.
- Signaling across 103 studies, 12,201 participants: g = 0.53 recall, 0.33 transfer; permanent structural cues (headings, bold) strongest at g = 0.71, blinking cues harmful at g = −0.56; no expertise reversal ([Schneider et al. 2018](https://www.clearinghouse.edu.tum.de/wp-content/uploads/2018/12/CHU_KR-22_-Schneider_2017_Lernmaterial_Hervorhebungen.pdf)).
- Text placed inside the picture: g = 0.63 overall, 0.72 in adult education, d = 0.78 for complex material vs 0.28 (n.s.) for simple ([Schroeder & Cenkci 2018](https://www.clearinghouse.edu.tum.de/wp-content/uploads/2019/06/CHU_KR-23_Schroeder-2018_Lernmaterial.pdf)).
- Concept maps: g = 0.58 overall; constructing g = 0.72 vs studying a provided map g = 0.43, and provided maps drop to g = 0.32 at university ([Schroeder et al. 2018](https://www.clearinghouse.edu.tum.de/wp-content/uploads/2023/10/CHU_KR-19_ENG_Schroeder-2_2017.pdf)); hyperlinked maps g = 0.017 (n.s.) ([Nesbit & Adesope 2006](https://www.sfu.ca/~jcnesbit/research/NesbitAdesope2006.pdf)).
- Learner-generated drawing: median d ≈ 0.40 and fragile ([Lawson & Mayer 2024](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2024.1452385/pdf)); support helps only when it aids integration, g = 0.35 vs −0.15 ([Biele & Leutner 2025](https://link.springer.com/article/10.1007/s10648-025-10067-7)); drawing from a finished animation underperforms because learners copy instead of translating. Drawing quality predicts retention, r ≈ .27–.32 ([Navratil & Kühl 2023](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2023.1286022/pdf)).
- Dual coding is not a style effect: instructed imagery plus verbal processing roughly doubled retention in 204 undergraduates regardless of VARK preference ([Cuevas & Dawson 2018](https://my.chartered.college/research-hub/learning-styles-versus-dual-coding-which-is-better-for-retention/)).

**Where visuals hurt**

- Seductive details g = −0.33 overall, up to −0.70 for static images and text-plus-image ([Sundararajan & Adesope 2020](https://inspire.acu.edu.au/articles/seductive-details)).
- Expertise reversal: explanations essential for novices become redundant after training; adaptive fading gained ≈ 0.46–0.69 over fixed instruction ([Kalyuga 2007](https://www.uky.edu/~gmswan3/EDC608/Kalyuga2007_Article_ExpertiseReversalEffectAndIsI.pdf)).
- Animation does not beat informationally equivalent static graphics; people think of processes as discrete steps and static frames allow re-inspection ([Tversky, Morrison & Bétrancourt 2002](https://hci.stanford.edu/courses/cs448b/papers/Tversky_AnimationFacilitate_IJHCS02.pdf)).
- Dunlosky's "low utility" for imagery applies to self-generated mental images of prose, not to provided diagrams. Sketchnoting has no credible controlled evidence. All evidence is from science/mechanics content; no controlled study covers diagrams of code, architectures or ML pipelines.

**Tutor implication**

- `map`: a lean static overview (few nodes, labels only, no hyperlink widget) that names the components and ties them to something the learner already knows, shown before the explanation. Later, have the learner extend, label a blanked version, or redraw the map, with feedback against the reference.
- `diagram`: pick the type by content structure (flow → flowchart or sequence, hierarchy → tree, parts → component diagram, state → state diagram, quantity → chart). Labels and one-line explanations on nodes and edges, never duplicated in prose below. One colour per concept class; no icons, emoji, mascots or fun-fact callouts. Prefer a short series of static frames (forward pass, then backward pass) over animation.
- Fade annotation with mastery: fully labelled on first contact, bare diagram to label later. Pair every provided diagram with a generative task, drawn from the textual explanation rather than from the finished diagram.

## Sound and speech

Audio earns its place as a channel for the learner's *own* speech (self-explanation, teach-back) and as narration over a visual, not as a way to take in dense technical text.

**Listening (input side)**

- The modality effect (narration + graphics beats on-screen text + graphics) is real but shrinks outside Mayer's lab: d = 0.72 in Ginns 2005 falls to d = 0.38, and 0.20 after publication-bias correction, in a re-analysis of 86 effects ([Reinwein 2012](https://link.springer.com/article/10.1007/s10936-011-9180-4)); d = 0.24–0.25 in a 91-study analysis, appearing mainly with system pacing (0.43), animation (0.50) and short material ([Advances in Psychological Science 2016](https://journal.psych.ac.cn/adps/EN/Y2016/V24/I3/335)). Mayer's own boundary conditions favour printed words for technical terms and learner-paced lessons.
- Spoken + written did not differ from written-only across 57 mostly postsecondary studies; on-screen *key terms* carried most of the advantage over spoken-only, verbatim captions did not ([Adesope & Nesbit 2012](https://rex.libraries.wsu.edu/esploro/outputs/journalArticle/Verbal-Redundancy-in-Multimedia-Learning-Environments/99900601157101842)).
- College-educated adults comprehended a narrative audiobook and e-text equally at immediate and two-week tests, N = 91, partly Audible-funded ([Rogowsky et al. 2016](https://journals.sagepub.com/doi/reader/10.1177/2158244016669550)). Students scored worse on a podcast lecture than on the same content as text and mind-wandered more (Daniel & Woody 2010). Technical AI/ML content is closer to the podcast case.

**Speaking (output side)**

- Prompted self-explanation: g = 0.55 \[0.45, 0.65\], 64 studies, 5,917 learners; concept-explanation prompts beat metacognitive prompts; few differences across age or domain, computer science included ([Bisra et al. 2018](https://www.clearinghouse.edu.tum.de/wp-content/uploads/2023/09/CHU-KR-25_ENG_Bisra_2018_Selbsterklaerungen.pdf)).
- Learning by teaching: g = 0.35 for preparing to teach, 0.56 for preparing plus teaching, larger when interactive ([Kobayashi 2019](https://metatoc.com/papers/112234-learning-by-preparing-to-teach-and-teaching-a-meta-analysis)).
- Oral explaining g = 0.34 vs written g = −0.07; plain self-explaining beat explaining to a fictitious student, d = 0.59, so audience framing can overload novices ([Lachner et al. 2021](https://dspace.library.uu.nl/bitstream/handle/1874/413782/1_s2.0_S0959475220307337_main.pdf?sequence=1)).
- Field study, 247 students: voice self-explanations were longer with more topic keywords, yet students first preferred text; voice preference rose from \~10 % to 46 % when free to choose. Barriers: social presence, load, performance anxiety ([DIS '24](https://unpaywall.org/10.1145%2F3643834.3661596)).
- The Feynman technique has no study of its own; it is a wrapper around these two literatures.
- Production effect (reading aloud): within-subject d ≈ 0.9–1.4 for the *specific items* read aloud, vanishing when everything is read aloud; untested for comprehension of whole texts ([MacLeod & Bodner 2017](https://uwaterloo.ca/memory-attention-cognition-lab/sites/default/files/uploads/files/macleodbodner_cdps17_0.pdf)).

**Voice with a computer tutor**

- The spoken ITSPOKE physics tutor changed the dialogue but showed no learning gain over typed dialogue ([survey, arXiv 1812.09628](https://arxiv.org/pdf/1812.09628)); 2023–2026 LLM voice-tutor papers report design evaluations without learning outcomes.
- Latency: in a 54-student within-subjects study, delays above \~4 s cut engagement, perceived competence and willingness to re-interact; spoken fillers reduced perceived delay only ([Maslych et al. CUI '25](https://arxiv.org/html/2507.22352v1)).
- Background white/pink noise: g = 0.25 for ADHD (13 studies, N = 335, mostly children), g = −0.21 for non-ADHD; no brown-noise studies at all ([Nigg et al. 2024](https://ohsu.elsevierpure.com/en/publications/systematic-review-and-meta-analysis-do-white-noise-or-pink-noise-)). See AuDHD section.

**Tutor implication**

- `audio`: narration over a visual with key terms or an outline on screen, never auto-played, transcript available; position it as recap of material already seen, not first exposure for dense content.
- Make voice the preferred channel for `explain-back` and `teach-back`. Use concept prompts ("explain why…", "justify this step…"), content-free; learner attempts before the tutor explains; the tutor-as-student asks follow-ups; notes hidden. Novices start with plain self-explanation before "teach a student" framing.
- Offer voice and text side by side with low social-presence framing: "explain this out loud to yourself; I'll listen."
- Phase-4 voice loop: median under 2 s to first audio (matches the roadmap benchmark), hard ceiling \~4 s; push-to-talk or a configurable 1–5 s end-of-turn silence for learners who pause to think; repeat and slow-down controls; live transcript always visible ([Avouris 2025](https://arxiv.org/pdf/2508.05156v1)).
- Use the production effect selectively: say the 3–5 key terms or steps aloud, not whole passages.

## Breaking things and trying out

Making errors yourself and then getting explanatory feedback is the best-supported "break it" mechanism; unguided tinkering is not.

**Struggle before instruction (productive failure)**

- g = 0.36 \[0.20, 0.51\] over 53 studies and 166 comparisons, concentrated on conceptual knowledge and transfer; procedural knowledge g = −0.03 (n.s.). Benefits grow with age (2nd–5th graders reverse). Fidelity raises g to 0.37–0.58; the decisive feature is consolidation that builds on the learners' own attempts ([Sinha & Kapur 2021](https://https-sage-cnpereading-com-443.webvpn1.xju.edu.cn/doi/10.3102/00346543211019105); [Loibl et al. 2017](https://cris.iucc.ac.il/en/publications/towards-a-theory-of-when-and-how-problem-solving-followed-by-inst/)).
- Scaffolds *during* the struggle did not help: g = −0.08 over 118 comparisons.
- Contested: several classroom studies found no advantage, and a 574-student biology course's midterm gain (d = 0.32) had vanished by the final.

**Discovery and guidance**

- Unassisted discovery loses to explicit instruction, d = −0.38 over 580 comparisons; enhanced discovery with guidance, elicited explanation or feedback wins, d = +0.30; computer skills d = 0.64; adults benefit more than children; generation alone d = −0.15 ([Alfieri et al. 2011](https://www.fisme.science.uu.nl/publicaties/literatuur/2011_alfieri_discovery_learning.pdf)).
- Desirable difficulties reverse for high element-interactivity material in novices, where worked examples win ([Chen et al. 2018](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2018.01483/full)); fading must be adaptive and not too fast ([Kalyuga 2007](https://www.uky.edu/~gmswan3/EDC608/Kalyuga2007_Article_ExpertiseReversalEffectAndIsI.pdf)).

**Learning from errors**

- Contrasting erroneous examples beat correct-only examples in 9 of 12 comparisons and never lost; plain erroneous examples are mixed (9 favour, 11 null, 1 against). Highlighting the error helps low-prior-knowledge learners; "why it is wrong" feedback beats knowledge-of-results ([Dieterich et al. 2025](https://link.springer.com/article/10.1007/s10648-025-10071-x)).
- In programming, planted *syntactic* errors reduced load and improved learning; *semantic* errors did not, because novices could not detect them (Beege et al. 2021 via [Bonetti et al. 2025](https://arxiv.org/pdf/2503.18080)).
- Errors cost enjoyment: an intelligent-tutor study found no immediate difference but a significant one-week advantage for erroneous examples, with students liking the lesson less ([Adams et al. 2014](https://www.learningscientists.org/blog/2023/7/27)). Confident errors are corrected best (hypercorrection; [Metcalfe 2017](https://annualreviews.org/doi/abs/10.1146/annurev-psych-010416-044022)).

**Programming-specific**

- Parsons problems: same learning and one-week retention as writing or fixing code, in much less time ([Ericson et al. 2017](https://www.codio.com/blog/parsons-problems)); Proof Blocks matched written proofs in 11.1 vs 43.4 minutes, d = 2.09 ([Poulsen et al. 2022](https://arxiv.org/pdf/2211.09609)); adaptive Parsons roughly doubled solve rates.
- Concrete, code-level debugging instruction with seeded bugs: 80 % localisation vs 20–44 % for abstract guidelines or nothing, held after three weeks, \~11 per group ([Zhang et al. 2025](https://arxiv.org/pdf/2509.22420)).
- Deliberately injected bugs in AI-generated code led 917 CS1 students to edit rather than re-prompt (49 % vs 35 %) and to fix them at 85 % vs 38 % for natural bugs; learning not measured ([Pădurean et al. 2026](https://arxiv.org/pdf/2607.05068)).
- Gap: no study of learners planting bugs for themselves, of predict-then-run in ML courses, or of any of this with adult self-directed learners outside courses.

**Tutor implication**

- `planted-error` mode: buggy and correct versions side by side; localise, explain, fix. Start with syntactic, highlighted bugs on new topics; move to unhighlighted semantic bugs once detection is reliable. Always give "why" feedback; route each error to a delayed FSRS item.
- `code exercise` ladder: Parsons/completion → faded worked example → open problem, gated by a quick diagnostic (can the learner trace or predict a simple case?).
- Every tinkering episode gets a hypothesis before and a comparison after. For ML ablations: predict direction and rough magnitude of the metric change, alter one hyperparameter, run, compare.
- Hint-first is consistent with the evidence only if hints are withheld during a committed attempt and the tutor's effort goes into consolidation afterwards: compare the attempt to the canonical solution, name critical features, explain the error's reasoning.
- Reserve full productive-failure episodes for 3–5 central concepts per unit; use short micro-attempts for procedures. Warn that lower enjoyment and some frustration are expected while learning improves; evaluate on delayed items, not immediate quizzes.

## Watching dynamic data flows

Watching execution or data flow helps only when the learner has to predict, supply input or construct; passive viewing produces unreliable gains.

**Evidence**

- Meta-study of 24 algorithm-visualization experiments: 11 favoured the visualization, 10 were null, 1 went the wrong way. Where one group had to exert more active effort it won in 10 of 14 studies; with equal effort only 3 of 9 differed. Constructivist theory supported in 71 % of tests, "picture fidelity" in 30 % ([Hundhausen et al. 2002](https://www.academia.edu/15636659/A_Meta_Study_of_Algorithm_Visualization_Effectiveness)).
- Text-only students who *predicted* matched animation viewers; removing the prediction condition removed the effect ([Byrne, Catrambone & Stasko](https://www.academia.edu/85216498/Do_algorithm_animations_aid_learning)). Learners who built their own input data outscored those watching supplied data.
- Jeliot classroom study: a "middle effect" — gains concentrated in average students, the strongest did not need it, the weakest were overwhelmed; benefit appeared only after sustained use ([Sorva et al. 2013](https://romisatriawahono.net/lecture/rm/survey/software%20engineering/Software%20Architecture/Sorva%20-%20Generic%20Program%20Visualization%20Systems%20for%20Introductory%20Programming%20-%202013.pdf)).
- Eye-tracking, N = 19 (2026): automated stepping "felt passive"; students traced by hand and used the visualizer to check; metaphor views were seen as childish ([Sibia et al. 2026](https://arxiv.org/pdf/2606.19570)).
- Animation meta-analyses: d = 0.37 overall, representational 0.40 vs decorational −0.05, procedural-motor 1.06 vs problem-solving 0.24 ([Höffler & Leutner 2007](https://wikicap.ulb.be/images/e/ef/Hoffler_Leutner_2007.pdf)); g = 0.23 with system-paced (0.31) beating learner-paced and iconic beating abstract ([Berney & Bétrancourt 2016](https://tecfa.unige.ch/perso/sandra/pdf/Earli2016_berney_betrancourt_FINAL.pdf)). Segmenting into chunks gives small-to-medium gains, more for higher prior knowledge ([Rey et al. 2018](https://is.tuebingen.mpg.de/publications/rey2018segmenting)).

**Tool-specific**

- Python Tutor: 20M+ users, no adequately powered learning study; its author flagged line-level stepping without sub-expression evaluation as a limitation ([Guo 2013](https://pg.ucsd.edu/publications/Online-Python-Tutor-web-based-program-visualization_SIGCSE-2013.pdf); [Guo 2024](https://pg.ucsd.edu/guo-research-statement-july-2024.pdf)).
- Tracing skill explains \~39 % of code-writing variance, "explain in plain English" \~31 %, N = 38 ([Lopez et al. 2008](https://opus.lib.uts.edu.au/bitstream/10453/10806/1/2008001530.pdf)); comprehension-first PLTutor d = 0.40 (n.s., N = 37) over Codecademy ([Nelson, Xie & Ko 2017](https://faculty.washington.edu/ajko/papers/Nelson2017PLTutor.pdf)).
- Live coding: no grade advantage over annotated static code in a 199-student quasi-experiment ([Shah et al. 2023](https://par.nsf.gov/servlets/purl/10491206)).
- Transformer Explainer, N = 90 randomized: 73.3 % quiz accuracy vs the Illustrated GPT-2 blog and the 3Blue1Brown video (p = .021 each); interactivity (own text, sampling parameters) named most helpful by 26/30; the one non-interactive module (MLP) learned worst; the video group reported understanding equal to the Explainer despite lower accuracy — "illusory understanding"; immediate post-test only ([Cho et al.](https://arxiv.org/pdf/2408.04619)).
- Instructors preferred guided one-parameter-at-a-time walkthroughs over freeform playgrounds ([Lau & Guo 2020](https://par.nsf.gov//servlets/purl/10210727)). Of \~1.23M public Jupyter notebooks, 27.6 % had no text and 3 % of academic ones a concluding cell: notebooks do not prompt reflection by themselves ([Rule et al. 2018](https://par.nsf.gov/servlets/purl/10064423)).

**Tutor implication**

- Make predict → step → compare the default of the Pyodide step-through: before each `next`, ask for the variable that will change, the next token's top-3, or the sign of a gradient; reveal; diff.
- Let the learner own the input: edit data, prompt or hyperparameter and re-run.
- Render discrete, re-inspectable states (trace table, frames-and-heap snapshot per step with the previous state visible). Use short schematic transitions only where the *change* is the concept: pointer re-binding, attention weights redistributing, gradient flowing back.
- Chunk execution at meaningful boundaries (one iteration, one layer, one token) with `next` / `back` / `replay step`, not a free scrub bar; expression-level zoom on demand.
- Pair each step with one sentence of what happened and why, plus a "why does this exist?" toggle (swap softmax for identity, ReLU for linear).
- Frame the visualizer as a checker of the learner's hand-trace; metaphor and memory views opt-in. Follow any watched sequence with a closed-book transfer item on a new input, not self-rated understanding.
- Target the middle: tutorial mode and lower density for true novices; optional verification view for near-experts.

## Learning-styles myth vs multiple representations

Matching instruction to a self-reported modality preference has no supporting evidence; combining representations and matching modality to *content* does.

**The myth**

- The required test is a style × method crossover interaction; adequately designed studies find "virtually no evidence" of it ([Pashler et al. 2008](https://digitalcommons.usf.edu/psy_facpub/1765/)).
- The one adult study with that design (auditory vs visual preference × audiobook vs e-text) found no interaction; visual-preference learners simply outscored auditory-preference learners in both modes, a reading-skill effect ([Rogowsky et al. 2015](https://www.apa.org/pubs/highlights/spotlight/issue-22)); replicated in fifth-graders ([Rogowsky et al. 2020](https://public-pages-files-2025.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2020.00164/text)).
- Among hundreds of anatomy undergraduates, 67 % did not study in their supposed style and those who did earned no better grades; specific effortful strategies predicted grades regardless ([Husmann & O'Loughlin 2019](https://bps.org.uk/research-digest/another-nail-coffin-learning-styles)).
- Over 90 % of US adults believe the myth; many revise it after a short reasoning exercise ([Nancekivell et al. 2019](https://www.apa.org/news/press/releases/2019/05/learning-styles-myth.html); ["A slippery myth"](https://research.polyu.edu.hk/en/publications/a-slippery-myth-how-learning-style-beliefs-shape-reasoning-about-/)).

**What is supported instead**

- Dunlosky's 2013 ratings have held: practice testing and spacing high; self-explanation, elaborative interrogation and interleaving moderate (interleaving now arguably high); summarising, highlighting, keyword mnemonics, imagery for text and rereading low ([Firth](https://firth.substack.com/p/jonathan-firth-s-memory-metacognition-updates-15-dunlosky-et-al-s-list-of-strategies-1347143)).
- Retrieval practice: 0.50 over 222 classroom studies, growing with retention interval; corrective feedback roughly doubles it ([Yang et al. 2021](https://eedi.com/articles/10-things-we-know-about-testing)).
- Interleaving: g = 0.42 \[0.34, 0.50\] overall, but blocking beats interleaving for word lists (g = −0.39) and expository text shows no effect ([Brunmair & Richter 2019](https://www.psychologie.uni-wuerzburg.de/fileadmin/06020400/2019/Brunmair_Richter_in_press__2019_META-ANALYSIS_OF_INTERLEAVED_LEARNING.pdf)).
- Worked examples beat problem solving for novices and reverse with expertise; fading and completion problems bridge the two. Printed text beats narration for technical terms and learner-paced lessons ([Mayer summary](https://www.unh.edu/teaching-learning-resource-hub/sites/default/files/media/2023-06/itow-research-based-principles-for-designing-multimedia-instruction-mayer.pdf)).
- No RCT isolates learner *choice* of representation as a causal lever in adults. Choice is justified indirectly: self-pacing disarms the redundancy and modality constraints, and autistic co-design participants wanted control over display.

**Tutor implication**

- The "no learning-styles typing; multiple representations instead" guardrail is correct. Never route to a representation because of a stated preference; show a diagram when the content has structure, tune annotation by prior knowledge, default to text for terminology and code.
- Evidence ranking of the representation menu: quiz (retrieval + feedback) and explain-back strongest; worked example strong for novices with fading; code exercise via completion problems as the fading step; map and diagram via multimedia, pretraining and contiguity; analogy as an elaborative-interrogation analogue (moderate); audio conditional.
- Interleave *problem types* (which loss, which data structure); block vocabulary.
- If the learner self-labels as "a visual learner", offer the short reasoning exercise rather than a contradiction.

## AuDHD considerations

Quantitative evidence on AuDHD adults learning technical material is nearly absent. What exists supports the same techniques as above, with more externalised structure, less extraneous load and no interruptions. Every effect size in this doc is an extrapolation to this learner.

**Cognition**

- ADHD shows medium neurocognitive deficits across 34 meta-analyses: working memory SMD ≈ 0.54, response inhibition 0.52, RT variability 0.53–0.66, set shifting 0.35 ([Pievsky & McGrath 2018](https://academic.oup.com/acn/article/33/2/143/3926568)). In adults, verbal *encoding* is impaired while recognition is intact, so front-load encoding support ([Skodzik et al. 2017](https://www.learningscientists.org/blog/2025/9/18)).
- In adult students, inattention predicted switch costs in *predictable* sequences (r = .19–.26), fully mediated by goal neglect rather than WM capacity ([PMC7515948](https://pmc.ncbi.nlm.nih.gov/articles/PMC7515948)): predictability alone does not help unless the preparation is done for the learner.
- Reassuring for retrieval-heavy design: the two-day benefit of retrieval practice with feedback was *larger* for lower working-memory capacity, r = −.42 ([Agarwal et al. 2017](https://profiles.wustl.edu/en/publications/benefits-from-retrieval-practice-are-greater-for-students-with-lo/)).
- The autistic "detail-first" claim is contested: across 56 articles and \~1,000 autistic participants, local accuracy g = −0.01 and global accuracy g = 0.13 (n.s.); the only large effect was *slower* global processing under local interference, RT g = −0.98 ([Van der Hallen et al. 2015](https://lirias.kuleuven.be/bitstream/123456789/461389/2/Van%20der%20Hallen%20et%20al._Psy%20Bulletin_2015.pdf)). Forcing a bottom-up sequence is unjustified; offer both entry points and allow time for integration.
- Monotropism (interest-tunnelled attention, slow cross-interest links) has thin empirical support: autistic and ADHD adults score higher on the Monotropism Questionnaire per an unreviewed preprint ([monotropism.org](https://monotropism.org/2023/mq/)); a 101-adult latent-profile study found the highest scores in a mixed ADHD–ASD profile without statistical differentiation ([Psychiatria Spersonalizowana](https://www.termedia.pl/Does-monotropism-bridge-ADHD-and-ASD-A-latent-profile-analysis-in-adults,169,57521,0,1.html)). Hyperfocus is self-reported more by ADHD adults; its performance benefit is unproven ([Ashinoff & Abu-Akel 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC7851038)).

**Qualitative convergence (neurodivergent developers and students)**

- Helps: clear task breakdown, explicit steps, TDD-style "done" signals, written communication, control over light and sound, AI as a judgment-free, non-interrupting co-presence. Hurts: interruptions, unclear steps, harsh review (rejection sensitivity), frequent switching, sensory overload, waiting on AI generation ([Gama et al. 2024](https://arxiv.org/abs/2411.13950); [Two's a Crowd](https://arxiv.org/abs/2609.21254); [Sasportes et al. 2025](https://arxiv.org/abs/2511.02736v1)).
- Autistic university students in co-design preferred well-structured text over infographics and video, muted design, no non-functional sound or motion, flat navigation, neutral tone, and control over how much is shown ([Leeds Beckett](https://eprints.leedsbeckett.ac.uk/id/eprint/2538/6/Human-Centered%20Design%20with%20Autistic%20University%20Students%20-%20Interface%2C%20Interaction%20and%20Information%20Preferences.pdf)).

**Body, noise, movement**

- Body doubling: one 12-person VR experiment; human and AI doubles both raised task efficiency (8.5 → \~11 bricks/min, p = .006) and perceived attention, no accuracy effect ([arXiv 2509.12153](https://arxiv.org/abs/2509.12153)). The widely cited FLOWN "117 adults" figures are an uncontrolled vendor survey.
- Acute exercise in adults with ADHD improves inhibitory control, SMD −0.65 \[−1.10, −0.20\], 14 RCTs, N ≈ 372, high heterogeneity, likely publication bias ([PMC11907377](https://pmc.ncbi.nlm.nih.gov/articles/PMC11907377/)); acute bouts do not improve working memory in child data ([PMC10434964](https://pmc.ncbi.nlm.nih.gov/articles/PMC10434964)).
- White/pink noise: g = 0.25 for ADHD, −0.21 for others; child-dominated, unblinded, often 70–85 dB, no brown-noise studies ([Nigg et al. 2024](https://ohsu.elsevierpure.com/en/publications/systematic-review-and-meta-analysis-do-white-noise-or-pink-noise-)); the predicted inverted-U was not found in 90 children ([Helps et al. 2014](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0112768)). Only neurotypical adult data exist (45 dB helped attention, 65 dB helped WM but raised stress; [Awada et al. 2022](https://doaj.org/article/b8bc9a610a5348698fb3dc1361bfb0a3)). The only adult-ADHD music evidence is a commercial amplitude-modulated track showing an interaction, not a main effect.

**Tutor implication**

- Externalise state: persistent visible plan (where we are, what is next, how long), announced transitions, one idea per screen, a one-line "where you were" recap on re-entry. Never interrupt an in-progress exercise; batch feedback to natural stop points; keep tutor latency low.
- Pre-train vocabulary via the map before explanation (encoding support); strip decoration (coherence is strongest for low-WM learners); in Low-capacity mode shorten the quiz and switch to recognition plus immediate feedback rather than dropping it.
- Make the bridge from the learner's existing interests and knowledge to the new concept explicit. Frame explain-back and grading non-evaluatively.
- Mode mapping. *Low-capacity*: coherence + segmenting + explicit next cues + recognition quizzes + text with one static diagram, no sound. *Steady*: constant session skeleton, FSRS-spaced retrieval, interleaved problem types, optional pre-session movement nudge framed as attention support. *Novelty*: learner picks topic order and example domain, richer media on request, scheduled non-intrusive exit cues for hyperfocus.
- Offer the co-presence functions (visible progress, gentle non-evaluative check-ins, activity-based breaks) without claiming emotional support. Noise and movement are opt-in n-of-1 experiments, never defaults; noise is never layered over narration.

## Mapping to AuDHS-Tutor

Evidence strength: **Strong** = several meta-analyses with adults, consistent direction; **Moderate** = one meta-analysis or several consistent adult studies; **Weak** = single studies, child-only, qualitative or extrapolated; **Refuted** = published nulls across adequate designs.

| Technique | Tutor touchpoint | Evidence | Build note |
| --- | --- | --- | --- |
| Predict before you read (free-text guess on title + subheadings) | New pre-read step before `simple/deep explanation`; feeds `calibration` | Moderate (prequestion g 0.45–0.54 adults; exact procedure untested) | 300–600-word chunks; ≥1 named term; optional confidence; 60–120 s; no reveal before reading; post-read confirmed/partly/wrong; show predicted-vs-unpredicted gap later |
| Problem or contrasting cases before instruction | Opener for 3–5 central concepts per unit | Moderate (g 0.36 conceptual/transfer; nil procedural; durability contested) | No hints during the attempt; consolidation compares attempt to canonical solution; micro-attempts for procedures |
| Overview map first, then learner-completed map | `map`; Stage-2 `skill-map` | Strong for pretraining/signaling; Moderate for constructing (g 0.72) | Few nodes, static, no hyperlink widget; explicit link to a known concept; later complete/label/redraw with feedback |
| Integrated diagram, in-place labels, no decoration | `diagram` | Strong (contiguity g 0.63–0.72 adults; seductive details g −0.33) | Type by content structure; labels on nodes/edges; no duplicate prose; one colour per concept class; static frames over animation; fade with mastery |
| Learner-generated drawing | Optional task after a text explanation | Weak–Moderate (median d 0.40) | Draw from text, not from a finished diagram; partial scaffold, then compare to reference |
| Oral self-explanation / explain-back | `explain-back`; voice loop | Strong (g 0.55 incl. CS; oral > written) | Concept prompts, content-free; learner first; voice and text side by side; low social presence; non-evaluative grading |
| Interactive teach-back | `teach-back` challenge mode | Moderate (prepare + teach g 0.56; interactive > monologue) | Tutor-as-student asks follow-ups; notes hidden; novices start with plain self-explanation |
| Narration over visual with key terms | `audio` | Moderate, shrinking (d 0.20–0.38; vanishes self-paced) | Never auto-play; key terms on screen, not captions; transcript; recap, not first exposure |
| Selective read-aloud of key items | Quiz / review | Moderate for item memory; untested for comprehension | Say the 3–5 key terms or steps aloud; never whole passages |
| Voice loop latency and turn-taking | Phase-4 `voice-loop` | Moderate for engagement (N = 54); none for learning | ≤2 s to first audio, ceiling 4 s; push-to-talk or 1–5 s end-of-turn silence; repeat/slow-down; live transcript |
| Planted errors in contrast with correct code | `planted-error` challenge mode | Moderate (contrasting never lost; syntactic > semantic for novices) | Buggy beside correct; localise, explain, fix; syntactic/highlighted first; "why wrong" feedback; delayed FSRS item |
| Parsons → faded example → open problem | `code exercise` (Pyodide) | Moderate (equal learning in a fraction of the time) | Trace/predict diagnostic gates the rung; adaptive fading; visible "done" |
| Predict → step → compare | Pyodide step-through / trace view | Strong directionally; effect sizes unquantified | Ask for the changing variable / top-3 token / gradient sign before `next`; diff; learner-owned input; discrete snapshots |
| Guided one-parameter ablations | `code exercise` for ML concepts | Weak (N = 90, immediate test only) | Predict metric direction first; one parameter at a time; transfer item on a new input afterwards |
| Retrieval practice with feedback, spaced | `quiz`; FSRS review | Strong (0.50; feedback doubles; helps low-WMC more) | Low stakes; recognition in Low-capacity, recall in Steady; never drop quizzing in Low-capacity |
| Interleaving by problem type | Planner within-domain interleaving | Strong, material-dependent (g 0.42; word lists g −0.39) | Interleave discriminations; block terminology |
| Confidence before feedback | `calibration`; pre-read confidence | Moderate (hypercorrection; weaker with age) | Record confidence on every assessed item; revisit corrected high-confidence errors via FSRS |
| Externalised structure, re-entry recap | Session screen, planner, `ParkingLotButton` | Weak–Moderate (goal-neglect mediation; qualitative) | Persistent plan; announced transitions; one idea per screen; "where you were" line on resume; no mid-exercise notifications |
| Background white/pink noise | `sensory-settings` | Weak (child-dominated; harms non-ADHD; no brown noise) | Opt-in with n-of-1 self-test; moderate volume; never over narration |
| Movement nudge before session | `energy-planner` movement block | Moderate for inhibition in ADHD adults (biased); none for learning | Frame as attention support; 20–30 min moderate aerobic |
| AI body-doubling / co-presence | `body-doubling` (Stage 4) | Weak (N = 12; qualitative) | Visible progress; gentle check-ins; activity-based breaks; no emotional-support claim |
| Learning-style routing | Nowhere | Refuted | Keep the guardrail; if the learner self-labels, offer the short reasoning exercise |

**Roadmap additions by stage**

- Stage 1: add the pre-read prediction step and confidence capture to `tutor-turn` and `assess-evidence` — cheapest, best-evidenced single lever. Add "predict the output" to the first code exercise.
- Stage 2: in `representations`, specify the diagram rules (contiguity, no decoration, static frames) and the map-completion task. In `challenge-modes`, implement planted-error as *contrasting* pairs with a syntactic → semantic ladder; route each error to an FSRS delayed item.
- Stage 3: chunk ingested sources at 300–600 words under headings so the pre-read step has units to work with.
- Stage 4: first n-of-1 experiments = (a) pre-read prediction on vs off on matched LearningObjects, (b) noise on vs off, both scored on delayed recall. Add the "where you were" recap to `session_checkpoint` resume.
- Stage 5: route `explain-back` and `teach-back` through voice first with text fallback; measure whether voice explanations are longer and improve delayed recall, since no study has measured learning outcomes for an LLM voice tutor.
- Stage 6: the bandit planner's reward stays delayed-review outcome, never satisfaction — every effective technique here (errors, pretesting, productive failure) lowers immediate enjoyment.

The open question the literature cannot answer is whether any of this transfers to a diagnosed AuDHD adult studying alone with an LLM; nobody has run that study. The n-of-1 experiment engine is therefore the only route to population-specific evidence, and its first trials should test the cheapest, best-supported levers (pre-read prediction, oral explain-back) against delayed recall before anything is spent on richer media or voice polish.
