<!-- Copyright 2021 Canonical Ltd.

Licensed under the Apache License, Version 2.0 (the "License"); you may
not use this file except in compliance with the License. You may obtain
a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.

For those usages not covered by the Apache License, Version 2.0 please
contact: legal@canonical.com

To get in touch with the maintainers, please contact:
osm-charmers@lists.launchpad.net -->

# Overview

Kafka for Juju CAAS


## Testing

The tests of this charm are done using tox and Zaza.



### Prepare environment

The machine in which the tests are run needs access to a juju k8s controller. The easiest way to approach this is by executing the following commands:

```
sudo apt install tox -y
sudo snap install microk8s --classic
sudo snap install juju

microk8s.status --wait-ready
microk8s.enable storage dashboard dns

juju bootstrap microk8s k8s-cloud
```

If /usr/bin/python does not exist, you should probably need to do this:

```
sudo ln -s /usr/bin/python3 /usr/bin/python
```

### Build Charm

**Download dependencies:**

```
mkdir -p ~/charm/layers ~/charm/build
cd ~/charm/layers
git clone https://git.launchpad.net/charm-k8s-kafka kafka-k8s
git clone https://git.launchpad.net/charm-k8s-zookeeper zookeeper-k8s
git clone https://git.launchpad.net/charm-osm-common osm-common
```

**Charm structure:**

```
├── config.yaml
├── icon.svg
├── layer.yaml
├── metadata.yaml
├── reactive
│   ├── spec_template.yaml
│   └── kafka.py
├── README.md
├── test-requirements.txt
├── tests
│   ├── basic_deployment.py
│   ├── bundles
│   │   ├── kafka-ha.yaml
│   │   └── kafka.yaml
│   └── tests.yaml
└── tox.ini
```

**Setup environment variables:**

```
export CHARM_LAYERS_DIR=~/charm/layers
export CHARM_BUILD_DIR=~/charm/build
```

**Build:**

```
mkdir ~/charm/layers/kafka-k8s/tests/build
charm build ~/charm/layers/kafka-k8s
charm build ~/charm/layers/zookeeper-k8s
mv ~/charm/build/* ~/charm/layers/kafka-k8s/tests/build/
```

### Test charm with Tox

```
cd ~/charm/layers/kafka-k8s
tox -e func
```