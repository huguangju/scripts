# zread-generate

`zread-generate` 对 `zread generate --stdio` 做了一层封装，用于无人值守地生成仓库文档。

当一次较长的生成任务因为模型或 API 的瞬时错误中途失败时，这个包装脚本尤其有用。它会尝试续跑草稿、在 zread 暴露重试入口时自动重试失败页面，并在成功退出前校验最终生成的 `.zread/wiki` 输出是否完整可用。

## 用法

在需要生成文档的仓库目录中执行：

```bash
zread-generate
```

也可以在任意目录下指定目标仓库：

```bash
zread-generate --cwd /path/to/repo
```

如果希望增加进程级重试次数：

```bash
zread-generate --cwd /path/to/repo --max-runs 10
```

如果允许 zread 在页面重试耗尽后提交部分 wiki：

```bash
zread-generate --cwd /path/to/repo --skip-failed
```

## 依赖要求

- Node.js 18 或更高版本
- 已安装 `zread` CLI，且能在 `PATH` 中找到
- `zread` 已完成配置，并可正常访问可用的 LLM Provider

## 行为说明

- 启动 `zread generate --stdio -y`。
- 当存在 `.zread/wiki/drafts` 时，自动附加 `--draft resume`。
- 以 `done/total` 格式打印页面进度。
- 当 zread 因页面失败而暂停时，自动发送 `retry` 指令。
- 如果进程退出后没有得到有效的当前 wiki，则重新执行整条命令。
- 在成功前会校验以下内容：
  - `.zread/wiki/current` 必须存在
  - 选中的版本目录必须包含 `wiki.json`
  - `wiki.json` 中列出的每个页面文件都必须存在
  - 不应残留草稿目录

## 配置项

命令行参数：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--cwd <repo>` | 当前目录 | 要生成文档的仓库 |
| `--max-runs <n>` | `5` | 最大进程级尝试次数 |
| `--retry-delay-ms <ms>` | `5000` | 进程级重试之间的等待时间 |
| `--skip-failed` | 关闭 | 向 zread 透传 `--skip-failed` |

环境变量：

| 变量 | 说明 |
| --- | --- |
| `ZREAD_MAX_RUNS` | 等同于 `--max-runs` |
| `ZREAD_RETRY_DELAY_MS` | 等同于 `--retry-delay-ms` |
| `ZREAD_SKIP_FAILED=1` | 等同于 `--skip-failed` |

## 退出码

- `0`：wiki 生成完成，且校验通过
- `1`：在配置的重试次数内仍未完成生成
- `127`：无法启动 `zread`
