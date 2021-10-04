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
from charms.osm.k8s import get_service_ip
import urllib.parse
import yaml
import traceback


@hook("upgrade-charm")
@when("leadership.is_leader")
def upgrade():
    clear_flag("nbi-k8s.configured")


@when("config.changed")
@when("leadership.is_leader")
def restart():
    clear_flag("nbi-k8s.configured")


@when("config.changed.auth-backend")
def clear_keystone_ready():
    clear_flag("keystone.ready")


@when_not("kafka.ready")
@when_not("nbi-k8s.configured")
@when("leadership.is_leader")
def waiting_for_kafka():
    layer.status.waiting("Waiting for kafka to be ready")


@when_not("mongo.ready")
@when_not("nbi-k8s.configured")
@when("leadership.is_leader")
def waiting_for_mongo():
    layer.status.waiting("Waiting for mongo to be ready")


@when_not("endpoint.prometheus.available")
@when_not("nbi-k8s.configured")
@when("leadership.is_leader")
def waiting_for_prometheus():
    layer.status.waiting("Waiting for prometheus to be ready")


@when_not("keystone.ready")
@when("leadership.is_leader")
@when_not("nbi-k8s.configured")
def waiting_for_keystone():
    auth_backend = config().get("auth-backend")
    if auth_backend == "keystone":
        layer.status.waiting("Waiting for Keystone to be ready")
    else:
        set_flag("keystone.ready")


@when_not("keystone.ready")
@when("leadership.is_leader")
@when_not("nbi-k8s.configured")
def waiting_for_keystone():
    auth_backend = config().get("auth-backend")
    if auth_backend == "keystone":
        layer.status.waiting("Waiting for Keystone to be ready")
    else:
        set_flag("keystone.ready")


@when("kafka.ready", "mongo.ready", "endpoint.prometheus.available", "keystone.ready")
@when_not("nbi-k8s.configured")
@when("leadership.is_leader")
def configure():
    layer.status.maintenance("Configuring nbi container")
    try:
        kafka = endpoint_from_flag("kafka.ready")
        mongo = endpoint_from_flag("mongo.ready")
        prometheus = endpoint_from_flag("endpoint.prometheus.available")

        if kafka and mongo and prometheus:
            kafka_units = kafka.kafkas()
            kafka_unit = kafka_units[0]

            mongo_uri = mongo.connection_string()
            log("Mongo URI: {}".format(mongo_uri))

            prometheus_uri = prometheus.targets()[0]["targets"][0]

            if (
                mongo_uri
                and kafka_unit["host"]
                and kafka_unit["port"]
                and prometheus_uri
            ):
                spec = yaml.load(
                    make_pod_spec(
                        kafka_unit["host"],
                        kafka_unit["port"],
                        mongo_uri,
                        prometheus_uri,
                    )
                )

                auth_backend = config().get("auth-backend")

                if auth_backend == "keystone":
                    keystone = endpoint_from_flag("keystone.ready")
                    if keystone:
                        keystone_units = keystone.keystones()
                        keystone_unit = keystone_units[0]
                        if (
                            keystone_unit["host"]
                            and keystone_unit["port"]
                            and keystone_unit["user_domain_name"]
                            and keystone_unit["project_domain_name"]
                            and keystone_unit["username"]
                            and keystone_unit["password"]
                            and keystone_unit["service"]
                        ):
                            auth_keystone = {
                                "OSMNBI_AUTHENTICATION_BACKEND": "keystone",
                                "OSMNBI_AUTHENTICATION_AUTH_URL": keystone_unit["host"],
                                "OSMNBI_AUTHENTICATION_AUTH_PORT": keystone_unit[
                                    "port"
                                ],
                                "OSMNBI_AUTHENTICATION_USER_DOMAIN_NAME": keystone_unit[
                                    "user_domain_name"
                                ],
                                "OSMNBI_AUTHENTICATION_PROJECT_DOMAIN_NAME": keystone_unit[
                                    "project_domain_name"
                                ],
                                "OSMNBI_AUTHENTICATION_SERVICE_USERNAME": keystone_unit[
                                    "username"
                                ],
                                "OSMNBI_AUTHENTICATION_SERVICE_PASSWORD": keystone_unit[
                                    "password"
                                ],
                                "OSMNBI_AUTHENTICATION_SERVICE_PROJECT": keystone_unit[
                                    "service"
                                ],
                            }
                            spec["containers"][0]["config"].update(auth_keystone)
                elif auth_backend == "internal":
                    spec["containers"][0]["config"][
                        "OSMNBI_AUTHENTICATION_BACKEND"
                    ] = auth_backend
                else:
                    layer.status.blocked(
                        "Unknown authentication method: {}".format(auth_backend)
                    )
                    raise
                log("set pod spec:\n{}".format(spec))
                pod_spec_set(spec)
                set_flag("nbi-k8s.configured")
    except Exception as e:
        layer.status.blocked("k8s spec failed to deploy: {}".format(e))
        log("Error: {}".format(traceback.format_exc()))


@when("kafka.ready", "mongo.ready", "endpoint.prometheus.available")
@when_not("leadership.is_leader")
def non_leaders_active():
    layer.status.active("ready")


@when("nbi-k8s.configured")
def set_nbi_active():
    layer.status.active("ready")


@when("nbi-k8s.configured", "nbi.joined")
def send_config():
    layer.status.maintenance("Sending NBI configuration")
    try:
        nbi = endpoint_from_flag("nbi.joined")
        if nbi:
            service_ip = get_service_ip("nbi")
            if service_ip:
                nbi.send_connection(service_ip, get_nbi_port())
                clear_flag("nbi.joined")
    except Exception as e:
        log("Fail sending NBI configuration: {}".format(e))


def make_pod_spec(kafka_host, kafka_port, mongo_uri, prometheus_uri):
    """Make pod specification for Kubernetes

    Args:
        kafka_host (str): Kafka hostname or IP
        kafka_port (int): Kafka port
        mongo_uri (str): Mongo URI
        prometheus_uri (str): Prometheus URI
    Returns:
        pod_spec: Pod specification for Kubernetes
    """

    with open("reactive/spec_template.yaml") as spec_file:
        pod_spec_template = spec_file.read()

    md = metadata()
    cfg = config()
    prometheus_host, prometheus_port = parse_hostport(prometheus_uri)
    data = {
        "name": md.get("name"),
        "mongo_uri": mongo_uri,
        "kafka_host": "{}".format(kafka_host),
        "kafka_port": "{}".format(kafka_port),
        "prometheus_host": "{}".format(prometheus_host),
        "prometheus_port": "{}".format(prometheus_port),
    }
    data.update(cfg)

    return pod_spec_template % data


def parse_hostport(uri):
    if "//" in uri:
        uri = uri.split("//")[1]
    result = urllib.parse.urlsplit("//" + uri)
    return result.hostname, result.port


def get_nbi_port():
    """Returns NBI port"""
    cfg = config()
    return cfg.get("advertised-port")
