# 贡献指南

感谢您考虑为 Standard Review Skill 做出贡献！

## 🤝 如何贡献

### 报告问题

如果您发现了 bug 或有功能建议，请：

1. 检查 [Issues](https://github.com/yourusername/standard-review/issues) 中是否已有相关问题
2. 如果没有，请创建新 Issue，包含：
   - 清晰的标题和描述
   - 复现步骤（如果是 bug）
   - 预期行为和实际行为
   - 环境信息（Python 版本、操作系统等）

### 提交代码

1. **Fork 仓库**
   ```bash
   git clone https://github.com/yourusername/standard-review.git
   cd standard-review
   ```

2. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **进行更改**
   - 遵循代码风格指南
   - 添加必要的测试
   - 更新文档

4. **提交更改**
   ```bash
   git add .
   git commit -m "Add: your feature description"
   ```

5. **推送到 GitHub**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **创建 Pull Request**
   - 提供清晰的标题和描述
   - 引用相关的 Issue
   - 等待代码审查

## 📝 代码风格

### Python 代码规范

- 遵循 [PEP 8](https://www.python.org/dev/peps/pep-0008/) 规范
- 使用 4 个空格缩进
- 函数和变量使用 snake_case
- 类使用 PascalCase
- 添加适当的注释和文档字符串

### 文档规范

- 使用 Markdown 格式
- 保持简洁清晰
- 提供示例代码
- 更新相关文档

## 🧪 测试

### 运行测试

```bash
python -m pytest tests/
```

### 编写测试

- 为新功能添加单元测试
- 确保测试覆盖主要功能
- 使用 pytest 框架

## 📚 文档

### 更新文档

- 更新 README.md（如需要）
- 更新使用指南（如需要）
- 更新 CHANGELOG.md

### 文档结构

```
docs/
├── usage-guide.md      # 使用指南
├── CHANGELOG.md        # 更新日志
└── API.md              # API 文档（待添加）
```

## 🔍 代码审查

所有提交都需要经过代码审查：

1. 确保代码质量
2. 检查测试覆盖
3. 验证文档完整性
4. 测试功能正确性

## 📋 检查清单

提交前请检查：

- [ ] 代码遵循 PEP 8 规范
- [ ] 添加了必要的测试
- [ ] 所有测试通过
- [ ] 更新了相关文档
- [ ] 提交信息清晰明确

## 🙏 感谢

感谢您的贡献！每一份贡献都让这个项目变得更好。

## 📧 联系

如有问题，请：
- 创建 Issue
- 发送邮件至 your.email@example.com

---

再次感谢您的支持！🎉