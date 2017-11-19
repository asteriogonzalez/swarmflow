#!/usr/bin/env python
"""swarmflow pipy install script"""

import os
from setuptools import setup


def read(fname):
    "Read a file located in package"
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

VERSION = '0.1.0'
setup(
    name='swarmflow',
    license='MIT',
    # packages=['mypkg'],
    # package_dir={'mypkg': 'src/mypkg'},
    # package_data={'mypkg': ['data/*.dat']},
    version=VERSION,
    description="Decentralized agents executing non-coordinated workflows",
    author='Asterio Gonzalez',
    author_email='asterio.gonzalez@gmail.com',
    url='https://github.com/asteriogonzalez/swarmflow',
    # download_url = \
    # 'https://github.com/asteriogonzalez/swarmflow/archive/%s.tar.gz' % \
    # VERSION,
    keywords=['swarm', 'decentralized', 'udp'],

    # https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Framework :: AsyncIO',
        'Intended Audience :: Developers',
        'License :: Freely Distributable',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: System :: Distributed Computing',
    ],

    long_description=read("README.md"),
    py_modules=['swarmflow'],
    entry_points={'pytest11': ['swarm = swarmflow']},
    install_requires=['ifcfg', 'netaddr', 'numpy'],

    # https://stackoverflow.com/a/814118/6924622
    # data_files parameter is a hack to get your setup.py into the distribution
    # script_name = './build/setup.py',
    # data_files = ['./build/setup.py']

    # data_files=[
    # ('bitmaps', ['bm/b1.gif', 'bm/b2.gif']),
    # ('config', ['cfg/data.cfg']),
    # ('/etc/init.d', ['init-script'])]
)
