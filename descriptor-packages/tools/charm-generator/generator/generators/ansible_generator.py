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

from jinja2 import Environment, PackageLoader

from generator.generators.actions_generator import ActionsGenerator
from generator.generators.metadata_generator import MetadataGenerator


class AnsibleGenerator:
    LOGGER = logging.getLogger()
    ENV = Environment(loader=PackageLoader('generator.ansible-charm', 'templates'))

    def __init__(self, metadata, license=None, options=None):
        """
        Creates the object to generate the ansible charm from templates.

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
        self.playbooks = AnsibleGenerator._fetch_all_playbooks(self.path)

        playbooks_name = [playbook['file'] for playbook in self.playbooks]
        AnsibleGenerator.LOGGER.debug('Playbooks found: %s', playbooks_name)

        self.metadata_generator = MetadataGenerator(metadata=self.metadata, license=self.license, options=self.options)
        self.actions_generator = ActionsGenerator(metadata=self.metadata, actions=self.playbooks, license=self.license,
                                                  options=self.options)

    def generate(self):
        """
        Generates the Ansible Charm using templates.
        """
        AnsibleGenerator.LOGGER.info('Generating the Ansible Charm...')

        # Generating metadata.yaml
        self.metadata_generator.generate()
        self.metadata = self.metadata_generator.get_metadata()

        # Generating actions
        self.actions_generator.generate()

        self._generate_ansible_lib()
        self._generate_layer_yaml_file()
        self._generate_reactive_file()

        AnsibleGenerator.LOGGER.info('Generated the Ansible Charm.')

    @staticmethod
    def _fetch_all_playbooks(path):
        """
        Walks over the playbooks directory, fetches the playbook's name.
        It takes the file name and normalizes it to be used in the ansible charm.

        :param path: path of the root of the charm.
        :return: a list of dictionaries with the information about the playbooks.
        """
        playbooks_path = path + '/playbooks'

        if os.path.isdir(playbooks_path) and len(os.listdir(playbooks_path)) != 0:
            filenames = os.listdir(playbooks_path)

            result = []
            for file in filenames:
                info = {
                    'action_name': file.replace('_', '-').replace('.yaml', ''),
                    'function_name': file.replace('-', '_').replace('.yaml', ''),
                    'file': file
                }
                result.append(info)

            return result
        else:
            AnsibleGenerator.LOGGER.error('Playbooks directory should exist and be populated.')
            sys.exit(-1)

    def _generate_ansible_lib(self):
        """
        Generates the ansible lib file from a template.
        """
        AnsibleGenerator.LOGGER.debug('Creating ansible.py lib...')

        lib_folder_path = self.path + '/lib/charms'
        ansible_lib_path = lib_folder_path + '/libansible.py'

        if not os.path.isdir(lib_folder_path):
            os.makedirs(lib_folder_path)

        ansible_lib_template = AnsibleGenerator.ENV.get_template('ansible_lib.py.j2')

        with open(ansible_lib_path, 'w') as f:
            f.write(ansible_lib_template.render(license=self.license))

        AnsibleGenerator.LOGGER.debug('Created anisble.py lib.')

    def _generate_layer_yaml_file(self):
        """
        Generates the layer.yaml file from a template.

        Note: disables the venv environment.
        """
        AnsibleGenerator.LOGGER.debug('Creating layer.yaml...')

        layer_yaml_path = self.path + '/layer.yaml'

        layers = [{
            'name': 'basic',
            'options': [{
                'name': 'use_venv',
                'value': 'false'
            }]}, {
            'name': 'ansible-base'
        }, {
            'name': 'vnfproxy'
        }]

        layer_template = AnsibleGenerator.ENV.get_template('layer.yaml.j2')

        with open(layer_yaml_path, 'w') as f:
            f.write(layer_template.render(layers=layers, license=self.license))

        AnsibleGenerator.LOGGER.debug('Created layer.yaml.')

    def _generate_reactive_file(self):
        """
        Generates the Ansible reactive file from a template.
        It takes all the playbook information and fills in the templates.

        Note: renames the old charm file with a .bkp extension, so the history is preserved.
        """
        AnsibleGenerator.LOGGER.debug('Creating ansible charm: %s...', self.metadata['file'])

        reactive_folder_path = self.path + '/reactive'
        charm_file_path = reactive_folder_path + ('/%s' % self.metadata['file'])
        ansible_charm_template = AnsibleGenerator.ENV.get_template('ansible_charm.py.j2')

        ids = [int(f.split('.')[-1]) for f in os.listdir(reactive_folder_path)
               if f.startswith('%s.bkp' % self.metadata['file'])]

        id = 0
        if ids:
            id = functools.reduce(lambda x, y: x if (x > y) else y, ids)
            id += 1

        backup_charm_file_path = reactive_folder_path + ('/%s.bkp.%02d' % (self.metadata['file'], id))
        os.rename(charm_file_path, backup_charm_file_path)

        with open(charm_file_path, 'w') as f:
            f.write(ansible_charm_template.render(charm_name=self.metadata['name'], playbooks=self.playbooks,
                                                  license=self.license))

        AnsibleGenerator.LOGGER.debug('Created ansible charm: %s.', self.metadata['file'])
