<div align="right">
  <span>[<a href="./README.md">简体中文</a>]</span>
  <span>[<a href="./README_EN.md">English</a>]</span>
</div>

<div align="center">
  <h1>dsh-floway</h1>
  <p>把一整套研发工作流装进 DeepSeek Harness：需求 → 设计 → 拆解 → 并行实现 → 审查 → 交付。<br>
  技能只负责判断，排序与检查点交给带测试的脚本；实现交给各自隔离在 git worktree 里的子代理。</p>
  <div align="center">
    <a href="https://9ashwin.github.io/dsh-floway/"><img src="https://img.shields.io/badge/%E5%9C%A8%E7%BA%BF%E6%96%87%E6%A1%A3-9ashwin.github.io-d97757" alt="Online docs" /></a>
    <img src="https://img.shields.io/github/license/9Ashwin/dsh-floway" alt="License" />
    <img src="https://img.shields.io/github/stars/9Ashwin/dsh-floway?style=social" alt="Stars" />
    <img src="https://img.shields.io/github/forks/9Ashwin/dsh-floway?style=social" alt="Forks" />
    <img src="https://img.shields.io/github/last-commit/9Ashwin/dsh-floway" alt="Last commit" />
  </div>
  <h3>
    <a href="https://9ashwin.github.io/dsh-floway/">在线文档</a> ·
    <a href="#快速开始">安装</a> ·
    <a href="#技能">技能</a> ·
    <a href="#它是怎么跑起来的">工作流</a> ·
    <a href="#项目状态">项目状态</a>
  </h3>
  <img src="docs/workflow.png" alt="dsh-floway 工作流信息图" width="1000">
</div>

## dsh-floway 是什么

dsh-floway 是一套面向 **DeepSeek Harness（DSH）** 的研发工作流技能集：25 个技能，把「想法 → 交付」拆成标准步骤——需求、设计、拆解、实现、审查、交付——每一步由一个技能负责。你说想做什么，剩下的交给 Agent：澄清问题、写 PRD、拆成有阻塞关系的 Issue、在隔离的工作树里并行实现、审查、开 PR、合入。

**实现节点是子代理**，每个节点一个独立 git worktree，职责到「实现 → 跑通项目门禁自证 → commit 到自己分支」为止。泄漏检查、集成、集成后的门禁、评审、交付收成一件事，**按波次各做一次**：一个 PR 关闭这一波满足的全部 Issue。

排序、分层、环检测、检查点读写这些算术，都在技能自带的 Python 脚本里（纯标准库、带自测）。技能本体只写判断规则——**脚本管算术，技能管判断**。

## 快速开始

### 方式一：作为技能目录安装（推荐）

```bash
npx skills add 9Ashwin/dsh-floway       # 安装到全局（~/.agents/skills）
npx skills update -g                    # 之后按来源更新
```

技能会落到 `~/.agents/skills`，DSH 在会话启动时扫描该目录。这是最省事的一条路：不必动 profile 的依赖，对所有 profile 都生效。

### 方式二：作为 DSH bundle 安装（可选）

```bash
dsh plugin --profile web add -w github:9Ashwin/dsh-floway
```

包里的 `dsh.bundle` 声明会让 `dsh` 把它追加进 profile 的 `bundles` 层，技能由**包内自带的 provider** 提供。

```bash
dsh --profile web --dump-config | grep -A3 dsh-floway   # 应看到 "# == dsh-floway-skills" 层
```

<details>
<summary><strong>更多安装细节（pnpm 报错 / 锁定版本 / 本地联调）</strong></summary>

- 若 pnpm 报 `ERR_PNPM_ADDING_TO_ROOT`，是 profile 被当作 workspace 根，补上 `-w` 重跑即可（pnpm 9 需要）。
- 生产环境建议锁定 commit：`dsh plugin --profile web add -w github:9Ashwin/dsh-floway#<sha>`。
- 本包是**纯配置包**（没有构建脚本），因此不需要 `allowBuilds` 授权。
- 本地 checkout 联调：`dsh plugin --profile demo add -w /path/to/dsh-floway`。

</details>

