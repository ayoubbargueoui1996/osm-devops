# Copyright 2021 Canonical Ltd.
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
# contact: legal@canonical.com
#
# To get in touch with the maintainers, please contact:
# osm-charmers@lists.launchpad.net
##

from charms.layer.caas_base import pod_spec_set
from charms.reactive import when, when_not, hook
from charms.reactive import endpoint_from_flag
from charms.reactive.flags import set_flag, clear_flag
from charmhelpers.core.hookenv import log, metadata, config
from charms import layer
from charms.osm.k8s import get_service_ip


@hook("upgrade-charm")
@when("leadership.is_leader")
def upgrade():
    clear_flag("kafka-k8s.configured")


@when("config.changed")
@when("leadership.is_leader")
def restart():
    clear_flag("kafka-k8s.configured")


@when_not("zookeeper.ready")
@when("leadership.is_leader")
def waiting_for_zookeeper():
    layer.status.waiting("Waiting for Zookeeper to be ready")


@when("zookeeper.ready")
@when_not("kafka-k8s.configured")
@when("leadership.is_leader")
def configure():
    layer.status.maintenance("Configuring kafka container")
    try:
        zookeeper = endpoint_from_flag("zookeeper.ready")
        zk_units = zookeeper.zookeepers()
        zk_unit = zk_units[0]
        if zk_unit["port"]:
            cfg = config()
            zookeeper_uri = ""
            zk_pod_base_name = "zookeeper-k8s"
            zk_service_name = cfg.get("zookeeper-service-name")
            zk_num = cfg.get("zookeeper-units")
            if zk_num == 1:
                zookeeper_uri = "{}:{}".format(zk_unit["host"], zk_unit["port"])
            else:
                for i in range(0, zk_num):
                    if i:
                        zookeeper_uri += ","
                    zookeeper_uri += "{}-{}.{}:{}".format(
                        zk_pod_base_name, i, zk_service_name, zk_unit["port"]
                    )
            spec = make_pod_spec(zookeeper_uri)
            log("set pod spec:\n{}".format(spec))
            pod_spec_set(spec)
            set_flag("kafka-k8s.configured")
    except Exception as e:
        layer.status.blocked("k8s spec failed to deploy: {}".format(e))


@when("kafka-k8s.configured")
def set_kafka_active():
    layer.status.active("ready")


@when("zookeeper.ready")
@when_not("leadership.is_leader")
def non_leaders_active():
    layer.status.active("ready")


@when("kafka-k8s.configured")
@when("kafka.joined", "zookeeper.ready")
def serve_client():
    layer.status.maintenance("Sending kafka configuration")
    try:
        kafka = endpoint_from_flag("kafka.joined")
        zookeeper = endpoint_from_flag("zookeeper.ready")
        if zookeeper and kafka:
            service_ip = get_service_ip("kafka")
            if service_ip:
                kafka.send_connection(
                    get_kafka_port(), service_ip,
                )
                kafka.send_zookeepers(zookeeper.zookeepers())
                clear_flag("kafka.joined")
    except Exception as e:
        log("Fail sending kafka configuration: {}".format(e))


def make_pod_spec(zookeeper_uri):
    """Make pod specification for Kubernetes

    Args:
        zookeeper_uri (str): Zookeeper hosts appended by comma.
    Returns:
        pod_spec: Pod specification for Kubernetes
    """

    with open("reactive/spec_template.yaml") as spec_file:
        pod_spec_template = spec_file.read()

    md = metadata()
    cfg = config()

    data = {
        "name": md.get("name"),
        "docker_image": cfg.get("image"),
        "port": get_kafka_port(),
        "zookeeper_uri": zookeeper_uri,
    }
    data.update(cfg)
    return pod_spec_template % data


def get_kafka_port():
    """Returns Kafka port"""
    cfg = config()
    return cfg.get("advertised-port")
