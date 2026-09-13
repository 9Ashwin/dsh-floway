---
name: review-it
description: "Two-axis code review closeout: Spec (did the diff do what was asked — missing, extra, wrong) and Standards (a fixed 8-dimension focus), reported separately. Triggers on: review-it, code review, autoreview, 代码审查, 审查这次改动."
---

# review-it — Code Review Closeout

Run the review closeout before committing or shipping. **Under DSH there is no external review CLI: the agent that loaded this skill is the reviewer.** It generates the diff, applies the Review Focus below to it directly, and reports findings by severity.

Use when:
- user asks for code review / review-it / autoreview
- after non-trivial code edits, before final/commit/ship
- reviewing a local branch or PR branch after fixes
- at a `/graph` wave fan-in (one review of the integrated diff)

## Contract

- Treat review output as advisory. Never blindly apply it.
- Verify every finding by reading the real code path and adjacent files.
- Read dependency docs/source/types when the finding depends on external behavior.
- Reject unrealistic edge cases, speculative risks, broad rewrites, and fixes that over-complicate the codebase.
- Prefer small fixes at the right ownership boundary; no refactor unless it clearly improves the bug class.
- Keep going until review returns no accepted/actionable findings.
- If a review-triggered fix changes code, rerun focused tests and rerun review.
- Stop as soon as the review comes back clean with no actionable findings.
- If rejecting a finding as intentional/not worth fixing, add a brief inline code comment only when it explains a real invariant or ownership decision that future reviewers should know.
- Do not push just to review. Push only when the user requested push/ship/PR update.

## Two axes — reviewed separately, never merged

Every review answers two different questions:

- **Spec** — does this diff do **what was asked**? Every acceptance criterion met, nothing extra that nobody requested, nothing missing, and no "right shape, wrong behaviour" hiding behind correct-looking code.
- **Standards** — is this **good code in this repo**? That is the eight dimensions below.

A change can pass every standard and still implement the wrong thing, and one merged ranked list hides exactly that: naming and style findings crowd out a missing requirement. Report the two axes as **two sections**, never as one ranking.

### Spec axis

1. **Find the spec before reading the diff**: the issue numbers in the commit messages (`gh issue view <n>`), a path the user handed you, or a matching `tasks/prd-*.md` / `tasks/spec-*.md` / `docs/*.md`. None exists → say so and review against the user's stated request; **do not invent requirements**.
2. **Check it three ways**: required but **missing** / **extra** but unrequested / present but **wrong**.
3. **Quote the criterion** each finding is checked against, so it is falsifiable rather than a preference.

## Review Focus — Standards 轴

请 review 当前 diff。不要只看语法和明显 bug，请重点检查以下维度，最后按严重程度排序：

1. **隐藏副作用 (Hidden Side Effects)** — 变更是否在非显而易见的地方产生级联影响？是否修改了共享状态、全局变量、或外部依赖的行为？
2. **破坏兼容性 (Breaking Compatibility)** — 是否改变了 API 签名、数据结构、配置文件格式、或命令行接口？现有调用方是否会受影响？
3. **边界情况 (Edge Cases)** — null/空值/空集合、极大/极小值、并发/竞态条件、异常路径是否被正确处理？
4. **性能风险 (Performance Risks)** — 是否引入了不必要的循环嵌套、N+1 查询、大对象分配、阻塞 I/O、或锁竞争？
5. **安全风险 (Security Risks)** — 是否存在注入、越权、敏感信息泄露、不安全的反序列化、或依赖版本漏洞？
6. **命名误导 (Naming Misleading)** — 变量/函数/类型名称是否与实际行为不一致？是否存在名不副实或语义模糊的命名？
7. **测试不足 (Insufficient Testing)** — 关键路径、边界条件、错误处理是否缺少测试覆盖？现有测试是否真正验证了期望行为？
8. **未来维护成本 (Future Maintenance Cost)** — 是否引入了不必要的抽象、重复代码、隐式耦合、或难以追踪的控制流？后来者是否容易理解和修改？

## Pick Target

**Dirty local work** (default) — review in place, covering the working tree (staged + unstaged) *and* untracked files:

```bash
git status --short
git diff
git diff --cached
```

**Branch / PR work** — generate the diff, then review that file:

```bash
base=$(gh pr view --json baseRefName --jq .baseRefName 2>/dev/null || echo main)
git diff "origin/$base"...HEAD > /tmp/review-it.diff
```

**Integrated wave** (called by `/graph` at fan-in) — target `git diff main...wave-{K}-{slug}` (or the single node's branch) and review it **one section per node**, spending the pass on the seams between nodes: shared interfaces, wiring/setup files, config and state that two nodes both touch. That is the class of defect a per-node review cannot see.

To have a *child* do the review instead, hand the diff path to a `subagent` with a fully self-contained prompt — it sees none of this conversation.

Two DSH mechanics matter here: bash starts a **fresh shell per call** (a `base=…` assignment does not survive into the next call, so keep the two lines in one invocation or pass an explicit `workdir`), and `review-it` has no external command to shell out to, so never invent one.

## Parallel Closeout

Format first if formatting can change line locations. Then it's OK to run tests and review in parallel:

```bash
<SKILL_DIR>/scripts/review-it --parallel-tests "<focused test command>"
```

`<SKILL_DIR>` is this skill's own directory — DSH states it on load as `Base directory for this skill`. The path is never a bare `scripts/review-it`: that resolves against the project cwd, not the skill.

Tradeoff: tests may force code changes that stale the review. If tests or review lead to code edits, rerun the affected tests and rerun review until no accepted/actionable findings remain.

## Uncommitted vs Branch Review

- **Uncommitted changes** (staged/unstaged): review them in place
- **Committed, not pushed**: `git diff origin/main...HEAD`, then review
- **Pushed/PR**: same as committed, against the PR base
- **Clean working tree**: skip review if there's truly nothing to review

## Helper

Bundled helper for target detection and parallel test + review orchestration:

```bash
<SKILL_DIR>/scripts/review-it --help      # e.g. ~/.agents/skills/review-it/scripts/review-it --help
```

The helper:
- Detects the running agent (`--agent auto`): DSH via `DSH_SESSION_ID` / `DSH_HOME`, and it **defaults to DSH** when nothing else matches
- Detects whether to use uncommitted review or branch diff review
- For branch mode: generates the diff against `origin/main` (or the PR base)
- Prints what to review instead of an external command — DSH has no review CLI, so the calling agent does the review
- Supports `--parallel-tests` for concurrent test + review execution
- Supports `--dry-run` for checking what command would be used
- Prints `review-it clean: no accepted/actionable findings reported` when review is clean

## Other CLIs

Claude Code, Codex, OpenCode, DeepSeek TUI and Antigravity CLI each have their own review command; the matrix, their exact invocations, and the `--agent` values that force them are in [`references/other-clis.md`](references/other-clis.md). Load that file only when you are running under one of them.

## Final Report

Include:
- review target (uncommitted / branch / PR base / wave)
- **spec axis**: what was required (with the source you read), and what is missing / extra / wrong
- **standards axis**: findings accepted/rejected, briefly why
- tests/proof run
- the clean review result, or why a remaining finding was consciously rejected

Do not run another review solely to improve the final report wording. If review exited clean with no actionable findings, report that as clean.
