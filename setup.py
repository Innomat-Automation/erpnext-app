# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in innomat/__init__.py
from innomat import __version__ as version

setup(
	name='innomat',
	version=version,
	description='Innomat ERPNext applications',
	author='Innomat, Asprotec and libracore',
	author_email='info@libracore.com',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
