<!--
Copyright 2020 Canonical Ltd.
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
    http://www.apache.org/licenses/LICENSE-2.0
    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License. -->

# Overview

NBI for Juju CAAS

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
mkdir -p ~/charm/layers ~/charm/build ~/charm/interfaces
git clone https://git.launchpad.net/canonical-osm ~/canonical-osm

cd ~/charm/layers
git clone https://git.launchpad.net/charm-osm-nbi nbi-k8s
git clone https://git.launchpad.net/charm-osm-ro ro-k8s
git clone https://git.launchpad.net/charm-k8s-kafka kafka-k8s ~/charm/interfaces
git clone https://git.launchpad.net/charm-k8s-zookeeper zookeeper-k8s
git clone https://git.launchpad.net/charm-k8s-mongodb mongodb-k8s

cd ~/charm/interfaces
mv ~/canonical-osm/charms/interfaces/* .
git clone https://git.launchpad.net/interface-mongodb mongodb

```

**Charm structure:**

```
├── config.yaml
├── icon.svg
├── layer.yaml
├── metadata.yaml
├── reactive
│   ├── spec_template.yaml
│   └── nbi.py
├── README.md
└── tox.ini
```

**Setup environment variables:**

```
export CHARM_LAYERS_DIR=~/charm/layers
export CHARM_BUILD_DIR=~/charm/build
export CHARM_INTERFACES_DIR=~/charm/interfaces
```

**Build:**

```
mkdir ~/charm/layers/nbi-k8s/tests/build
charm build ~/charm/layers/nbi-k8s
charm build ~/charm/layers/kafka-k8s
charm build ~/charm/layers/zookeeper-k8s
charm build ~/charm/layers/mongodb-k8s
mv ~/charm/build/* ~/charm/layers/nbi-k8s/tests/build/
```
