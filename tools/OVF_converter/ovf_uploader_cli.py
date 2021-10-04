##
# Copyright 2019 VMware Inc.
# This file is part of ETSI OSM
# All Rights Reserved.
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
# contact:  osslegalrouting@vmware.com
##

import argparse
from uploader import OVFUploader, get_version


def execute_cli():

    """
        Method to parse CLI arguments and execute commands accordingly
        Args : None
        Return : None
    """
    parser = argparse.ArgumentParser(description='Utility to upload an OVF package to vCD')

    parser.add_argument("-v", "--version", action="version", version=str(get_version()),
                        help="shows version of vCD Uploader tool")

    parser.add_argument("ovf_file", action="store",
                        help="filename of OVF file to upload to vCD")

    parser.add_argument("-l", "--vcd_url", action="store",
                        required=True,
                        help="URL for vCD login (ie: https://vcd.local/")

    parser.add_argument("-u", "--username", action="store",
                        required=True,
                        help="Username for vCD login")

    parser.add_argument("-p", "--password", action="store",
                        required=True,
                        help="Password for vCD login")

    parser.add_argument("-o", "--orgname", action="store",
                        required=True,
                        help="Organization name for vCD login")

    args = parser.parse_args()

    if args.ovf_file:
        try:
            uploader = OVFUploader(args.ovf_file,
                                   vcd_url=args.vcd_url,
                                   username=args.username,
                                   password=args.password,
                                   orgname=args.orgname)
            uploader.make_catalog()
            uploader.upload_ovf()
            uploader.wait_for_task_completion()
        except Exception as exp:
            print(exp)
            exit(1)


if __name__ == "__main__":
    execute_cli()
