#!/usr/bin/env python3
# Copyright 2020 Canonical Ltd.
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

import logging
from typing import Any, Dict, List, NoReturn

logger = logging.getLogger(__name__)


def _validate_data(
    config_data: Dict[str, Any], relation_data: Dict[str, Any]
) -> NoReturn:
    """Validate input data.

    Args:
        config_data (Dict[str, Any]): configuration data.
        relation_data (Dict[str, Any]): relation data.
    """
    config_validators = {
        "openstack_default_granularity": lambda value, _: (
            isinstance(value, int) and value > 0
        ),
        "global_request_timeout": lambda value, _: isinstance(value, int) and value > 0,
        "log_level": lambda value, _: (
            isinstance(value, str) and value in ("INFO", "DEBUG")
        ),
        "collector_interval": lambda value, _: isinstance(value, int) and value > 0,
        "evaluator_interval": lambda value, _: isinstance(value, int) and value > 0,
        "database_commonkey": lambda value, _: (
            isinstance(value, str) and len(value) > 0
        ),
        "vca_host": lambda value, _: isinstance(value, str) and len(value) > 0,
        "vca_user": lambda value, _: isinstance(value, str) and len(value) > 0,
        "vca_password": lambda value, _: isinstance(value, str) and len(value) > 0,
        "vca_cacert": lambda value, _: isinstance(value, str),
    }
    relation_validators = {
        "message_host": lambda value, _: isinstance(value, str) and len(value) > 0,
        "message_port": lambda value, _: isinstance(value, int) and value > 0,
        "database_uri": lambda value, _: (
            isinstance(value, str) and value.startswith("mongodb://")
        ),
        "prometheus_host": lambda value, _: isinstance(value, str) and len(value) > 0,
        "prometheus_port": lambda value, _: isinstance(value, int) and value > 0,
    }
    problems = []

    for key, validator in config_validators.items():
        valid = validator(config_data.get(key), config_data)

        if not valid:
            problems.append(key)

    for key, validator in relation_validators.items():
        valid = validator(relation_data.get(key), relation_data)

        if not valid:
            problems.append(key)

    if len(problems) > 0:
        raise ValueError("Errors found in: {}".format(", ".join(problems)))


def _make_pod_ports(port: int) -> List[Dict[str, Any]]:
    """Generate pod ports details.

    Args:
        port (int): port to expose.

    Returns:
        List[Dict[str, Any]]: pod port details.
    """
    return [{"name": "mon", "containerPort": port, "protocol": "TCP"}]


def _make_pod_envconfig(
    config: Dict[str, Any], relation_state: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate pod environment configuration.

    Args:
        config (Dict[str, Any]): configuration information.
        relation_state (Dict[str, Any]): relation state information.

    Returns:
        Dict[str, Any]: pod environment configuration.
    """
    envconfig = {
        # General configuration
        "ALLOW_ANONYMOUS_LOGIN": "yes",
        "OSMMON_OPENSTACK_DEFAULT_GRANULARITY": config["openstack_default_granularity"],
        "OSMMON_GLOBAL_REQUEST_TIMEOUT": config["global_request_timeout"],
        "OSMMON_GLOBAL_LOGLEVEL": config["log_level"],
        "OSMMON_COLLECTOR_INTERVAL": config["collector_interval"],
        "OSMMON_EVALUATOR_INTERVAL": config["evaluator_interval"],
        # Kafka configuration
        "OSMMON_MESSAGE_DRIVER": "kafka",
        "OSMMON_MESSAGE_HOST": relation_state["message_host"],
        "OSMMON_MESSAGE_PORT": relation_state["message_port"],
        # Database configuration
        "OSMMON_DATABASE_DRIVER": "mongo",
        "OSMMON_DATABASE_URI": relation_state["database_uri"],
        "OSMMON_DATABASE_COMMONKEY": config["database_commonkey"],
        # Prometheus configuration
        "OSMMON_PROMETHEUS_URL": f"http://{relation_state['prometheus_host']}:{relation_state['prometheus_port']}",
        # VCA configuration
        "OSMMON_VCA_HOST": config["vca_host"],
        "OSMMON_VCA_USER": config["vca_user"],
        "OSMMON_VCA_SECRET": config["vca_password"],
        "OSMMON_VCA_CACERT": config["vca_cacert"],
    }

    return envconfig


def _make_startup_probe() -> Dict[str, Any]:
    """Generate startup probe.

    Returns:
        Dict[str, Any]: startup probe.
    """
    return {
        "exec": {"command": ["/usr/bin/pgrep python3"]},
        "initialDelaySeconds": 60,
        "timeoutSeconds": 5,
    }


def _make_readiness_probe(port: int) -> Dict[str, Any]:
    """Generate readiness probe.

    Args:
        port (int): [description]

    Returns:
        Dict[str, Any]: readiness probe.
    """
    return {
        "tcpSocket": {
            "port": port,
        },
        "periodSeconds": 10,
        "timeoutSeconds": 5,
        "successThreshold": 1,
        "failureThreshold": 3,
    }


def _make_liveness_probe(port: int) -> Dict[str, Any]:
    """Generate liveness probe.

    Args:
        port (int): [description]

    Returns:
        Dict[str, Any]: liveness probe.
    """
    return {
        "tcpSocket": {
            "port": port,
        },
        "initialDelaySeconds": 45,
        "periodSeconds": 10,
        "timeoutSeconds": 5,
        "successThreshold": 1,
        "failureThreshold": 3,
    }


def make_pod_spec(
    image_info: Dict[str, str],
    config: Dict[str, Any],
    relation_state: Dict[str, Any],
    app_name: str = "mon",
    port: int = 8000,
) -> Dict[str, Any]:
    """Generate the pod spec information.

    Args:
        image_info (Dict[str, str]): Object provided by
                                     OCIImageResource("image").fetch().
        config (Dict[str, Any]): Configuration information.
        relation_state (Dict[str, Any]): Relation state information.
        app_name (str, optional): Application name. Defaults to "mon".
        port (int, optional): Port for the container. Defaults to 8000.

    Returns:
        Dict[str, Any]: Pod spec dictionary for the charm.
    """
    if not image_info:
        return None

    _validate_data(config, relation_state)

    ports = _make_pod_ports(port)
    env_config = _make_pod_envconfig(config, relation_state)

    return {
        "version": 3,
        "containers": [
            {
                "name": app_name,
                "imageDetails": image_info,
                "imagePullPolicy": "Always",
                "ports": ports,
                "envConfig": env_config,
            }
        ],
        "kubernetesResources": {
            "ingressResources": [],
        },
    }
