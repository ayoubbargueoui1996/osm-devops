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
from charms.reactive import endpoint_from_flag
from charms.layer.caas_base import pod_spec_set
from charms.reactive import when, when_not, hook
from charms.reactive.flags import set_flag, clear_flag
from charmhelpers.core.hookenv import log, metadata, config
from charms import layer


@hook("upgrade-charm")
@when("leadership.is_leader")
def upgrade():
    clear_flag("mon-k8s.configured")


@when("config.changed")
@when("leadership.is_leader")
def restart():
    clear_flag("mon-k8s.configured")


@when_not("kafka.ready")
@when_not("mon-k8s.configured")
@when("leadership.is_leader")
def waiting_for_kafka():
    layer.status.waiting("Waiting for kafka to be ready")


@when_not("mongo.ready")
@when_not("mon-k8s.configured")
@when("leadership.is_leader")
def waiting_for_mongo():
    layer.status.waiting("Waiting for mongo to be ready")


@when_not("endpoint.prometheus.available")
@when_not("mon-k8s.configured")
@when("leadership.is_leader")
def waiting_for_prometheus():
    layer.status.waiting("Waiting for prometheus to be ready")


@when("kafka.ready", "mongo.ready", "endpoint.prometheus.available")
@when_not("mon-k8s.configured")
@when("leadership.is_leader")
def configure():
    layer.status.maintenance("Configuring mon container")
    try:
        kafka = endpoint_from_flag("kafka.ready")
        mongo = endpoint_from_flag("mongo.ready")
        prometheus = endpoint_from_flag("endpoint.prometheus.available")

        if kafka and mongo and prometheus:
            kafka_units = kafka.kafkas()
            kafka_unit = kafka_units[0]

            mongo_uri = mongo.connection_string()
            log("Mongo URI: {}".format(mongo_uri))

            prometheus_url = prometheus.targets()[0]["targets"][0]

            if mongo_uri and kafka_unit["host"]:

                spec = make_pod_spec(
                    kafka_unit["host"], kafka_unit["port"], mongo_uri, prometheus_url
                )

                log("set pod spec:\n{}".format(spec))
                pod_spec_set(spec)
                set_flag("mon-k8s.configured")
    except Exception as e:
        layer.status.blocked("k8s spec failed to deploy: {}".format(e))


@when("kafka.ready", "mongo.ready", "endpoint.prometheus.available")
@when_not("leadership.is_leader")
def non_leaders_active():
    layer.status.active("ready")


@when("mon-k8s.configured")
def set_mon_active():
    layer.status.active("ready")


def make_pod_spec(kafka_host, kafka_port, mongo_uri, prometheus_url):
    """Make pod specification for Kubernetes

    Args:
        kafka_host (str): Kafka hostname or IP
        kafka_port (int): Kafka port
        mongo_uri (str): Mongo URI
    Returns:
        pod_spec: Pod specification for Kubernetes
    """

    with open("reactive/spec_template.yaml") as spec_file:
        pod_spec_template = spec_file.read()

    md = metadata()
    cfg = config()

    data = {
        "name": md.get("name"),
        "kafka_host": kafka_host,
        "kafka_port": kafka_port,
        "mongo_uri": mongo_uri,
        "prometheus_url": prometheus_url,
    }
    data.update(cfg)
    return pod_spec_template % data
