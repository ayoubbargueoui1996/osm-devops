#!/bin/bash

#   Copyright 2019 Minsait - Indra S.A.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#   Author: Jose Manuel Palacios (jmpalacios@minsait.com)
#   Author: Jose Antonio Martinez (jamartinezv@minsait.com)

# Script to generate new charts for prometheus-operator
HERE=$(dirname $(readlink -f ${BASH_SOURCE[0]}))
source $HERE/versions_monitoring
V_OPERATOR=""

# Assign versions
V_OPERATOR=$PROMETHEUS_OPERATOR

WORK_DIR=$HERE
CHARTS_DIR="$HERE/helm_charts"

# This two objects are not exporting metrics
DELETE_YAML_DAHSBOARDS="etcd.yaml \
    proxy.yaml"
DELETE_YAML_RULES="etcd.yaml"

# There is a bug in this dashboard and it is necessary to change it
CHANGE_YAML_DAHSBOARDS="statefulset.yaml"

# Delete old versions
cd $CHARTS_DIR

rm -rf prometheus-operator > /dev/null 2>&1 
rm prometheus-operator* > /dev/null 2>&1 

echo "Fetching stable/prometheus-operator..."
helm fetch --version=$V_OPERATOR stable/prometheus-operator
tar xvf prometheus-operator-$V_OPERATOR.tgz > /dev/null 2>&1 

cd $WORK_DIR

# Deleting grafana dashboard
echo "Changing prometheus-operator grafana dashboards...."
cd $CHARTS_DIR/prometheus-operator/templates/grafana/dashboards-1.14
for i in $DELETE_YAML_DAHSBOARDS 
do
    #echo "Deleting $i...."
    rm $i
done

# Change CHANGE_YAML_DAHSBOARDS because it has an error
mv $CHANGE_YAML_DAHSBOARDS ${CHANGE_YAML_DAHSBOARDS}.ORI
cat ${CHANGE_YAML_DAHSBOARDS}.ORI | \
    sed 's@{job=\\\"kube-state-metrics\\\"}, cluster=\\\"\$cluster\\\",@{job=\\\"kube-state-metrics\\\", cluster=\\\"\$cluster\\\"},@' > \
    $CHANGE_YAML_DAHSBOARDS
chmod 755 $CHANGE_YAML_DAHSBOARDS
rm ${CHANGE_YAML_DAHSBOARDS}.ORI

cd $WORK_DIR

# Deleting prometheus rules
echo "Changing prometheus-operator rules...."
cd $CHARTS_DIR/prometheus-operator/templates/prometheus/rules-1.14
for i in $DELETE_YAML_RULES 
do
    #echo "Deleting $i...."
    rm $i
done

# Deleting Grafana dependence to avoid it installation
sed -i -e '/.*- name: grafana.*/,+3d' $CHARTS_DIR/prometheus-operator/requirements.yaml
sed -i -e '/.*- name: grafana.*/,+2d' $CHARTS_DIR/prometheus-operator/requirements.lock
rm -rf $CHARTS_DIR/prometheus-operator/charts/grafana

exit 0
