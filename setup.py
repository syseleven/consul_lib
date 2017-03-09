import sys

from setuptools import setup, find_packages

if not sys.version_info >= (3, 5):
    sys.exit("This tool was developed on Python 3.5, please upgrade")

setup(
    name="consul_lib",
    url="http://www.syseleven.de",
    version="0.1.0.dev0",
    maintainer="Cloudstackers",
    maintainer_email="Cloudstackers <cloudstackers@syseleven.de>",
    packages=find_packages(),
    install_requires=[
        "python-consul",
        "requests",
    ],
)
