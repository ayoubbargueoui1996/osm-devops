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

import functools
import logging
import os
import sys

import yaml

from jinja2 import Environment, PackageLoader


class MetadataGenerator:
    LOGGER = logging.getLogger()
    ENV = Environment(loader=PackageLoader('generator.metadata', 'templates'))

    def __init__(self, metadata, license=None, options=None):
        """
        Creates the object to generate the metadata.yaml file from a template.

        Usage should be:

        1) Create the object.
        2) Run the generate method.

        :param metadata: metadata information about the charm being generated.
        :param license: information license to included in the charm being generated.
        :param options: options to override the normal flow.
        """
        self.path = os.getcwd()
        self.metadata = metadata
        self.license = license
        self.options = options

    def generate(self):
        """
        Generates the metadata.yaml using templates.
        """
        MetadataGenerator.LOGGER.info('Generating the metadata.yaml...')

        standard_metadata = self._read_metadata_yaml()
        self._update_metadata(standard_metadata)
        self._rename_metadata_yaml_as_backup()
        self._write_metadata_yaml()

        MetadataGenerator.LOGGER.info('Generated the metadata.yaml.')

    def get_metadata(self):
        """
        Gets the enhanced metadata.

        :return: the enhanced metadata dictionary.
        """
        return self.metadata

    def _read_metadata_yaml(self):
        """
        Reads the values from the old metadata.yaml and does a cleanup on undesired values.
        """
        MetadataGenerator.LOGGER.debug('Reading old metadata.yaml...')

        metadata_yaml_path = self.path + '/metadata.yaml'

        if not os.path.isfile(metadata_yaml_path):
            MetadataGenerator.LOGGER.error('metadata.yaml must be present. Must be run in the root of the charm')
            sys.exit(-1)

        with open(metadata_yaml_path, 'r') as f:
            metadata = yaml.load(f)

        if 'tags' in metadata.keys():
            del metadata['tags']
        if 'provides' in metadata.keys():
            del metadata['provides']
        if 'requires' in metadata.keys():
            del metadata['requires']
        if 'peers' in metadata.keys():
            del metadata['peers']

        MetadataGenerator.LOGGER.debug('Read old metadata.yaml.')

        return metadata

    def _update_metadata(self, metadata):
        """
        Update internal metadata before writing the new metadata.yaml.

        :param metadata: metadata values provided by the user.
        """
        MetadataGenerator.LOGGER.debug('Generating the Ansible Charm...')

        if 'name' in metadata:
            self.metadata['name'] = metadata['name']
            self.metadata['file'] = '%s.py' % metadata['name'].replace('-', '_')

        self.metadata['subordinate'] = False
        self.metadata['tags'] = ['misc', 'osm', 'vnf']
        self.metadata['series'] = ['xenial', 'trusty']

        MetadataGenerator.LOGGER.debug('Generating the Ansible Charm...')

    def _rename_metadata_yaml_as_backup(self):
        """
        Renames the metadata.yaml to metadata.yaml.bkp.*.
        Preserves the history of the charm for the user.
        """
        MetadataGenerator.LOGGER.debug('Renaming the metadata.yaml to .bkp.*...')

        metadata_yaml_path = self.path + '/metadata.yaml'

        ids = [int(f.split('.')[-1]) for f in os.listdir(self.path)
               if f.startswith('metadata.yaml.bkp')]

        id = 0
        if ids:
            id = functools.reduce(lambda x, y: x if (x > y) else y, ids)
            id += 1

        backup_metadata_yaml_path = self.path + ('/metadata.yaml.bkp.%02d' % id)
        os.rename(metadata_yaml_path, backup_metadata_yaml_path)

        MetadataGenerator.LOGGER.debug('Renamed the metadata.yaml to .bkp.%02d.', id)

    def _write_metadata_yaml(self):
        """
        Writes the enriched metadata to metadata.yaml.
        """
        MetadataGenerator.LOGGER.debug('Generating metadata.yaml...')

        metadata_yaml_path = self.path + '/metadata.yaml'
        metadata_yaml_template = MetadataGenerator.ENV.get_template('metadata.yaml.j2')

        with open(metadata_yaml_path, 'w') as f:
            f.write(metadata_yaml_template.render(metadata=self.metadata, license=self.license))

        MetadataGenerator.LOGGER.debug('Generated metadata.yaml.')
