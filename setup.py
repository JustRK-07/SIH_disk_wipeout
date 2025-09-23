"""
Setup script for Disk Wipeout application
"""

from setuptools import setup, find_packages
import os

# Read README file
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="disk-wipeout",
    version="1.0.0",
    author="Disk Wipeout Team",
    author_email="contact@diskwipeout.com",
    description="Cross-platform secure data erasure tool",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/diskwipeout/disk-wipeout",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Security",
        "Topic :: System :: Systems Administration",
    ],
    python_requires=">=3.7",
    install_requires=read_requirements(),
    entry_points={
        "console_scripts": [
            "disk-wipeout=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt"],
    },
    keywords="disk wipe, data erasure, security, cross-platform, windows, linux, android",
    project_urls={
        "Bug Reports": "https://github.com/diskwipeout/disk-wipeout/issues",
        "Source": "https://github.com/diskwipeout/disk-wipeout",
        "Documentation": "https://github.com/diskwipeout/disk-wipeout/wiki",
    },
)
