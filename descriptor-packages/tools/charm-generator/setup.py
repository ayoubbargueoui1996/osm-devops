# Copyright 2019 Whitestack, LLC
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# For those usages not covered by the Apache License, Version 2.0 please
# contact: esousa@whitestack.com or glavado@whitestack.com
##

import re
import setuptools

print(setuptools.find_packages())

version = re.search(
    r'^__version__\s*=\s*["\'](.*)["\']',
    open('generator/generator.py').read(),
    re.MULTILINE).group(1)

with open('README.md', 'r') as f:
    long_description = f.read()

setuptools.setup(
    name='osm-charm-generator',
    packages=setuptools.find_packages(),
    entry_points={
        "console_scripts": ['osm-charm-generator = generator.generator:main']
    },
    version=version,
    author='Eduardo Sousa',
    author_email='esousa@whitestack.com',
    description='OSM Charm Generator using Ansible',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://osm.etsi.org',
    install_requires=[
        'Jinja2>=2.10'
    ],
    package_data={
        'generator.actions': ['templates/*.j2'],
        'generator.ansible-charm': ['templates/*.j2'],
        'generator.metadata': ['templates/*.j2'],
    },
    include_package_data=True,
    classifiers=[
        'Programming Language :: Python :: 3 :: Only',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Environment :: Console',
        'Intended Audience :: Telecommunications Industry',
        'Natural Language :: English',
        'Topic :: Software Development :: Code Generators'
    ]
)
