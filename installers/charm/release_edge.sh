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
set -eux

channel=edge
tag=testing-daily

# 1. Build charms
./build.sh

# 2. Release charms
# Reactive charms
charms="lcm-k8s mon-k8s pol-k8s ro-k8s"
for charm in $charms; do
    cs_revision=`charm push $charm/release cs:~charmed-osm/$charm | tail -n +1 | head -1 | awk '{print $2}'`
    charm release --channel $channel $cs_revision
    echo "$charm charm released!"
done

# New charms (with resources)
charms="ng-ui nbi pla keystone ro lcm mon pol"
for charm in $charms; do
    echo "Releasing $charm charm"
    cs_revision=$(charm push $charm/$charm.charm cs:~charmed-osm/$charm | tail -n +1 | head -1 | awk '{print $2}')
    resource_revision=$(charm attach $cs_revision image=external::opensourcemano/$charm:$tag | tail -n +1 | sed 's/[^0-9]*//g')
    image_revision_num=$(echo $resource_revision  | awk '{print $NF}')
    resources_string="--resource image-$image_revision_num"
    charm release --channel $channel $cs_revision $resources_string
    echo "$charm charm released!"
done

charm="prometheus"
echo "Releasing $charm charm"
cs_revision=$(charm push $charm/$charm.charm cs:~charmed-osm/$charm | tail -n +1 | head -1 | awk '{print $2}')
resource_revision=$(charm attach $cs_revision image=external::ubuntu/$charm:latest | tail -n +1 | sed 's/[^0-9]*//g')
image_revision_num=$(echo $resource_revision  | awk '{print $NF}')
backup_resource_revision=$(charm attach $cs_revision backup-image=external::ed1000/prometheus-backup:latest | tail -n +1 | sed 's/[^0-9]*//g')
backup_image_revision_num=$(echo $backup_resource_revision  | awk '{print $NF}')
resources_string="--resource image-$image_revision_num --resource backup-image-$backup_image_revision_num"
charm release --channel $channel $cs_revision $resources_string
echo "$charm charm released!"


charm="grafana"
echo "Releasing $charm charm"
cs_revision=$(charm push $charm/$charm.charm cs:~charmed-osm/$charm | tail -n +1 | head -1 | awk '{print $2}')
resource_revision=$(charm attach $cs_revision image=external::ubuntu/$charm:latest | tail -n +1 | sed 's/[^0-9]*//g')
image_revision_num=$(echo $resource_revision  | awk '{print $NF}')
resources_string="--resource image-$image_revision_num"
charm release --channel $channel $cs_revision $resources_string
echo "$charm charm released!"

# 3. Grant permissions
all_charms="ng-ui nbi pla keystone ro lcm mon pol grafana prometheus"
for charm in $all_charms; do
    echo "Granting permission for $charm charm"
    charm grant cs:~charmed-osm/$charm --channel $channel --acl read everyone
done