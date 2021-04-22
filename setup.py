#!/usr/bin/env python

try:
    from setuptools import setup, find_packages
except ImportError:
    raise RuntimeError('setuptools is required')

DESCRIPTION = ('pvops is a python library for the analysis of ' +
               'field collected operational data for photovoltaic systems.')

LONG_DESCRIPTION = """
pvops is a python package for PV operators & researchers. It is
a collection of functions for working with text-based data
from photovoltaic power systems. The library includes functions for
processing text data as well as fusion of the text information with
time series data for visualization of contextual details for data
analysis. 

Documentation: https://pvops.readthedocs.io/en/latest/index.html

Source code: https://github.com/tgunda/pvops

"""

DISTNAME = 'pvops'
MAINTAINER = "Thushara Gunda"
MAINTAINER_EMAIL = 'tgunda@sandia.gov'
LICENSE = 'Revised BSD'
URL = 'https://github.com/tgunda/pvops'

TESTS_REQUIRE = [
    'pytest',
]

INSTALL_REQUIRES = [
    'numpy >= 1.15.0',
    'pandas >= 0.23.0',
    'scipy >= 1.2.0',
    'scikit-learn',
    'nltk',
    'datefinder',
    'matplotlib',
    'seaborn',
    'plotly',
    'gensim',
    'networkx',
    'pvlib',
    'pvanalytics',
    'timezonefinder'
]

DOCS_REQUIRE = [
    'sphinx == 2.2.0'
]

EXTRAS_REQUIRE = {
    'optional': ['ruptures'],
    'test': TESTS_REQUIRE,
    'doc': DOCS_REQUIRE
}

EXTRAS_REQUIRE['all'] = sorted(set(sum(EXTRAS_REQUIRE.values(), [])))

SETUP_REQUIRES = ['setuptools_scm']

CLASSIFIERS = [
    'Development Status :: 2 - Pre-Alpha',
    'Operating System :: OS Independent',
    'Intended Audience :: Science/Research',
    'Programming Language :: Python :: 3',
    'Topic :: Scientific/Engineering'
]

PACKAGES = find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"])

setup(
    name=DISTNAME,
    use_scm_version=True,
    packages=PACKAGES,
    install_requires=INSTALL_REQUIRES,
    extras_require=EXTRAS_REQUIRE,
    tests_require=TESTS_REQUIRE,
    setup_requires=SETUP_REQUIRES,
    ext_modules=[],
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    maintainer=MAINTAINER,
    maintainer_email=MAINTAINER_EMAIL,
    license=LICENSE,
    classifiers=CLASSIFIERS,
    url=URL
)
