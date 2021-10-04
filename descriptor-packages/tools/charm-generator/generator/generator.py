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

__version__ = '1.0.0'

import argparse
import logging
import sys

from datetime import datetime

from .generators.ansible_generator import AnsibleGenerator


def configure_logger(args):
    global logger
    logger = logging.getLogger()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)

    if args.verbose:
        handler.setLevel(logging.DEBUG)
    else:
        handler.setLevel(logging.INFO)

    formatter = logging.Formatter('[%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def verify_environment(args):
    pass


def input_processing():
    parser = argparse.ArgumentParser(description='Charm generator for OSM VNFs')

    # Setting logger from INFO to DEBUG
    parser.add_argument('-v', '--verbose', required=False, action='store_true',
                        help='increase output verbosity')

    # Backend selection
    backend_parser = parser.add_mutually_exclusive_group(required=True)

    backend_parser.add_argument('--ansible', action='store_true',
                                help='generate an Ansible charm')
    backend_parser.add_argument('--http', action='store_true',
                                help='generate a HTTP charm')
    backend_parser.add_argument('--sol002', action='store_true',
                                help='generate a SOL002 charm')
    backend_parser.add_argument('--scripts', action='store_true',
                                help='generate a Scripts charm')

    # Metadata inputs
    metadata_parser = parser.add_argument_group('metadata')

    metadata_parser.add_argument('--summary', required=False, action='store',
                                 help='summary to be included in the metadata.yaml')
    metadata_parser.add_argument('--maintainer', required=False, action='store',
                                 help='maintainer information to be included in the metadata.yaml')
    metadata_parser.add_argument('--description', required=False, action='store',
                                 help='description to be included in the metadata.yaml')

    # License header inputs
    license_header_group = parser.add_argument_group('license_header')

    license_header_group.add_argument('--company', required=False, action='store',
                                      help='company name to be included in the license headers')
    license_header_group.add_argument('--email', required=False, action='store',
                                      help='email to be included in the license headers')

    return parser.parse_args()


def process_args(args):
    # Metadata information for metadata.yaml
    metadata = {}

    if args.summary:
        metadata['summary'] = args.summary
    if args.maintainer:
        metadata['maintainer'] = args.maintainer
    if args.description:
        metadata['description'] = args.description

    # Information for license headers
    license = {
        'year': datetime.now().year
    }

    if args.company:
        license['company'] = args.company
    if args.email:
        license['email'] = args.email

    # Options to configure the backends
    options = {
        'backend': None
    }

    if args.ansible:
        options['backend'] = 'ansible'
    elif args.http:
        options['backend'] = 'http'
    elif args.sol002:
        options['backend'] = 'sol002'
    elif args.scripts:
        options['backend'] = 'scripts'

    return metadata, license, options


def main():
    # getting the input from the user
    args = input_processing()

    # configure the logger
    configure_logger(args)

    logger.info('Starting generation process...')

    # verify if the environment is correct and the args are valid
    verify_environment(args)

    # process data to input in generator
    metadata, license, options = process_args(args)

    logger.debug('Metadata: %s', metadata)
    logger.debug('License: %s', license)
    logger.debug('Options: %s', options)

    if options['backend'] == 'ansible':
        generator = AnsibleGenerator(metadata=metadata, license=license, options=options)
    elif options['backend'] == 'http':
        logger.error('HTTP backend not yet available. Available backends are: ansible')
        sys.exit(-1)
    elif options['backend'] == 'sol002':
        logger.error('SOL002 backend not yet available. Available backends are: ansible')
        sys.exit(-1)
    elif options['backend'] == 'scripts':
        logger.error('Scripts backend not yet available. Available backends are: ansible')
        sys.exit(-1)
    else:
        logger.error('Undefined backend for generator. Available backends are: ansible')
        sys.exit(-1)

    generator.generate()

    logger.info('Generation process complete.')
