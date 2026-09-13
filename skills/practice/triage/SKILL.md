---
name: triage
description: "处理别人提的原始 issue 与 bug 报告：复现、定角色、补成 agent 可执行的卡片，信息不足时按模板要信息。Triggers: triage, 分诊, 处理 issue, 一堆 bug, 归类, 要信息, 清理 issue."
---

# triage — 把进来的原始条目变成可执行的卡片

`/to-issues` 处理的是**你自己**从 PRD 拆出来的东西，那些已经是 agent-ready 的；**这个技能处理从外面进来的**：bug 报告、用户反馈、别人提的需求。**不要对 `/to-issues` 产出的卡片做 triage。**

## 角色（每条最后必须落到一个）

| 角色 | 含义 | 动作 |
| --- | --- | --- |
| `ready` | 复现/需求清楚，验收条件写得出来 | 补全正文（复现步骤、期望、验收条件、影响面），打 `ready`，交给主线 |
| `needs-info` | 缺关键信息，现在无法判断 | 按下面的模板发一条评论，打 `needs-info` |
| `bug-confirmed` | 确实是 bug，但根因未定 | 记下症状与最小复现，转 `/diagnose` |
| `duplicate` | 已有同一条 | 评论指路 → 关闭 |
| `wontfix` | 明确不做 | 评论写清理由（对应哪条产品边界）→ 关闭 |

## 先看哪些需要处理

```bash
gh issue list --state open --limit 50 --json number,title,labels,createdAt,comments \
  --jq '.[] | select((.labels|map(.name)|index("ready")|not) and (.labels|map(.name)|index("needs-info")|not)) | "\(.number)\t\(.createdAt)\t\(.title)"'
```

## 处理一条

1. **先复现 / 先理解**：能不能按报告里的步骤重现？重现不了就明确说"我按 X 复现不了"，不要假装。
2. **判断影响面**：影响谁、会不会坏数据、有没有绕过办法、是不是老版本才有。
3. **补成 agent-ready 的卡片**：正文要写到"一个不共享本次对话上下文的子代理也能独立开工"的程度——复现步骤、期望行为、验收条件、涉及文件/模块、明确的非目标。这条标准与 `/to-issues` 一致。
4. **标注 + 按角色行动**（关闭时说明理由并指路）。

## 要信息的模板（`needs-info`）

```markdown
需要更多信息才能判断这个条目。

**已知**：<他给了什么>
**还缺**：
- [ ] <最小复现步骤 / 版本号 / 配置 / 完整报错>
- [ ] <期望行为 vs 实际行为>

补齐后我会重新评估；如果这是老版本的问题，请先确认在最新 <版本/commit> 上仍然存在。
```

## 记录

每条处理完，**在那个 issue 上留一条评论**说明结论（角色 + 理由 + 下一步），不要只改标签——后来的人要能看懂"为什么这么判"。整批处理完，把新增的 `ready` / `needs-info` / `wontfix` 数量报给用户，并把 `ready` 的那些交给主线（一串有依赖关系的用 `/loop-it`，互不共享文件的用 `/graph`）。
