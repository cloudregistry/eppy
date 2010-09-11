from setuptools import setup, find_packages

from eppy import __version__


setup(
    name = "EPPy",
    version = __version__,
    author = "Wil Tan",
    author_email = "wil@cloudregistry.net",
    description = "EPP Client for Python",
    license = "MIT/X",
    install_requires = [],
    packages = find_packages(),
)
