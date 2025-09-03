from setuptools import setup, find_packages

setup(
    name="masense-ai-agent",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'langchain',
        'python-dotenv',
        'boto3',
    ],
)
