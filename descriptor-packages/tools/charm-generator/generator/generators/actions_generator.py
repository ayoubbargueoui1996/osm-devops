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
import stat

from jinja2 import Environment, PackageLoader


class ActionsGenerator:
    LOGGER = logging.getLogger()
    ENV = Environment(loader=PackageLoader('generator.actions', 'templates'))

    def __init__(self, metadata, actions, license=None, options=None):
        """
        Creates the object to generate the actions folder, actions files and actions.yaml.

        Usage should be:

        1) Create the object.
        2) Run the generate method.

        :param metadata: metadata information about the charm being generated.
        :param actions: actions to be included in the charm.
        :param license: information license to included in the charm being generated.
        :param options: options to override the normal flow.
        """
        self.path = os.getcwd()
        self.metadata = metadata
        self.actions = actions
        self.license = license
        self.options = options

    def generate(self):
        """
        Generates the actions folder, actions files and actions.yaml.
        """
        ActionsGenerator.LOGGER.info('Generating the actions...')

        self._create_actions_folder()

        for action in self.actions:
            self._generate_action_file(action)

        self._generate_actions_yaml_file()

        ActionsGenerator.LOGGER.info('Generated the actions.')

    def _create_actions_folder(self):
        """
        Creates the actions folder, where all the action files are placed.
        These files are the entry point for the execution of the actions.
        """
        ActionsGenerator.LOGGER.debug('Creating the actions folder...')

        actions_path = self.path + '/actions'

        if not os.path.isdir(actions_path):
            os.mkdir(actions_path)
        else:
            ActionsGenerator.LOGGER.warning('Actions folder already exists.')
            return

        ActionsGenerator.LOGGER.debug('Created actions folder.')

    def _generate_action_file(self, action):
        """
        Generates the action file to act as entry point for a specific action.

        Note: the action file is made executable during this function.

        :param action: dictionary with information about the action
        """
        ActionsGenerator.LOGGER.debug('Creating action file: %s...', action['action_name'])

        playbook_path = self.path + ('/actions/%s' % action['action_name'])
        action_file_template = ActionsGenerator.ENV.get_template('action.j2')

        with open(playbook_path, "w") as f:
            f.write(action_file_template.render(license=self.license))
            mode = os.fstat(f.fileno()).st_mode
            mode |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            os.fchmod(f.fileno(), stat.S_IMODE(mode))

        ActionsGenerator.LOGGER.debug('Created action file: %s.', action['action_name'])

    def _generate_actions_yaml_file(self):
        """
        Generates the actions.yaml file from a template.
        It takes all the playbook information and fills in the templates.

        Note: renames the old actions.yaml file with a .bkp extension, so the history is preserved.
        """
        ActionsGenerator.LOGGER.debug('Creating actions.yaml...')

        actions_yaml_path = self.path + '/actions.yaml'
        actions_template = ActionsGenerator.ENV.get_template('actions.yaml.j2')

        if os.path.isfile(actions_yaml_path):
            ids = [int(f.split('.')[-1]) for f in os.listdir(self.path) if f.startswith('actions.yaml.bkp')]

            id = 0
            if ids:
                id = functools.reduce(lambda x, y: x if (x > y) else y, ids)
                id += 1

            backup_actions_yaml_path = self.path + ('/actions.yaml.bkp.%02d' % id)
            os.rename(actions_yaml_path, backup_actions_yaml_path)

        with open(actions_yaml_path, 'w') as f:
            f.write(actions_template.render(actions=self.actions, license=self.license))

        ActionsGenerator.LOGGER.debug('Created actions.yaml.')
