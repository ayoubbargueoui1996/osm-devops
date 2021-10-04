#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##
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
##
from __future__ import print_function
import json
import yaml
import sys
import getopt
import os

"""
Tests the format of OSM VNFD and NSD descriptors
"""
__author__ = "Alfonso Tierno, Guillermo Calvino"
__date__ = "2018-04-16"
__version__ = "0.0.1"
version_date = "Apr 2018"


class ArgumentParserError(Exception):
    pass

class DescriptorValidationError(Exception):
    pass

def usage():
    print("Usage: {} [options] FILE".format(sys.argv[0]))
    print(" Validates vnfd, nsd and nst descriptors format")
    print(" FILE: a yaml or json vnfd-catalog, nsd-catalog or nst descriptor")
    print(" OPTIONS:")
    print("      -v|--version: prints current version")
    print("      -h|--help: shows this help")
    print("      -i|--input FILE: (same as param FILE) descriptor file to be upgraded")
    print("      -c|--charms: looks for the charms folder and validates its coherency with the descriptor")
    return


def remove_prefix(desc, prefix):
    """
    Recursively removes prefix from keys
    :param desc: dictionary or list to change
    :param prefix: prefix to remove. Must
    :return: None, param desc is changed
    """
    prefix_len = len(prefix)
    if isinstance(desc, dict):
        prefixed_list=[]
        for k,v in desc.items():
            if isinstance(v, (list, tuple, dict)):
                remove_prefix(v, prefix)
            if isinstance(k, str) and k.startswith(prefix) and k != prefix:
                prefixed_list.append(k)
        for k in prefixed_list:
            desc[k[prefix_len:]] = desc.pop(k)
    elif isinstance(desc, (list, tuple)):
        for i in desc:
            if isinstance(desc, (list, tuple, dict)):
                remove_prefix(i, prefix)


# Mrityunjay Yadav: Function to verify charm included in VNF Package
def validate_charm(charm, desc_file):
    """
    Verify charm included in VNF Package and raised error if invalid
    :param charm: vnf-configuration/vdu-configuration
    :param desc_file: descriptor file
    :return: None
    """
    check_list = ['layer.yaml', 'metadata.yaml', 'actions.yaml', 'actions', 'hooks']
    charm_name = charm['juju']['charm']
    charm_dir = os.path.join(os.path.abspath(os.path.dirname(desc_file)), 'charms', charm_name)

    config_primitive = charm.get('config-primitive', [])
    initial_config_primitive = charm.get('initial-config-primitive', [])

    if charm.get('metrics'):
        check_list.append('metrics.yaml')

    if os.path.exists(charm_dir):
        if not all(item in os.listdir(charm_dir) for item in check_list):
            raise KeyError("Invalid charm {}".format(charm_name))
    else:
        raise KeyError("Provided charm:{} does not exist in descriptor.".format(charm_name))


