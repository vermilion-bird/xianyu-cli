from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="xianyu-cli",
    version="0.1.0",
    author="CodeNinja",
    author_email="coderxiu@qq.com",
    description="闲鱼消息管理 CLI 工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/shaxiu/XianyuAutoAgent",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "click>=8.0.0",
        "requests>=2.28.0",
        "python-dotenv>=0.19.0",
        "websockets>=10.0.0",
        "loguru>=0.6.0",
    ],
    entry_points={
        "console_scripts": [
            "xianyu=xianyu_cli.cli:cli",
        ],
    },
    include_package_data=True,
    package_data={
        "xianyu_cli": ["py.typed"],
    },
)