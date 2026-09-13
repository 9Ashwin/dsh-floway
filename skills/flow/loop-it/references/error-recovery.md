# 错误分类与恢复 (error-recovery)

`/loop-it` 的查找表：出错时先分类，再按策略恢复。分类结果用
`loop_state.py set --error-class <class> --error "<message>"` 记进检查点，
`summary` / `next` 会把它显示给下一轮。

| 错误类别 (error_class) | 检测信号 | 恢复策略 | 最大重试 |
|------------------------|----------|----------|----------|
| `build_failure` | 编译错误、undefined、类型错误 | 读错误，修代码，重新构建 | 3 |
| `test_failure` | 断言失败、`test failed` | 读测试输出，修实现，重跑测试 | 3 |
| `lint_failure` | lint 错误、格式问题 | 自动修复（`lint --fix` / `gofmt`），重跑 | 2 |
| `merge_conflict` | `CONFLICT` 标记 | rebase `origin/main`，解决冲突，push | 2 |
| `ci_failure` | `gh pr checks` 失败 | 读 CI 日志，本地修复，push | 2 |
| `auth_failure` | 403、401、认证错误 | 停止，告知用户重新认证 | 0 |
| `rate_limit` | `rate limit`、`secondary abuse` | 等待 60s，重试 | 3 |
| `issue_unclear` | issue 无验收条件且无法推断需求 | 跳过，标记 `failed` | 0 |
| `network_error` | timeout、connection refused | 等待 30s，重试 | 3 |
| `unknown` | 其他情况 | 记录完整错误，跳过 | 0 |

**恢复协议：**

1. 匹配错误类别。
2. 匹配成功 → 应用恢复策略，重试最多 N 次（同一条命令失败后不要换个说法反复重跑）。
3. 重试全部失败 → `set --issue N --status failed --error-class <class> --error "<msg>"`，写检查点，继续下一个 issue。
4. 无法匹配 → 按 `unknown` 记录完整错误后继续。
5. **绝不无限重试。绝不未经确认 force-push。**

**在默认（批末 review/ship）模式下的位置：**

- `build_failure` / `test_failure` / `lint_failure` / `issue_unclear` 在每个 issue 的内联实现阶段就会遇到，按上表就地重试。
- `merge_conflict` / `ci_failure` 通常**推迟到批末**：批末把各 issue 分支汇总成一条批次分支、跑 `/review-it` + `/ship-it` 时才会出现。此时按上表处理，且要意识到它影响的是整个批次，不只是单个 issue。
- `auth_failure` / `rate_limit` / `network_error` 与阶段无关，随时可能命中。