**两条路怎么选。** Web 这类面由 shipped preset 提供技能目录，`~/.agents/skills` 本来就在它的技能根里——所以只想要技能，方式一就够。同名技能按**近层优先**去重，目录那份会赢过插件包那份。方式二多出来的是**随包携带的 preset**：谁挂哪些技能、子代理带不带技能目录（`toolFilter`）与 persona，都变成部署层的一等配置。要是你用的面根本没挂 preset（某些 minimal profile），技能可见就得靠它。

两条都装也不会重复出现，只是在 Web 面上后者赢不了前者。

> [!TIP]
> 不记得该用哪个技能？直接敲 **`/ask-flow`**——它给出下一步该敲什么，以及那一步里哪些决定得你来拍。
>
> 完整使用指南（安装、每一步怎么触发、验收标准、FAQ）在 **<https://9ashwin.github.io/dsh-floway/>**，会自动按浏览器语言跳转到中文或英文版；仓库内是 [docs/index_cn.html](docs/index_cn.html) 与 [docs/index_en.html](docs/index_en.html)。

## 它是怎么跑起来的

三个阶段，作用域互不重叠：

| 作用域 | 做什么 | 不做什么 |
| --- | --- | --- |
| **节点** | 在自己的 worktree 里实现、用项目门禁自证、**只 commit 到自己的分支** | 不 push、不开 PR、不合并、不自审 |
| **波次** | 泄漏检查 → 只合并已完成的节点 → 在集成后的树上跑门禁 → **评审一次**（逐节点分节，重点看节点之间的结合部）→ **交付一次**（一个 PR，带逐项证据表） | 不做节点级 PR |
| **批次** | `/loop-it` 的串行路径同理：一次一个 Issue 内联实现并 commit，批末统一评审与交付 | — |

几个刻意设计的地方：

- **`/graph` 只在真有并行度时用。** 一个单元、两个共享文件的单元、或「schema → API → UI」这种链式工作，交给 `/loop-it` 或直接内联做——`/graph` 的价值全部来自波内节点的真独立。
- **单节点波不建波分支。** 没有可集成的东西，就直接拿该节点分支评审与交付。
- **失败节点先原地重试。** `send_message` 复用该节点自己的上下文；重试仍失败就重跑、再失败则从波分支剔除——它的兄弟节点本来就相互独立，其余照常交付。
- **一批多 Issue 共用一个 PR 时必须逐项列证据**：commit、关闭的 Issue、证明它的测试名、人工验收状态。squash 之后那些 commit 在 `main` 上就看不见了，没有这张表就无法单独回滚或审计。

## 为什么是 dsh-floway

- **按波次算成本，而不是按节点。** 每个子代理都要为它的整个生命周期付父级的 system prompt、工具 schema 与技能目录；一个节点一次 `/review-it` + `/ship-it` 意味着 N 个 PR、N 次 CI、N 次卡在合并冲突上的机会。所以节点止于 commit，评审与交付收在波次上。
- **算术下沉到脚本。** 依赖排序、波次分层、scope 冲突串行化、检查点状态机都在 `scripts/` 里，每个都带自测；技能写的是「什么时候用、边界在哪」，不是算法复述。
- **为 DSH 的真实约束设计，而不是理想模型。** 子代理没有自己的 cwd、每次 bash 都是新 shell、委派深度默认上限 3、技能目录对每个子代理都收费——这些在技能里都落成了硬约束（绝对路径纪律 + 共享检出泄漏检查、节点不得再派子代理、可选的 [节点瘦身补丁](skills/flow/graph/references/lean-subagent.md)）。

## 技能

**不知道该用哪个？先敲 `/ask-flow`** —— 它只回答下一步该敲什么，不替你动手。

