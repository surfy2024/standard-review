#!/usr/bin/env python3
"""
GitHub 快速发布脚本

功能：
- 检查必要文件是否存在
- 初始化 Git 仓库
- 提交所有文件
- 提供发布指导

使用方法：
    python publish.py
"""

import os
import sys
from pathlib import Path


class GitHubPublisher:
    """GitHub 发布助手"""
    
    def __init__(self):
        self.project_dir = Path(__file__).parent
        self.required_files = [
            "README.md",
            "LICENSE",
            "requirements.txt",
            "setup.py",
            ".gitignore",
            "CONTRIBUTING.md",
            "scripts/check_standard.py",
            "scripts/analyze_styles.py",
            "references/structure-rules.md",
            "references/format-rules.md",
            "references/terminology-rules.md",
            "references/common-errors.md",
            "docs/CHANGELOG.md"
        ]
    
    def check_files(self) -> bool:
        """检查必要文件是否存在"""
        print("\n=== 检查必要文件 ===\n")
        
        all_exist = True
        for file in self.required_files:
            file_path = self.project_dir / file
            if file_path.exists():
                print(f"✅ {file}")
            else:
                print(f"❌ {file} - 不存在")
                all_exist = False
        
        return all_exist
    
    def init_git(self) -> None:
        """初始化 Git 仓库"""
        print("\n=== 初始化 Git 仓库 ===\n")
        
        os.chdir(self.project_dir)
        
        # 检查是否已初始化
        if (self.project_dir / ".git").exists():
            print("✅ Git 仓库已存在")
            return
        
        # 初始化
        os.system("git init")
        print("✅ Git 仓库初始化完成")
    
    def add_files(self) -> None:
        """添加所有文件"""
        print("\n=== 添加文件到 Git ===\n")
        
        os.chdir(self.project_dir)
        os.system("git add .")
        print("✅ 所有文件已添加")
    
    def commit(self, message: str = "Initial commit: Standard Review Skill v1.1.0") -> None:
        """提交更改"""
        print("\n=== 提交更改 ===\n")
        
        os.chdir(self.project_dir)
        os.system(f'git commit -m "{message}"')
        print("✅ 更改已提交")
    
    def show_guide(self) -> None:
        """显示发布指南"""
        guide = """
╔══════════════════════════════════════════════════════════════╗
║                    GitHub 发布指南                            ║
╚══════════════════════════════════════════════════════════════╝

接下来，请按照以下步骤完成发布：

1️⃣  创建 GitHub 仓库
   - 登录 GitHub: https://github.com
   - 点击 "+" → "New repository"
   - 仓库名称: standard-review
   - 描述: GB/T 1.1-2020 标准草稿自动化审查工具
   - 选择 Public 或 Private
   - 不要勾选 "Add a README file"
   - 点击 "Create repository"

2️⃣  连接远程仓库
   git remote add origin https://github.com/YOUR_USERNAME/standard-review.git
   git branch -M main
   git push -u origin main

   或使用 SSH（推荐）：
   git remote add origin git@github.com:YOUR_USERNAME/standard-review.git
   git branch -M main
   git push -u origin main

3️⃣  创建 Release
   - 进入仓库页面
   - 点击 "Releases" → "Create a new release"
   - Tag version: v1.1.0
   - Release title: Standard Review Skill v1.1.0
   - 添加发布说明
   - 点击 "Publish release"

4️⃣  更新 README.md
   - 替换 yourusername 为你的 GitHub 用户名
   - 替换 your.email@example.com 为你的邮箱
   - 添加徽章和截图

📚 详细指南
   查看 docs/GITHUB_PUBLISH_GUIDE.md

🎉 发布成功后
   - 在社交媒体分享你的项目
   - 添加主题标签: python, standard, review
   - 邀请朋友 Star 你的项目

祝发布顺利！
"""
        print(guide)
    
    def run(self) -> None:
        """运行发布流程"""
        print("\n" + "="*60)
        print("Standard Review Skill - GitHub 发布助手")
        print("="*60)
        
        # 检查文件
        if not self.check_files():
            print("\n❌ 缺少必要文件，请先准备完整")
            return
        
        # 初始化 Git
        self.init_git()
        
        # 添加文件
        self.add_files()
        
        # 提交
        self.commit()
        
        # 显示指南
        self.show_guide()


def main():
    publisher = GitHubPublisher()
    publisher.run()


if __name__ == "__main__":
    main()