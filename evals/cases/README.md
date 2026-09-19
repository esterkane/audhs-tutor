# Eval cases
One YAML per case:
```yaml
id: hint-first-gradient-descent
block_type: new_material
questioning_style: explicit
retrieved: [ {course: "PyTorch Basics", section: "3", lecture: "12", t: "04:10", text: "..."} ]
turns:
  - learner: "Why does gradient descent overshoot with a large learning rate?"
expect:
  hard:
    no_full_solution: true
    citation_present: true
    max_sentences: 6
    no_banned_language: true
    mode_respected: true
  rubric: [cognitive_load, active_learning, metacognition, curiosity, adaptivity]
```
Baseline lives in `results/baseline.json` (commit it after the first accepted run).
