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
from charmhelpers.core.hookenv import (
    log,
    metadata,
    config,
)
from charms import layer
from charmhelpers.core import hookenv
import traceback


@hook("upgrade-charm")
@when("leadership.is_leader")
def upgrade():
    clear_flag("grafana-k8s.configured")


@when("config.changed")
@when("leadership.is_leader")
def restart():
    clear_flag("grafana-k8s.configured")


@when_not("endpoint.prometheus.available")
@when("leadership.is_leader")
def waiting_for_prometheus_interface():
    layer.status.waiting("Waiting for prometheus interface")


@when("endpoint.prometheus.available")
@when_not("grafana-k8s.configured")
@when("leadership.is_leader")
def configure():
    layer.status.maintenance("Configuring grafana container")
    try:
        prometheus = endpoint_from_flag("endpoint.prometheus.available")
        prometheus_url = prometheus.targets()[0]["targets"][0]

        if prometheus_url:
            spec = make_pod_spec(prometheus_url)
            log("set pod spec:\n{}".format(spec))
            pod_spec_set(spec)
            set_flag("grafana-k8s.configured")
            layer.status.active("ready")

    except Exception as e:
        layer.status.blocked("k8s spec failed to deploy: {}".format(e))
        log(traceback.format_exc(), level=hookenv.ERROR)


@when("grafana-k8s.configured")
def set_grafana_active():
    layer.status.active("ready")


@when("endpoint.prometheus.available")
@when_not("leadership.is_leader")
def non_leaders_active():
    layer.status.active("ready")


def make_pod_spec(prometheus_url):
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
        "docker_image": cfg.get("image"),
        "prometheus_url": prometheus_url,
    }
    data.update(cfg)
    return pod_spec_template % data
