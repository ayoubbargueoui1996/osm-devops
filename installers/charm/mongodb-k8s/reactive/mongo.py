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
from charms.reactive import endpoint_from_flag
from charms.reactive import when, when_not, hook
from charms.reactive.flags import set_flag, clear_flag
from charmhelpers.core.hookenv import log, metadata, config, goal_state
from charms import layer


@hook("upgrade-charm")
@when("leadership.is_leader")
def upgrade():
    clear_flag("mongodb-k8s.configured")


@when("config.changed")
@when("leadership.is_leader")
def restart():
    clear_flag("mongodb-k8s.configured")


@when_not("mongodb-k8s.configured")
@when("leadership.is_leader")
def configure():
    layer.status.maintenance("Configuring MongoDB container")
    try:
        spec = make_pod_spec()
        log("set pod spec:\n{}".format(spec))
        pod_spec_set(spec)
        set_flag("mongodb-k8s.configured")
    except Exception as e:
        layer.status.blocked("k8s spec failed to deploy: {}".format(e))


@when("mongodb-k8s.configured")
def set_mongodb_active():
    layer.status.active("ready")


@when_not("leadership.is_leader")
def non_leaders_active():
    layer.status.active("ready")


@when("mongodb-k8s.configured", "mongo.joined")
def send_config():
    layer.status.maintenance("Sending mongo configuration")
    try:
        mongo = endpoint_from_flag("mongo.joined")
        if mongo:
            cfg = config()
            mongo_uri = "mongodb://"
            for i, unit in enumerate(goal_state()["units"]):
                pod_base_name = unit.split("/")[0]
                service_name = cfg.get("service-name")
                pod_name = "{}-{}".format(pod_base_name, i)
                if i:
                    mongo_uri += ","
                mongo_uri += "{}.{}:{}".format(
                    pod_name, service_name, get_mongodb_port()
                )
            if cfg.get("enable-sidecar"):
                mongo_uri += "/?replicaSet={}".format(get_mongodb_replset())
            log("Mongo URI: {}".format(mongo_uri))
            mongo.send_connection_string(mongo_uri)
            clear_flag("mongo.joined")
    except Exception as e:
        log("Exception sending config: {}".format(e))
        clear_flag("mongo.joined")


def make_pod_spec():
    """Make pod specification for Kubernetes

    Returns:
        pod_spec: Pod specification for Kubernetes
    """
    md = metadata()
    cfg = config()

    if cfg.get("enable-sidecar"):
        with open("reactive/spec_template_ha.yaml") as spec_file:
            pod_spec_template = spec_file.read()
    else:
        with open("reactive/spec_template.yaml") as spec_file:
            pod_spec_template = spec_file.read()

    data = {
        "name": md.get("name"),
        "docker_image": cfg.get("mongodb-image"),
        "sc_docker_image": cfg.get("sidecar-image"),
        "pod_labels": "juju-app={}".format(cfg.get("advertised-hostname")),
    }

    data.update(cfg)
    return pod_spec_template % data


def get_mongodb_port():
    """Returns MongoDB port"""
    cfg = config()
    return cfg.get("advertised-port")


def get_mongodb_replset():
    """Returns MongoDB port"""
    cfg = config()
    return cfg.get("replica-set")
