---
name: loop-it
description: "Serial GitHub issue loop with checkpoint/resume: order open issues by dependency, implement each on its own branch, then review and ship the batch once. Triggers on: loop-it, issue loop, 批量实现, 循环实现, 恢复循环, resume loop."
user-invocable: true
---

# loop-it — 带检查点恢复的串行 Issue 循环

取一批有阻塞关系的 open GitHub issue，按依赖顺序**一次一个**内联实现，进度落到 `.loop-state.json`，崩溃后可从检查点恢复。

**这是指导，不是脚本。** 排序（拓扑 + 环打破）、下一项判定、检查点读写全部由 `scripts/loop_state.py` 完成并落盘——不要用散文重推这些算法，跑脚本、读它的输出即可。本文件只说明何时用、单个 issue 的边界，以及批末收尾。

## 何时用 / 何时不用

| 场景 | 选择 |
|------|------|
| 一批 issue 之间有真实阻塞边，要串行推进、崩溃可恢复 | **本 skill** |
| 节点之间**真并行**（互不共享文件、能各自 worktree 隔离） | `/graph`：每节点独立 worktree，按波次 fan-out；loop-it 是单工作树串行，并行会互相踩 |
| 有依赖，但部分分支可并行 | 用 `/graph`；loop-it 只做纯串行批次 |
| 只有一个 issue | 直接内联实现 → `/review-it` → `/ship-it`，不必开循环 |

## 批处理模型

默认（也是推荐）模式：**review 和 ship 都只在批末做一次**。

```
每个 issue（N 次）:  内联实现 → 用项目门禁自证 → 在该 issue 的分支上 commit
批末（1 次）:        /review-it 审整批合并 diff → /ship-it → 1 个 PR → merge → 关闭本批满足的 issue
```

- 每个 issue 用自己的分支，命名不变：`feat/issue-N-slug`（与 `/ship-it` 一致）。**不 push、不开 PR。**
- 「项目门禁」= 目标仓库自己的构建/测试/lint（如 `go build ./...`、`go test ./...`、`pnpm lint`、`mise run check`），以 issue 所属项目为准。
- 为什么批末统一 review：**审自己刚写完的代码是最弱的评审**；per-issue review 审的是可能根本活不过集成的代码。批末一次看的是集成后的完整 diff。
- 为什么批末统一 ship：per-issue PR = N 个 PR、N 次 CI、N 次 merge 争用。默认不做。
- 批末把各 issue 分支汇总到一条批次分支（`git merge --no-ff` 各分支，或直接在累积分支上顺序 commit；**`failed` 的分支不要并入**），`/review-it` 看这条分支相对默认分支（`main` 或 `master`，先解析，别假设）的 diff，`/ship-it` 从它开一个 PR。批末 PR 关闭多个 issue，因此按 `/ship-it` 的「多个 issue 共用一个 PR」逐项列出 commit / 关闭的 issue / 验收证据 / 人工验收状态——否则单个 issue 的实现无法追溯与回滚。
- **per-issue PR 模式**（仅当用户明确要求）：每个 issue 都走 `/review-it` + `/ship-it`，成本是 N 个 PR / N 次 CI / N 次 merge；这就是「昂贵模式」，用户没点名就用默认。

## 前置检查

开始前逐条验证，任一失败就停下并报告。

| 检查 | 命令 | 失败处理 |
|------|------|----------|
| gh 已认证 | `gh auth status` | 停止，提示 `gh auth login` |
| 在 git 仓库内 | `git rev-parse --is-inside-work-tree` | 停止 |
| 工作树干净 | `git status --porcelain` | 让用户选：stash 后继续 / 中止（默认）/ 强制继续 |
| 在默认分支 | `git branch --show-current` | 提示切回默认分支并 `git pull` |
| 远程可达 | `git ls-remote --heads origin` | 停止，检查网络与权限 |
| 恢复还是重来 | `.loop-state.json` 是否存在 | 恢复 / 删除重来 / 中止；`scan` 会自动合并旧状态，只有损坏文件才要求用户处理 |

`.loop-state.json` 必须加进 `.gitignore`；若已被 git 跟踪，提醒用户 `git rm --cached`。

## 执行循环

`<SKILL_DIR>` = 本技能目录，取自 loader 每次加载技能时给出的 `Base directory for this skill` 资源块。

### 1. 取 issue、排序、建检查点（全部交给脚本）

```bash
gh issue list --state open --json number,title,labels,body | python3 <SKILL_DIR>/scripts/loop_state.py scan
# 也可先落盘：python3 <SKILL_DIR>/scripts/loop_state.py scan --issues issues.json [--repo owner/name]
```

脚本负责：解析 `Dependencies: #3, #5` / `Depends on: #3` / `depends on #3` / `requires #3`；建依赖图；按编号打破环并打印警告；拓扑排序；与已有状态合并（**已记录的状态绝不丢失**，损坏文件报错拒绝覆盖）；写检查点；打印有序列表、下一项、blocked/skipped。

