# 问题跟踪器：GitHub

本仓库的问题和 PRD 均以 GitHub Issue 的形式管理。所有操作使用 `gh` CLI 完成。

## 约定

- **创建问题**：`gh issue create --title "..." --body "..."`。
- **读取问题**：`gh issue view <number> --comments`，同时读取标签。
- **列出问题**：使用 `gh issue list --state open --json number,title,body,labels,comments`，并按需添加筛选条件。
- **评论问题**：`gh issue comment <number> --body "..."`。
- **添加／移除标签**：`gh issue edit <number> --add-label "..."` / `--remove-label "..."`。
- **关闭问题**：`gh issue close <number> --comment "..."`。

通过 `git remote -v` 确定仓库；在克隆的仓库目录内，`gh` 会自动完成此操作。

## 技能路由

- 当技能要求“发布到问题跟踪器”时，创建一个 GitHub Issue。
- 当技能要求“获取相关工单”时，运行 `gh issue view <number> --comments`。
