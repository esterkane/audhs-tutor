---
name: commit
description: Stage and commit current work with a Conventional Commits message after tests/lint pass. Manual only.
disable-model-invocation: true
allowed-tools: Bash(git add *) Bash(git commit *) Bash(git status *) Bash(git diff *) Bash(make test *) Bash(make lint *)
---
# Commit

Diff: !`cd "${CLAUDE_PROJECT_DIR}" && git status --short && git diff --stat HEAD | tail -5`

1. Never stage `.env*`, `data/`, `evals/results/latest.json`, or anything in `.gitignore`.
2. If source files changed: run `make lint` and the relevant `make test-*`; touch `.claude/.tests-ran` when green. Abort on failure.
3. Message: `<type>(<scope>): <imperative summary>` where type ∈ feat|fix|refactor|test|docs|chore|perf and scope is the slice/module (e.g. `feat(fsrs): due-queue endpoint`). Body: what + why, bullet per notable change, reference ADR/slice doc.
4. One logical change per commit; split if the diff mixes concerns.
5. Stage explicitly: `git status --short` first; if the tree also holds unrelated or pre-existing changes (e.g. `.env.example`, another slice), `git add -- <the slice's files>` instead of `git add -A`. Only when everything in the tree is one logical change: `git add -A -- ':!data' ':!.env*'`. Then `git commit`. Do not push. This skill is invoked by the owner only.
