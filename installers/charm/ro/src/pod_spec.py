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
    """Validates passed information.

    Args:
        config_data (Dict[str, Any]): configuration information.
        relation_data (Dict[str, Any]): relation information

    Raises:
        ValueError: when config and/or relation data is not valid.
    """
    config_validators = {
        "enable_ng_ro": lambda value, _: isinstance(value, bool),
        "database_commonkey": lambda value, values: (
            isinstance(value, str) and len(value) > 0
        )
        if values.get("enable_ng_ro", True)
        else True,
        "log_level": lambda value, _: (
            isinstance(value, str) and value in ("INFO", "DEBUG")
        ),
        "vim_database": lambda value, values: (
            isinstance(value, str) and len(value) > 0
        )
        if not values.get("enable_ng_ro", True)
        else True,
        "ro_database": lambda value, values: (isinstance(value, str) and len(value) > 0)
        if not values.get("enable_ng_ro", True)
        else True,
        "openmano_tenant": lambda value, values: (
            isinstance(value, str) and len(value) > 0
        )
        if not values.get("enable_ng_ro", True)
        else True,
    }
    relation_validators = {
        "kafka_host": lambda value, _: (isinstance(value, str) and len(value) > 0)
        if config_data.get("enable_ng_ro", True)
        else True,
        "kafka_port": lambda value, _: (isinstance(value, str) and len(value) > 0)
        if config_data.get("enable_ng_ro", True)
        else True,
        "mongodb_connection_string": lambda value, _: (
            isinstance(value, str) and value.startswith("mongodb://")
        )
        if config_data.get("enable_ng_ro", True)
        else True,
        "mysql_host": lambda value, _: (isinstance(value, str) and len(value) > 0)
        if not config_data.get("enable_ng_ro", True)
        else True,
        "mysql_port": lambda value, _: (isinstance(value, int) and value > 0)
        if not config_data.get("enable_ng_ro", True)
        else True,
        "mysql_user": lambda value, _: (isinstance(value, str) and len(value) > 0)
        if not config_data.get("enable_ng_ro", True)
        else True,
        "mysql_password": lambda value, _: (isinstance(value, str) and len(value) > 0)
        if not config_data.get("enable_ng_ro", True)
        else True,
        "mysql_root_password": lambda value, _: (
            isinstance(value, str) and len(value) > 0
        )
        if not config_data.get("enable_ng_ro", True)
        else True,
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
    return [{"name": "ro", "containerPort": port, "protocol": "TCP"}]


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
        "OSMRO_LOG_LEVEL": config["log_level"],
    }

    if config.get("enable_ng_ro", True):
        # Kafka configuration
        envconfig["OSMRO_MESSAGE_DRIVER"] = "kafka"
        envconfig["OSMRO_MESSAGE_HOST"] = relation_state["kafka_host"]
        envconfig["OSMRO_MESSAGE_PORT"] = relation_state["kafka_port"]

        # MongoDB configuration
        envconfig["OSMRO_DATABASE_DRIVER"] = "mongo"
        envconfig["OSMRO_DATABASE_URI"] = relation_state["mongodb_connection_string"]
        envconfig["OSMRO_DATABASE_COMMONKEY"] = config["database_commonkey"]
    else:
        envconfig["RO_DB_HOST"] = relation_state["mysql_host"]
        envconfig["RO_DB_OVIM_HOST"] = relation_state["mysql_host"]
        envconfig["RO_DB_PORT"] = relation_state["mysql_port"]
        envconfig["RO_DB_OVIM_PORT"] = relation_state["mysql_port"]
        envconfig["RO_DB_USER"] = relation_state["mysql_user"]
        envconfig["RO_DB_OVIM_USER"] = relation_state["mysql_user"]
        envconfig["RO_DB_PASSWORD"] = relation_state["mysql_password"]
        envconfig["RO_DB_OVIM_PASSWORD"] = relation_state["mysql_password"]
        envconfig["RO_DB_ROOT_PASSWORD"] = relation_state["mysql_root_password"]
        envconfig["RO_DB_OVIM_ROOT_PASSWORD"] = relation_state["mysql_root_password"]
        envconfig["RO_DB_NAME"] = config["ro_database"]
        envconfig["RO_DB_OVIM_NAME"] = config["vim_database"]
        envconfig["OPENMANO_TENANT"] = config["openmano_tenant"]

    return envconfig


def _make_startup_probe() -> Dict[str, Any]:
    """Generate startup probe.

    Returns:
        Dict[str, Any]: startup probe.
    """
    return {
        "exec": {"command": ["/usr/bin/pgrep", "python3"]},
        "initialDelaySeconds": 60,
        "timeoutSeconds": 5,
    }


def _make_readiness_probe(port: int) -> Dict[str, Any]:
    """Generate readiness probe.

    Args:
        port (int): service port.

    Returns:
        Dict[str, Any]: readiness probe.
    """
    return {
        "httpGet": {
            "path": "/openmano/tenants",
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
        port (int): service port.

    Returns:
        Dict[str, Any]: liveness probe.
    """
    return {
        "httpGet": {
            "path": "/openmano/tenants",
            "port": port,
        },
        "initialDelaySeconds": 600,
        "periodSeconds": 10,
        "timeoutSeconds": 5,
        "successThreshold": 1,
        "failureThreshold": 3,
    }


def make_pod_spec(
    image_info: Dict[str, str],
    config: Dict[str, Any],
    relation_state: Dict[str, Any],
    app_name: str = "ro",
    port: int = 9090,
) -> Dict[str, Any]:
    """Generate the pod spec information.

    Args:
        image_info (Dict[str, str]): Object provided by
                                     OCIImageResource("image").fetch().
        config (Dict[str, Any]): Configuration information.
        relation_state (Dict[str, Any]): Relation state information.
        app_name (str, optional): Application name. Defaults to "ro".
        port (int, optional): Port for the container. Defaults to 9090.

    Returns:
        Dict[str, Any]: Pod spec dictionary for the charm.
    """
    if not image_info:
        return None

    _validate_data(config, relation_state)

    ports = _make_pod_ports(port)
    env_config = _make_pod_envconfig(config, relation_state)
    startup_probe = _make_startup_probe()
    readiness_probe = _make_readiness_probe(port)
    liveness_probe = _make_liveness_probe(port)

    return {
        "version": 3,
        "containers": [
            {
                "name": app_name,
                "imageDetails": image_info,
                "imagePullPolicy": "Always",
                "ports": ports,
                "envConfig": env_config,
                "kubernetes": {
                    "startupProbe": startup_probe,
                    "readinessProbe": readiness_probe,
                    "livenessProbe": liveness_probe,
                },
            }
        ],
        "kubernetesResources": {
            "ingressResources": [],
        },
    }
