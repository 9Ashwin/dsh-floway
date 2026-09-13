---
name: conflict
description: "解决进行中的 git merge / rebase 冲突：查清各方意图后逐 hunk 解，跑项目门禁，绝不 --abort。Triggers: conflict, 冲突, merge conflict, rebase 冲突, 解冲突, 合并冲突."
---

# conflict — 逐 hunk 按意图解冲突

1. 看清现状。`git status`、`git log --oneline --graph -10`、列出冲突文件。确认这是 merge 还是 rebase、从哪分出来的、这次合并要达成什么——目标不清楚时选边就是抛硬币。

2. 找出每处冲突的原始意图（难点全在这里）。读两边的 commit message、看对应的 PR 与 issue、必要时 grep 调用方。不要只看哪边新、哪边大就选哪边：冲突的两边通常各自解决过不同的问题，"哪边更新"和"哪边对"没有关系。
   - `git log --merge -p <文件>` 只看与冲突相关的提交
   - `git show <sha> -- <文件>` 看某次改动到底改了什么、为什么

3. 逐个 hunk 解。能同时保留两边意图就都保留；真的不兼容时，选与本次合并目标一致的那一边，并把这个权衡写进 commit message。绝不发明新行为——冲突不是加需求的地方。永远解，不 `git merge --abort` / `git rebase --abort`：abort 会把已经解好的 hunk 一起丢掉，下一次面对的是同一堆冲突。

4. 跑项目门禁。找到该仓库自己的检查命令（`mise run check`、`go build ./... && go test ./...`、`pnpm --dir web lint` …），至少跑构建 + 测试，把合并弄坏的地方修好。判据是合并后的树自己通过门禁，而不是"两边合起来看起来对"——两边各自正确、合起来编译不过或语义变了，正是合并最典型的失败。

5. 收尾。`git add` 全部冲突文件，把这次操作做完（rebase 时 `git rebase --continue` 直到所有提交重放完）。然后把"哪边让了什么"写进 commit / PR 说明，让后面看历史的人知道这不是随手选的。

## 在 DSH 里

- 在 `/graph` 的节点里解冲突时，冲突在该节点的 worktree 内——用绝对路径与 `workdir=`。
- 在共享检出上解冲突时，解完确认 `git status` 除了这次合并没有别的脏东西：共享检出的干净是编排器做泄漏检查的依据。
- 冲突牵涉多个节点/多个 PR 的改动时，先确认这次要合的是哪一个目标，别把两件事的意图搅在一起。
