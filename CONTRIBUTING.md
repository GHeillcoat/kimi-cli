# 贡献 Kimi CLI

感谢您有兴趣为 Kimi CLI 做出贡献！

我们欢迎各种形式的贡献，包括修复 bug、开发新功能、改进文档、修正拼写错误等。为了保持高质量的代码库和用户体验，我们为贡献者提供以下指导方针：

1. 我们只合并与我们路线图一致的拉取请求（pull request）。对于任何引入超过 100 行代码更改的拉取请求，我们强烈建议您在开始工作前，通过[提交 issue](https://github.com/MoonshotAI/kimi-cli/issues) 或在现有 issue 中与我们进行讨论。否则，您的拉取请求可能会在未经审查的情况下被关闭或忽略。
2. 我们坚持高代码质量。请确保您的代码质量与前沿的编程智能体所写的代码相当，甚至更好。在您的拉取请求被合并之前，我们可能会要求您进行修改。

## 提交前钩子 (Pre-commit hooks)

我们通过 [pre-commit](https://pre-commit.com/) 在本地运行格式化和检查。

1. 安装 pre-commit（任选其一）：`uv tool install pre-commit`、`pipx install pre-commit` 或 `pip install pre-commit`。
2. 在此仓库中安装钩子：`pre-commit install`。
3. （可选）在提交 PR 前对所有文件运行检查：`pre-commit run --all-files`。

安装后，格式化和检查将在每次提交时运行。您可以使用 `git commit --no-verify` 来跳过某个中间提交的检查，或使用 `pre-commit run --all-files` 手动触发所有钩子。

这些钩子会执行 `make format` 和 `make check`，因此请确保已经运行了 `make prepare`（或 `uv sync`）并且本地依赖已安装。
