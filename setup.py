from setuptools import setup, find_packages

setup(
    name="memoria-ai",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "neo4j>=5.18.0",
        "pydantic>=2.6.0",
        "instructor>=1.0.0",
        "sentence-transformers>=2.5.0",
        "python-dotenv>=1.0.0",
        "click>=8.1.0",
        "numpy>=1.24.0",
    ],
    entry_points={
        "console_scripts": [
            "memoria=memoria.cli:cli",
        ],
    },
)
