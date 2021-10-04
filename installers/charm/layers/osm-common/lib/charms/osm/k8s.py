# Copyright 2020 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.

from charmhelpers.core.hookenv import (
    network_get,
    relation_id,
    log,
)


def get_service_ip(endpoint):
    try:
        info = network_get(endpoint, relation_id())
        if 'ingress-addresses' in info:
            addr = info['ingress-addresses'][0]
            if len(addr):
                return addr
        else:
            log("No ingress-addresses: {}".format(info))
    except Exception as e:
        log("Caught exception checking for service IP: {}".format(e))

    return None


def is_pod_up(endpoint):
    """Check to see if the pod of a relation is up.

    application-vimdb: 19:29:10 INFO unit.vimdb/0.juju-log network info

    In the example below:
    - 10.1.1.105 is the address of the application pod.
    - 10.152.183.199 is the service cluster ip

    {
        'bind-addresses': [{
            'macaddress': '',
            'interfacename': '',
            'addresses': [{
                'hostname': '',
                'address': '10.1.1.105',
                'cidr': ''
            }]
        }],
        'egress-subnets': [
            '10.152.183.199/32'
        ],
        'ingress-addresses': [
            '10.152.183.199',
            '10.1.1.105'
        ]
    }
    """
    try:
        info = network_get(endpoint, relation_id())

        # Check to see if the pod has been assigned it's internal and
        # external ips
        for ingress in info['ingress-addresses']:
            if len(ingress) == 0:
                return False
    except:
        return False

    return True
