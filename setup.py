from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="DrafterBench",
    version="0.1.0",
    description="A benchmark evaluates LLMs' performance in automating drawing revision tasks.",
    author="anonymous",
    author_email="266373004+anonymous733882@users.noreply.github.com",
    packages=find_packages(),
    python_requires=">=3.11,<3.12",
    install_requires=requirements,
)
