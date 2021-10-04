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

from charms.reactive import when, when_not, hook
from charms.reactive.flags import set_flag, clear_flag
from charmhelpers.core.hookenv import (
    log,
    metadata,
    config,
    network_get,
    relation_id,
)
from charms import layer
from charmhelpers.core import hookenv
import traceback


@hook("upgrade-charm")
@when("leadership.is_leader")
def upgrade():
    clear_flag("prometheus-k8s.configured")


@when("config.changed")
@when("leadership.is_leader")
def restart():
    clear_flag("prometheus-k8s.configured")


@when_not("prometheus-k8s.configured")
@when("leadership.is_leader")
def configure():
    layer.status.maintenance("Configuring prometheus container")
    try:
        spec = make_pod_spec()
        log("set pod spec:\n{}".format(spec))
        layer.caas_base.pod_spec_set(spec)
        set_flag("prometheus-k8s.configured")
        layer.status.active("ready")

    except Exception as e:
        layer.status.blocked("k8s spec failed to deploy: {}".format(e))
        log(traceback.format_exc(), level=hookenv.ERROR)


@when("prometheus-k8s.configured")
def set_prometheus_active():
    layer.status.active("ready")


@when_not("leadership.is_leader")
def non_leaders_active():
    layer.status.active("ready")


@when("prometheus-k8s.configured", "endpoint.prometheus.available")
def send_config(prometheus):
    layer.status.maintenance("Sending prometheus configuration")
    cfg = config()
    try:
        info = network_get("prometheus", relation_id())
        log("network info {0}".format(info))
        host = info.get("ingress-addresses", [""])[0]

        prometheus.configure(hostname=host, port=cfg.get("advertised-port"))
        clear_flag("endpoint.prometheus.available")
    except Exception as e:
        log("Exception sending config: {}".format(e))


def make_pod_spec():
    """Make pod specification for Kubernetes

    Returns:
        pod_spec: Pod specification for Kubernetes
    """
    with open("reactive/spec_template.yaml") as spec_file:
        pod_spec_template = spec_file.read()

    md = metadata()
    cfg = config()

    data = {
        "name": md.get("name"),
        "docker_image": cfg.get("prometheus-image"),
        "a_docker_image": cfg.get("alpine-image"),
    }
    data.update(cfg)
    return pod_spec_template % data
