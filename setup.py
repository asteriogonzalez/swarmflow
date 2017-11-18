#!/usr/bin/env python

import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

VERSION = '0.1.0'
setup(
    name='swarmflow',
    license='MIT',
    # packages=['swarmflow'],
    version=VERSION,
    description="Decentralized agents that execute workflows in a non-coordinated way",
    author='Asterio Gonzalez',
    author_email='asterio.gonzalez@gmail.com',
    url='https://github.com/asteriogonzalez/swarmflow',
    # download_url = 'https://github.com/asteriogonzalez/swarmflow/archive/%s.tar.gz' % VERSION,
    keywords = ['swarm', 'decentralized', 'udp'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Topic :: Software Development',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
    ],

    long_description=read("README.md"),
    py_modules=['swarmflow'],
    entry_points={'pytest11': ['swarm = swarmflow']},
    install_requires=[]
)
