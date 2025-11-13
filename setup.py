from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="grokputer",
    version="1.7.0",
    author="Grokputer Team",
    author_email="team@grokputer.ai",
    description="Autonomous AI development platform with multi-modal capabilities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sst/opencode",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "asyncio",
        "click",
        "rich",
        "redis",
        "requests",
        "psutil",
        "streamlit",
        "GPUtil",
        "docker",
        "json",
        "pathlib",
        "contextlib",
        "datetime",
        "subprocess",
        "re",
        "random",
        "logging",
    ],
    extras_require={
        "dev": [
            "flake8",
            "black",
            "pytest",
        ],
    },
    entry_points={
        "console_scripts": [
            "grokputer=main:main",
        ],
    },
)
