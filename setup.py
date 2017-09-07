#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'aiohttp',
    'Click>=6.0',
    'APScheduler',
    'click-log',
    'hbmqtt',
    'aiolifxc>=0.5.2',
    'PyYAML',
    'python-dateutil',
]

setup_requirements = [
    'pytest-runner',
]

test_requirements = [
    'pytest',
]

setup(
    name='robotica',
    version='0.1.27',
    description="Robotic maid to scare innocent children",
    long_description=readme + '\n\n' + history,
    author="Brian May",
    author_email='brian@linuxpenguins.xyz',
    url='https://github.com/brianmay/robotica',
    packages=find_packages(include=['robotica']),
    entry_points={
        'console_scripts': [
            'robotica=robotica.cli:main'
        ]
    },
    include_package_data=True,
    install_requires=requirements,
    license="GNU General Public License v3",
    zip_safe=False,
    keywords='robotica',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    setup_requires=setup_requirements,
)
