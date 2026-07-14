#!/usr/bin/env python3
"""
Standard Review Skill - Setup Configuration
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip()]

setup(
    name="standard-review",
    version="1.1.0",
    author="surfy2024",
    author_email="13911085796@139.com",
    description="GB/T 1.1-2020 标准草稿自动化审查工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/surfy2024/standard-review",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Text Processing :: Markup",
        "Topic :: Office/Business :: Office Suites",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "standard-review=scripts.check_standard:main",
            "analyze-styles=scripts.analyze_styles:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)