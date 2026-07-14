# GitHub 发布指南

本指南将帮助您将 Standard Review Skill 发布到 GitHub。

## 📋 发布前准备

### 1. 准备 GitHub 账号

- 注册 GitHub 账号：https://github.com/signup
- 配置 SSH 密钥（推荐）：https://docs.github.com/en/authentication/connecting-to-github-with-ssh

### 2. 安装 Git

```bash
# Windows
# 下载并安装 Git：https://git-scm.com/download/win

# macOS
brew install git

# Linux
sudo apt-get install git
```

### 3. 配置 Git

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

---

## 📦 准备发布文件

### 1. 检查文件结构

确保 `standard-review-github` 目录包含以下文件：

```
standard-review-github/
├── README.md                   ✅ 项目说明
├── LICENSE                     ✅ 许可证
├── requirements.txt            ✅ Python 依赖
├── setup.py                    ✅ 安装配置
├── .gitignore                  ✅ Git 忽略文件
├── CONTRIBUTING.md             ✅ 贡献指南
├── scripts/                    ✅ 核心脚本
│   ├── check_standard.py
│   └── analyze_styles.py
├── references/                 ✅ 规则文件
│   ├── structure-rules.md
│   ├── format-rules.md
│   ├── terminology-rules.md
│   ├── common-errors.md
│   └── usage-guide.md
└── docs/                       ✅ 文档
    └── CHANGELOG.md
```

### 2. 更新文件内容

**README.md**：
- 更新作者信息
- 更新 GitHub 仓库地址
- 更新联系方式

**LICENSE**：
- 更新版权信息
- 更新年份和作者名称

**setup.py**：
- 更新作者信息
- 更新邮箱地址
- 更新 GitHub 仓库地址

---

## 🚀 发布到 GitHub

### 步骤 1：创建 GitHub 仓库

1. 登录 GitHub
2. 点击右上角的 "+" → "New repository"
3. 填写仓库信息：
   - **Repository name**: `standard-review`
   - **Description**: `GB/T 1.1-2020 标准草稿自动化审查工具`
   - **Public** 或 **Private**：选择公开或私有
   - **不要**勾选 "Add a README file"（我们已经有了）
   - **不要**勾选 "Add .gitignore"（我们已经有了）
   - **License**: 选择 "MIT License"（我们已经有了）
4. 点击 "Create repository"

### 步骤 2：初始化本地 Git 仓库

```bash
# 进入项目目录
cd "c:/学习文件/标准/标准审查技能/standard-review-github"

# 初始化 Git 仓库
git init

# 添加所有文件
git add .

# 提交更改
git commit -m "Initial commit: Standard Review Skill v1.1.0"
```

### 步骤 3：连接到 GitHub 仓库

```bash
# 添加远程仓库（替换 yourusername）
git remote add origin https://github.com/yourusername/standard-review.git

# 或使用 SSH（推荐）
git remote add origin git@github.com:yourusername/standard-review.git
```

### 步骤 4：推送到 GitHub

```bash
# 推送到主分支
git branch -M main
git push -u origin main
```

---

## 📝 发布后设置

### 1. 添加仓库描述

1. 进入仓库页面
2. 点击 "About" 旁边的 ⚙️ 图标
3. 添加描述：`GB/T 1.1-2020 标准草稿自动化审查工具`
4. 添加网站（如有）
5. 添加主题标签：`python`, `standard`, `review`, `gb-t-1.1`, `docx`

### 2. 创建 Release

1. 点击 "Releases" → "Create a new release"
2. 填写信息：
   - **Tag version**: `v1.1.0`
   - **Release title**: `Standard Review Skill v1.1.0`
   - **Description**:
     ```markdown
     ## 新增功能
     - ✅ 样式分析功能
     - ✅ 智能标题识别算法
     - ✅ 上下文信息输出
     
     ## 改进
     - ✅ 优化标题识别逻辑，误报率降低 97%
     - ✅ 改进错误提示信息
     
     ## 修复
     - 🐛 修复将长段落误判为标题的问题
     - 🐛 修复样式识别不准确的问题
     ```
3. 点击 "Publish release"

### 3. 添加徽章

在 README.md 顶部添加徽章：

```markdown
[![GitHub release](https://img.shields.io/github/v/release/yourusername/standard-review.svg)](https://github.com/yourusername/standard-review/releases)
[![GitHub stars](https://img.shields.io/github/stars/yourusername/standard-review.svg)](https://github.com/yourusername/standard-review/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/yourusername/standard-review.svg)](https://github.com/yourusername/standard-review/issues)
[![GitHub license](https://img.shields.io/github/license/yourusername/standard-review.svg)](https://github.com/yourusername/standard-review/blob/main/LICENSE)
```

---

## 🔄 后续维护

### 更新代码

```bash
# 修改文件后
git add .
git commit -m "Update: your update description"
git push
```

### 创建新版本

```bash
# 更新版本号
# 1. 更新 setup.py 中的 version
# 2. 更新 CHANGELOG.md

# 提交更改
git add .
git commit -m "Release v1.2.0"

# 创建标签
git tag -a v1.2.0 -m "Release v1.2.0"

# 推送标签
git push origin v1.2.0

# 在 GitHub 上创建 Release
```

---

## 📢 推广建议

### 1. 社交媒体

- Twitter/X
- LinkedIn
- 微博
- 知乎

### 2. 技术社区

- GitHub Trending
- Hacker News
- Reddit r/Python
- V2EX

### 3. 文档站点

- Read the Docs
- GitHub Pages
- GitBook

---

## 🎯 最佳实践

### 1. 版本管理

- 遵循语义化版本规范
- 及时更新 CHANGELOG.md
- 为每个版本创建 Release

### 2. 文档维护

- 保持 README.md 更新
- 提供清晰的使用示例
- 及时回复 Issues

### 3. 社区互动

- 欢迎 Pull Requests
- 及时处理 Issues
- 感谢贡献者

---

## ❓ 常见问题

### Q1: 如何处理敏感信息？

**A**: 
- 不要提交包含个人信息的文件
- 使用 `.gitignore` 排除敏感文件
- 使用环境变量存储配置

### Q2: 如何撤销错误的提交？

**A**:
```bash
# 撤销最后一次提交（保留更改）
git reset --soft HEAD~1

# 撤销最后一次提交（丢弃更改）
git reset --hard HEAD~1

# 已推送到远程，创建反向提交
git revert <commit-hash>
```

### Q3: 如何处理合并冲突？

**A**:
```bash
# 拉取最新更改
git pull origin main

# 解决冲突后
git add .
git commit -m "Merge: resolve conflicts"
git push
```

---

## 📚 参考资源

- [GitHub 文档](https://docs.github.com/)
- [Git 文档](https://git-scm.com/doc)
- [语义化版本](https://semver.org/lang/zh-CN/)
- [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)

---

**祝您发布顺利！** 🎉