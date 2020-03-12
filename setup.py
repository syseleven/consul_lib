import sys

from setuptools import setup, find_packages

if not sys.version_info >= (3, 5):
    sys.exit("This tool was developed on Python 3.5, please upgrade")

setup(
    name="consul_lib",
    version="0.1.1.dev",
    maintainer="Syseleven Cloudstackers",
    maintainer_email="cloudstackers@syseleven.de",
    url="https://github.com/syseleven/consul_lib",
    packages=find_packages(),
    install_requires=[
        "python-consul",
        "requests",
    ],
)
