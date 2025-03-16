"""
Setup script for SkillLab
"""

from setuptools import setup, find_packages

setup(
    name="skilllab",
    version="0.1.0",
    description="Tool for extracting, structuring, and training a model on resume data",
    author="SkillBase Team",
    packages=find_packages(),
    install_requires=[
        # Core dependencies
        "torch>=1.9.0",
        "transformers>=4.15.0",
        "paddlepaddle",
        "paddleocr",
        "pdf2image>=1.16.0",
        "pillow>=8.3.1",
        "pynvml>=11.0.0",
        "requests>=2.26.0",
        "tqdm>=4.62.2",
        "numpy>=1.21.2",
        "nltk>=3.6.3",
        "protobuf<4.0.0",
        
        # Donut dependencies
        "sentencepiece",
        "python-Levenshtein",
        "albumentations",
        
        # Monitoring dependencies
        "psutil",
        "rich",
        "blessed",
        
        # Review system dependencies
        "streamlit>=1.22.0",
        "matplotlib",
        "pandas",
        "plotly",
        "watchdog",
    ],
    python_requires=">=3.8",
    entry_points={
        'console_scripts': [
            'skilllab=cli:main',
            'sl=cli:main',
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)