if __name__ == "__main__":
    error_position = []
    format_output_yaml = True
    input_file_name = None
    test_file = None
    file_name = None
    validate_charms = False
    try:
        # load parameters and configuration
        opts, args = getopt.getopt(sys.argv[1:], "hvi:o:", ["input=", "help", "version",])

        for o, a in opts:
            if o in ("-v", "--version"):
                print("test descriptor version THREE " + __version__ + ' ' + version_date)
                sys.exit()
            elif o in ("-h", "--help"):
                usage()
                sys.exit()
            elif o in ("-i", "--input"):
                input_file_name = a
            elif o in ("-c", "--charms"):
                validate_charms = True
            else:
                assert False, "Unhandled option"
        if not input_file_name:
            if not args:
                raise ArgumentParserError("missing DESCRIPTOR_FILE parameter. Type --help for more info")
            input_file_name = args[0]

        # Open files
        file_name = input_file_name
        with open(file_name, 'r') as f:
            descriptor_str = f.read()
        file_name = None

        if input_file_name.endswith('.yaml') or input_file_name.endswith('.yml') or not \
            (input_file_name.endswith('.json') or '\t' in descriptor_str):
            data = yaml.load(descriptor_str)
        else:   # json
            data = json.loads(descriptor_str)
            format_output_yaml = False

        import osm_im.vnfd as vnfd_catalog
        import osm_im.nsd as nsd_catalog
        import osm_im.nst as nst_catalog
        from pyangbind.lib.serialise import pybindJSONDecoder

        if "vnfd:vnfd-catalog" in data or "vnfd-catalog" in data:
            descriptor = "VNF"
            # Check if mgmt-interface is defined:
            remove_prefix(data, "vnfd:")
            vnfd_descriptor = data["vnfd-catalog"]
            vnfd_list = vnfd_descriptor["vnfd"]
            mgmt_iface = False
            for vnfd in vnfd_list:
                if "vdu" not in vnfd and "kdu" not in vnfd:
                    raise DescriptorValidationError("vdu or kdu not present in the descriptor")
                vdu_list = vnfd.get("vdu",[])
                for vdu in vdu_list:
                    interface_list = []
                    external_interface_list = vdu.pop("external-interface", ())
                    for external_interface in external_interface_list:
                        if external_interface.get("virtual-interface", {}).get("type") == "OM-MGMT":
                            raise KeyError(
                                "Wrong 'Virtual-interface type': Deprecated 'OM-MGMT' value. Please, use 'PARAVIRT' instead")
                    interface_list = vdu.get("interface", ())
                    for interface in interface_list:
                        if interface.get("virtual-interface", {}).get("type") == "OM-MGMT":
                            raise KeyError(
                                "Wrong 'Virtual-interface type': Deprecated 'OM-MGMT' value. Please, use 'PARAVIRT' instead")
                    # Mrityunjay yadav: Verify charm if included in vdu
                    if vdu.get("vdu-configuration", False) and validate_charms:
                        validate_charm(vdu["vdu-configuration"], input_file_name)
                if vnfd.get("mgmt-interface"):
                    mgmt_iface = True
                    if vnfd["mgmt-interface"].get("vdu-id"):
                        raise KeyError("'mgmt-iface': Deprecated 'vdu-id' field. Please, use 'cp' field instead")
                # Mrityunjay yadav: Verify charm if included in vnf
                if vnfd.get("vnf-configuration", False) and validate_charms:
                    validate_charm(vnfd["vnf-configuration"], input_file_name)
                kdu_list = vnfd.get("kdu",[])

            if not mgmt_iface:
                raise KeyError("'mgmt-interface' is a mandatory field and it is not defined")
            myvnfd = vnfd_catalog.vnfd()
            pybindJSONDecoder.load_ietf_json(data, None, None, obj=myvnfd)
        elif "nsd:nsd-catalog" in data or "nsd-catalog" in data:
            descriptor = "NS"
            mynsd = nsd_catalog.nsd()
            pybindJSONDecoder.load_ietf_json(data, None, None, obj=mynsd)
        elif "nst:nst" in data or "nst" in data:
            descriptor = "NST"
            mynst = nst_catalog.nst()
            pybindJSONDecoder.load_ietf_json(data, None, None, obj=mynst)
        else:
            descriptor = None
            raise KeyError("This is not neither nsd-catalog nor vnfd-catalog descriptor")
        exit(0)

    except yaml.YAMLError as exc:
        error_pos = ""
        if hasattr(exc, 'problem_mark'):
            mark = exc.problem_mark
            error_pos = "at line:%s column:%s" % (mark.line + 1, mark.column + 1)
        print("Error loading file '{}'. yaml format error {}".format(input_file_name, error_pos), file=sys.stderr)
    except DescriptorValidationError as e:
        print(str(e), file=sys.stderr)
    except ArgumentParserError as e:
        print(str(e), file=sys.stderr)
    except IOError as e:
        print("Error loading file '{}': {}".format(file_name, e), file=sys.stderr)
    except ImportError as e:
        print ("Package python-osm-im not installed: {}".format(e), file=sys.stderr)
    except Exception as e:
        if file_name:
            print("Error loading file '{}': {}".format(file_name, str(e)), file=sys.stderr)
        else:
            if descriptor:
                print("Error. Invalid {} descriptor format in '{}': {}".format(descriptor, input_file_name, str(e)), file=sys.stderr)
            else:
                print("Error. Invalid descriptor format in '{}': {}".format(input_file_name, str(e)), file=sys.stderr)
    exit(1)
