from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="foundry-meeting-audiorecording-processor",
    version="0.1.0",
    author="Jonathan Dhaene",
    description="Process meeting audio files with Azure services for transcription and content understanding",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jonathandhaene/foundry-meeting-audiorecording-processor",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.10",
    install_requires=[
        "azure-cognitiveservices-speech>=1.38.0",
        "azure-ai-textanalytics>=5.3.0",
        "azure-storage-blob>=12.19.0",
        "azure-functions>=1.18.0",
        "pydub>=0.25.1",
        "python-dotenv>=1.0.0",
        "pyyaml>=6.0.1",
    ],
    extras_require={
        "dev": [
            "pytest>=8.2.0",
            "pytest-cov>=5.0.0",
            "pytest-asyncio>=0.23.6",
            "pytest-mock>=3.14.0",
            "mypy>=1.10.0",
            "black>=24.4.2",
            "flake8>=7.0.0",
        ],
    },
)
