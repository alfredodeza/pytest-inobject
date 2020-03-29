import re

module_file = open("pytest_inobject/__init__.py").read()
metadata = dict(re.findall(r"__([a-z]+)__\s*=\s*['\"]([^'\"]*)['\"]", module_file))
long_description = open('README.rst').read()
install_requires = []

from setuptools import setup


setup(
    name = 'pytest_inobject',
    description = 'Pytest plugin to enhance object assertions',
    packages = ['pytest_inobject'],
    author = 'Alfredo Deza',
    author_email = 'contact@deza.pe',
    version = metadata['version'],
    url = 'http://github.com/alfredodeza/pytest_inobject',
    license = "MIT",
    zip_safe = False,
    keywords = "pytest, hook, objects, assert, plugin",
    long_description = long_description,
    # the following makes a plugin available to pytest
    entry_points = {
        'pytest11': [
            'inobject = pytest_inobject.plugin',
        ]
    },
    classifiers = [
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Utilities',
        'Framework :: Pytest',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
    ]
)
