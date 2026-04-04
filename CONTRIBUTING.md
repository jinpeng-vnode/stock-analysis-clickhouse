# 贡献指南

感谢您对 stock-analysis-clickhouse 项目的关注！我们欢迎各种形式的贡献。

## 🤝 如何参与

### 1. Fork 项目
点击 GitHub 页面右上角的 "Fork" 按钮，将项目 fork 到您的账户下。

### 2. Clone 到本地
```bash
git clone https://github.com/YOUR_USERNAME/stock-analysis-clickhouse.git
cd stock-analysis-clickhouse
```

### 3. 创建分支
```bash
git checkout -b feature/您的功能名
# 或
git checkout -b fix/修复的问题名
```

### 4. 提交更改
确保您的代码符合项目的代码风格，然后提交：
```bash
git add .
git commit -m "feat(scope): 添加新功能描述"
```

### 5. 推送分支
```bash
git push origin feature/您的功能名
```

### 6. 创建 Pull Request
在 GitHub 上创建 Pull Request，详细描述您的更改内容。

## 📝 代码风格

### Python 代码规范
- 使用 Python 3.11+ 的新语法特性
- 函数和变量使用 `snake_case` 命名
- 类名使用 `PascalCase` 命名
- 常量使用 `UPPER_SNAKE_CASE` 命名
- 所有函数必须添加类型注解
- 使用 `loguru` 记录日志，避免使用 `print`
- 异步代码使用 `async/await`

### 提交信息格式
```
<type>(<scope>): <简短描述>

[可选的详细描述]

[可选的关联 Issue]
```

类型说明：
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

示例：
```
feat(api): 添加股票基本信息查询接口
fix(frontend): 修复 K线图日期显示错误
docs(readme): 更新安装说明
```

## 🐛 Issue 规范

### Bug 报告
创建 Issue 时请包含以下信息：
- **标题**: [Bug] 简短描述问题
- **环境**: 操作系统、Python 版本、浏览器版本等
- **复现步骤**: 详细的重现步骤
- **期望行为**: 描述您期望发生的情况
- **实际行为**: 实际发生的情况
- **截图**: 如有相关，请附上截图

### 功能请求
创建 Issue 时请包含：
- **标题**: [Feature] 功能简短描述
- **问题描述**: 详细描述您希望添加的功能
- **使用场景**: 说明这个功能的实际应用场景
- **可能的实现**: 如果您有实现思路，请分享

## 🔍 开发流程

1. **查看 Issue**: 在开始开发前，查看相关的 Issue，避免重复工作
2. **讨论方案**: 对于大的功能改动，先在 Issue 中讨论实现方案
3. **编写代码**: 按照代码风格规范编写代码
4. **编写测试**: 为新功能添加相应的测试
5. **更新文档**: 如需要，更新相关文档
6. **提交 PR**: 创建 Pull Request 并等待代码审查

## 📋 代码审查

所有 Pull Request 都需要通过代码审查才能合并。审查重点：
- 代码逻辑是否正确
- 是否符合项目代码风格
- 是否有足够的测试覆盖
- 是否有安全漏洞
- 文档是否需要更新

## 🚀 发布流程

项目维护者会定期合并已审查的 PR 并发布新版本。

## 💬 沟通渠道

- GitHub Issues: 报告 Bug、功能请求
- GitHub Discussions: 一般讨论、问答
- Pull Request: 代码审查

## 📄 许可证

通过贡献代码，您同意您的贡献将在 [MIT License](LICENSE) 下发布。

---

再次感谢您的贡献！🎉
