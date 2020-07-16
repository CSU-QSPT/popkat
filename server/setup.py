from setuptools import setup

setup(
    name="popkat_server",
    version="0.1",
    description="This package is the server component of the PoPKAT application",
    url="https://gitlab.com/csu-qspt/popkat-server",
    author="Brad Reisfeld",
    author_email="brad.reisfeld@colostate.edu",
    license="MIT",
    packages=["popkat_server"],
    install_requires=["rpyc"],
    python_requires=">=3.6",
    entry_points={"console_scripts": ["popkat_server=popkat_server.server:main"]},
)
