import sys
from setuptools import setup, find_packages

from eppy import __version__

install_requires = ['six', 'future']
if sys.version_info < (3,2):
    install_requires.append('backports.ssl_match_hostname')

setup(
    name = "EPP",
    version = __version__,
    author = "Wil Tan",
    author_email = "wil@cloudregistry.net",
    description = "EPP Client for Python",
    license = "MIT/X",
    install_requires = install_requires,
    packages = ['eppy']
)
