# 边界情况 (edge cases)

按需加载的查找表：正常流程走 `SKILL.md` 即可，命中下表时再查。

| 场景 | 处理 |
|------|------|
| 没有 open issue | `scan` 打印 `✅ No open issues found. Nothing to do.` 后退出 |
| 所有 issue 都是提问 | 逐个 `set --status skipped`，最后 `summary` |
| `gh` 未认证 | 前置检查停止，提示 `gh auth login` |
| issue 没有正文 | 只用标题判断 skip / implement |
| issue 引用 PRD/SPEC（如 `tasks/prd-*.md`） | 读取被引用文件作为实现上下文 |
| 多个 issue 互相依赖 | `scan` 拓扑排序，依赖先处理 |
| 循环依赖 | `scan` 打印 `⚠️ 循环依赖检测到`，按最低编号打破（忽略该 issue 的依赖边）并继续 |
| 依赖不在本批（issue 已关闭） | 按未 `shipped` 处理，依赖方 waiting；确实要放行就 `set --issue <dep> --status shipped` 手工补记 |
| 开始前工作树脏 | 前置检查：stash 后继续 / 中止（默认）/ 强制继续 |
| 状态文件损坏（非法 JSON 或字段缺失） | `loop_state.py` 报错退出，**绝不覆盖**；由用户修复或删除后重跑 `scan` |
| 状态文件来自另一个 repo | `scan` 打印 repo 不一致警告；确认不是同一批就删除状态文件重来 |
| 上次运行留下 `in_progress` 的 issue | `next` 会把它作为「恢复 in_progress」返回；检查分支与已有改动后决定继续或重跑 |
| 用户在循环中途放弃 | 检查点已是最新，下次 `scan` + `next` 即可恢复 |
| 循环期间新建了 issue | 本批不重新拉取；跑完当前批次后再开一次 `/loop-it` |
| `.loop-state.json` 被 git 跟踪 | 提醒用户加入 `.gitignore` 并 `git rm --cached` |
| 误以为需要外部 goal 命令 | 没有外部 goal 命令可用；「实现 issue」由 agent 内联完成，不要因此中止循环 |
| issue 之间真并行（互不共享文件） | 本 skill 仍串行；改用 `/graph` 做波次并行（每节点独立 worktree） |
| 长时间构建 / 测试 | 作为后台任务运行，拿到任务标识后继续别的工作 |
| `/ship-it` 在批末失败 | 按 `error-recovery.md` 分类；批次分支与检查点都还在，修好后重新 ship，不必重跑已 shipped 的 issue |