| 阶段 | 技能 | 做什么 |
| --- | --- | --- |
| 入口 | `/ask-flow` | 不知道该用哪个技能、这套流程该怎么走时问它（只路由，不替你动手） |
| 需求与设计 | `/prd` · `/prd-to-spec` · `/to-design` · `/design-it` | 需求文档 → 技术 SPEC → Go 风格设计提案 → 固定风格的 HTML 设计文档 |
| 拆解与分诊 | `/to-issues` · `/triage` | 把自己的 PRD/SPEC 拆成垂直切片 · 把**外面进来的**原始 issue 分流成可执行卡片 |
| 实现 | `/implement` · `/test-first` · `/graph` · `/loop-it` | 单个单元内联做完 · 红-绿写测试 · DAG 波次并行（每节点独立 worktree）· issue 依赖序串行（检查点可恢复） |
| 排障 | `/diagnose` · `/conflict` | 先拿到一条会变红的命令再推理的排查循环 · 逐 hunk 按意图解 merge/rebase 冲突 |
| 审查与交付 | `/review-it` · `/ship-it` · `/note-it` | 双轴评审（Spec + 8 维度标准）· 提交/PR/合入/关闭 Issue · 为 Issue 留实现笔记 |
| 代码质量 | `/smell` · `/refactor` · `/modern-go` | 架构坏味道与复杂度热点 · Fowler 重构目录 · Go 1.0→1.27+ 现代化 |
| 逆向与文档 | `/code-to-spec` · `/understand` · `/insight-diagram` | 从代码逆向出 SPEC · 把本次改动变成可交互审阅网页 · UML/架构图 |
| 内容 | `/humanize-it` · `/article-icons` · `/listenhub-tts` | 去 AI 味改写 · 文章配图 · 文本转语音 |

标了 `disable-model-invocation` 的 5 个技能（`/ask-flow` · `/insight-diagram` · 最后一行三个内容工具）**不进模型目录**：模型不会主动挑它们，你直接敲命令就行——省下的是每个会话和**每个子代理**都要付的那份固定成本。当前 25 个技能、目录总量 4818 字符，模型实际看到 **3651 字符**。

`/goal` 是 DSH 的 **UI 命令**（不是技能）：由你在命令行里敲，创建一个带自动续跑轮次的持久目标；模型不能替你创建它。

## 仓库结构

```
skills/
├── flow/       # PRD → 交付这条链上的一环，按顺序跑（9 个）
├── practice/   # 流程中途随时单独触发的工程实践（7 个）
├── meta/       # 关于这套技能集本身：路由（1 个）
└── bonus/      # 产出非代码工件：设计文档、图表、规格逆向、内容（8 个）
```

判据是「它在这条链上扮演什么角色」：`flow` 是流水线本身；`practice` 是你在中途因为「出事了 / 要保证质量」伸手拿的（测试方法、排障、冲突、外部分诊、质量巡检）；`meta` 是描述整套技能集自身的（`/ask-flow` 这个路由）；`bonus` 产生的是非代码工件。

DSH 的技能根**只扫一层**（`<root>/<name>/SKILL.md`），所以 `cordis.patch.yml` 把四个桶各列为一个 root，而不是指向 `skills/`。`npx skills add` 是递归扫描、安装时拍平，两种装法得到的技能集完全相同。`scripts/check_skills.py` 守着两个静默失败面：**技能被放回顶层**（bundle 装法看不到它），以及**某个桶漏进 patch**（那一桶会整体消失，且不报错）。

## 项目状态

![License](https://img.shields.io/github/license/9Ashwin/dsh-floway) ![Last Commit](https://img.shields.io/github/last-commit/9Ashwin/dsh-floway) ![Commit Activity](https://img.shields.io/github/commit-activity/m/9Ashwin/dsh-floway) ![Issues](https://img.shields.io/github/issues/9Ashwin/dsh-floway) ![Pull Requests](https://img.shields.io/github/issues-pr/9Ashwin/dsh-floway)

## 社区与反馈

- 🌐 [**在线文档**](https://9ashwin.github.io/dsh-floway/) — 中文 / English 使用指南
- 🐛 [**Issues**](https://github.com/9Ashwin/dsh-floway/issues) — 报错、需求、技能改进建议
- 🧩 [**DeepSeek Harness**](https://github.com/deepseek-ai/DeepSeek-Harness) — 这套技能运行的宿主

## 许可

MIT，全文见 [LICENSE](./LICENSE)。
