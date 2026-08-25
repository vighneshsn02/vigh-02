from setuptools import setup, find_packages

setup(
    name="vigh-02",
    version="2.0.0",
    description="VIGH-02 AI AGENT: Offline-First Autonomous Local & Cloud Coding Assistant",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "vigh_agent": [
            "web/static/*",
            "web/static/**/*"
        ]
    },
    install_requires=[
        "rich>=13.0.0",
        "prompt_toolkit>=3.0.0",
        "fastapi>=0.100.0",
        "uvicorn>=0.20.0",
        "requests>=2.28.0",
        "httpx>=0.24.0",
        "pydantic>=2.0.0"
    ],
    entry_points={
        "console_scripts": [
            "vigh-02=vigh_agent.cli:main",
            "vigh=vigh_agent.cli:main",
        ]
    },
    python_requires=">=3.8",
)