状态文件 schema 与旧版一致（`version`、`repo`、`total_issues`、`issues.<n>.{status,branch,phase,error_class,attempts,started_at,updated_at,completed_at,last_error}`），旧状态文件可直接恢复；`title`、`deps` 是 `scan` 追加的附加字段。

随时查进度，不要自己算：

```bash
python3 <SKILL_DIR>/scripts/loop_state.py next      # 下一项 + 其它为什么在等
python3 <SKILL_DIR>/scripts/loop_state.py summary   # 进度表
```

### 2. 逐个 issue

以 `next` 的输出为准，处理下一项：

```bash
# 记开始：attempts +1，写检查点
python3 <SKILL_DIR>/scripts/loop_state.py set --issue N --status in_progress

# 分支：每次 bash 都是全新 shell，多步 git 必须写在同一条命令里
# 默认分支不一定是 main，先解析再切
BASE="$(git symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')"
BASE="${BASE:-$(git rev-parse --abbrev-ref HEAD)}"
git checkout "$BASE" && git pull && git checkout -b feat/issue-N-slug
```

然后**内联实现**：读 issue 标题与正文，提取全部验收条件；正文引用的 PRD/SPEC（如 `tasks/prd-*.md`）一并读；按目标仓库既有风格改代码；跑该项目的门禁自证；长时间构建/测试交给 `job_*` 后台任务。持续到验收条件全部满足、门禁通过，然后在该 issue 的分支上 commit。

收尾时记录结果（脚本据此重算下一项）：

```bash
python3 <SKILL_DIR>/scripts/loop_state.py set --issue N --status shipped --branch feat/issue-N-slug
python3 <SKILL_DIR>/scripts/loop_state.py set --issue N --status skipped
python3 <SKILL_DIR>/scripts/loop_state.py set --issue N --status blocked
python3 <SKILL_DIR>/scripts/loop_state.py set --issue N --status failed --error-class build_failure --error "<message>"
```

- **跳过**：提问/讨论、纯文档、已实现、重复、带 `wontfix`/`question`/`discussion`/`invalid` 标签、无验收条件且推不出需求。
- **blocked**：依赖未 `shipped`（`next` 已经给出，不要自己判断）。依赖不在本批（issue 已关闭）也按未 `shipped` 处理；确实要放行就 `set --issue <dep> --status shipped` 手工补记。
- 每个 issue 结束后切回默认分支；**失败的分支保留**，不要删。
- 回到 `next` 处理下一项，直到 `set` 输出「全部 issue 处理完毕」。

### 3. 批末收尾（只做一次）

```bash
# 1) 把各 issue 分支汇总成批次分支后，审整批合并 diff
/review-it
# 2) 一个 PR、一次 CI、一次 merge，关闭本批满足的 issue
/ship-it
python3 <SKILL_DIR>/scripts/loop_state.py summary
```

批末评审同样**逐 issue 分节**过一遍合并 diff，重点看 issue 之间的结合部（共享接口、装配文件、配置与状态），而不是每个 issue 的内部实现。PR body 按 `/ship-it` 的「多个 issue 共用一个 PR」逐项列出每个 issue 的 commit、关闭编号、验收证据与人工验收状态。`failed` 的 issue 不进批次分支，也不进这张表。

`/ship-it` 之后保留 `.loop-state.json` 作为记录，由用户决定何时删除。

## 失败处理

错误类别（build / test / lint / merge / ci / auth / rate-limit / network / unknown）、恢复策略与最大重试次数见 [`references/error-recovery.md`](references/error-recovery.md)——它是查找表，按需加载。分类后按上限重试；重试耗尽就 `set --status failed --error-class <class> --error "<msg>"` 并继续下一项，**绝不无限重试，绝不 force-push**。

## 运行须知（DSH）

- **`/goal` 是 DSH 的 UI 命令，模型调不到**；「实现 issue」就是 agent 自己读 issue、写代码、跑门禁。**不要在循环里调用 `create_goal`**。
- 每次 bash 调用都是全新 shell：`cd`、变量不跨调用保留；`git checkout "$BASE" && git pull` 这类多步（含解析默认分支那两行）必须写在同一条命令里。
- 用 `todo_write` 维护每个 issue 一条的可见进度；它与 `.loop-state.json` 在同一状态转换后更新，冲突时以脚本为准。
- 长构建/测试用 `job_*` 后台任务，不要阻塞在单次调用里。
- 严格串行：一次只处理一个 issue（实现会改工作树）。依赖图里有真并行分支时改用 `/graph`。

## References

- [`references/error-recovery.md`](references/error-recovery.md) — 错误分类表与恢复协议。
- [`references/edge-cases.md`](references/edge-cases.md) — 边界情况处理表。
- `scripts/loop_state.py` — `scan` / `set` / `next` / `summary`，顺序与检查点的唯一实现。
- `scripts/test_loop_state.py` — 自测：`python3 <SKILL_DIR>/scripts/test_loop_state.py`。

## 与其他 skill 的关系

```
/prd → /prd-to-spec → /to-issues ─┬─→ /loop-it  (串行，一次一个 issue)
                                   └─→ /graph    (并行，波次 fan-out)
```
