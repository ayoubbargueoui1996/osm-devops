#!/bin/bash
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

function build() {
    cd $1 && tox -e build && cd ..
}

# reactive_charms=""
# for charm_directory in $reactive_charms; do
#     echo "Building charm $charm_directory..."
#     cd $charm_directory
#     charmcraft build
#     cd ..
# done

# build 'lcm-k8s'
# build 'mon-k8s'
# build 'nbi-k8s'
# build 'pol-k8s'
# build 'ro-k8s'
# build 'ui-k8s'

charms="ro nbi pla pol mon lcm ng-ui keystone grafana prometheus keystone mariadb-k8s mongodb-k8s zookeeper-k8s kafka-k8s"
if [ -z `which charmcraft` ]; then
    sudo snap install charmcraft --edge
fi

for charm_directory in $charms; do
    echo "Building charm $charm_directory..."
    # cd $charm_directory
    build $charm_directory
    # cd ..
done
