"""Setup configuration for Millionaire 2026"""

from setuptools import setup, find_packages

setup(
    name="millionaire-2026",
    version="0.1.0",
    description="Quantitative crypto trading system for Bitcoin and Ethereum",
    author="Trading Team",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "pandas>=1.5.0",
        "numpy>=1.24.0",
        "requests>=2.28.0",
        "python-dotenv>=0.20.0",
    ],
    extras_require={
        "dev": ["pytest>=7.0.0", "black>=22.0.0", "flake8>=4.0.0"],
    },
)
