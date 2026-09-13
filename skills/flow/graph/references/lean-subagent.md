# 给节点瘦身：`subagent_lean`

节点是 DSH 的子代理，而子代理要付父级的**整套技能目录**。这份文件说明怎么用一次部署补丁把它去掉，以及为什么这件事只能这么做。

## 成本有多大

DSH 把每个 skill 的 `name` + 规范化 `description` 组成**技能目录**，它：

- 每个 session 付一次；
- **每个子代理也付一次** —— 子代理加入父级的 composition，system prompt、工具 schema、技能目录都不按 depth 裁剪；
- 只能由部署层裁掉（模型面的 `subagent` 工具**不接受**裁剪参数）。

本技能集实测：25 个技能、目录总量 6639 字符，其中 5 个只给人用的技能（`ask-flow` / `humanize-it` / `article-icons` / `listenhub-tts` / `insight-diagram`）标了 `disable-model-invocation: true`，所以**模型实际看到的是 5472 字符**。一波 4 个节点 = 这份目录付 5 次。

想再压一截，只有两条路：把模型可见技能的 description 砍短（它们现在最长的几个在 330–391 字符，砍到 180 以内约省 1150 字符，代价是触发准确率要逐个验），或者用下面的补丁让节点子代理**完全不带**这份目录。

## 机制（已核对 DSH 源码）

`@deepseek-ai/dsh-tool-skill` 的注释就是这个机制的定义：

> The catalog is emitted only when the calling agent resolves this plugin's exact tool registration; **a restriction or scoped same-name shadow therefore removes both the schema and its call guidance.**

`@deepseek-ai/dsh-tool-subagent` 的 config 接受 `toolFilter`（`allow` / `deny`）与 `persona`，并在派发时应用到子代理上下文（`config.toolFilter` → `startInProcessRun` → `applyChildComposition` → `childCtx.tools.restrict(...)`）。

于是：**让一个 subagent 工具实例带上 `toolFilter.deny: [skill]`，它派出的子代理就既没有 `skill` 工具、也没有那份目录。**

## 粘贴位置

`$DSH_HOME/profiles/<profile>/cordis.patch.yml`（默认 profile 通常是 `~/.dsh/profiles/web/cordis.patch.yml`）。文件是一个顶层 YAML 数组：`- id: <行 id>` 覆盖已存在的行，`- insert: [...]` 插入新行。

**不要覆盖默认的 `tool-subagent` 行。** 那会让评审与调研子代理也失去技能加载能力（`/graph` 的波级评审可以把集成 diff 交给一个子代理）。新增一个同插件、不同工具名的行：

```yaml
- insert:
    - id: tool-subagent-lean
      name: '@deepseek-ai/dsh-tool-subagent'
      config:
        provider: spawn
        toolName: subagent_lean
        backgroundMode: continuable
        toolFilter:
          deny:
            - skill          # 技能目录 + skill 加载器一起消失
            - subagent       # 强制执行 depth 1：节点不得再派子代理
            - subagent_fork
            - workflow
            - ralph
```

**四个注意点：**

- 补丁**整块替换** `config`（不合并）。上面的 `provider` / `toolName` / `backgroundMode` / `toolFilter` 要写全，缺一项那一行就缺配置。
- `toolName` 必须唯一，且不能与现有工具重名。
- `backgroundMode: continuable` 不能省：失败节点要能 `send_message` 原地重试。
- `toolFilter` 只影响**之后新派发**的子代理；已经在跑的节点不受影响。补丁热加载（`patchReload: live`）即可，不必重启进程。

## 验证

1. 热加载后工具列表里应出现 `subagent_lean`，与 `subagent`、`subagent_fork` 并列。
2. 用 `subagent_lean` 派一个子代理，让它列出自己可用的技能 —— 它看不到 `skill` 工具，也看不到技能目录；用 `subagent` 派同样的子代理则应能看到。这一条就是「目录确实没进它的 prompt」的直接证据。
3. `subagent_lean` 派出的子代理调用 `subagent` 应当直接失败（工具不存在），这就是 depth 1 的强制点。

## 何时不要用它

- 需要子代理**加载技能**的场合继续用默认 `subagent`：波级评审的评审子代理、调研节点、`workflow` 的审计阶段。
- 节点本身不需要技能：`references/node-prompt.md` 已经把实现约束、门禁命令和报告格式全部写进提示词，这也是节点契约能止于 commit 的前提。
- 如果部署里没有 `subagent_lean`，一切照旧用 `subagent` —— 这只是省固定成本的可选项，不是流程要求。
