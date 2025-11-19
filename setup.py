"""Setup configuration for RDBMS to Graph Migration System."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="rdbms-to-graph-migration",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A comprehensive system for migrating relational databases to Neo4j property graph databases",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/rdbms-to-graph-migration",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Database",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "neo4j>=5.14.0",
        "PyYAML>=6.0.1",
        "click>=8.1.7",
        "mysql-connector-python>=8.2.0",
        "psycopg2-binary>=2.9.9",
        "pyodbc>=5.0.1",
        "pandas>=2.1.4",
        "numpy>=1.26.2",
        "tqdm>=4.66.1",
        "colorlog>=6.8.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
            "black>=23.12.1",
            "flake8>=6.1.0",
            "mypy>=1.7.1",
        ],
    },
    entry_points={
        "console_scripts": [
            "migrate-db=src.cli:cli",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yml", "*.yaml"],
    },
)
