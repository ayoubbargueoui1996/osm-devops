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

# Obtain the path where the script is located
HERE=$(dirname $(readlink -f ${BASH_SOURCE[0]}))

echo $HERE
# Load component versions to be deployed
source $HERE/versions_monitoring
V_OPERATOR=""
V_MONGODB_EXPORTER=""
V_MYSQL_EXPORTER=""

V_OPERATOR=$PROMETHEUS_OPERATOR
V_MONGODB_EXPORTER=$PROMETHEUS_MONGODB_EXPORTER
V_MYSQL_EXPORTER=$PROMETHEUS_MYSQL_EXPORTER


function usage(){
    echo -e "usage: $0 [OPTIONS]"
    echo -e "Install OSM Monitoring"
    echo -e "  OPTIONS"
    echo -e "     -n <namespace>   :   use specified kubernetes namespace - default: monitoring"
    echo -e "     -s <service_type>:   service type (ClusterIP|NodePort|LoadBalancer) - default: NodePort"
    echo -e "     --debug          :   debug script"
    echo -e "     --dump           :   dump arguments and versions"
    echo -e "     -h / --help      :   print this help"
}

NAMESPACE=monitoring
HELM=""
DEBUG=""
DUMP_VARS=""
SERVICE_TYPE=""
while getopts ":h-:n:s:" o; do
    case "${o}" in
        h)
            usage && exit 0
            ;;
        n)
            NAMESPACE="${OPTARG}"
            ;;

        s)
            SERVICE_TYPE="${OPTARG}"
            ;;

        -)
            [ "${OPTARG}" == "help" ] && usage && exit 0
            [ "${OPTARG}" == "debug" ] && DEBUG="y" && continue
            [ "${OPTARG}" == "dump" ] && DUMP_VARS="y" && continue
            echo -e "Invalid option: '--$OPTARG'\n" >&2
            usage && exit 1
            ;;

        \?)
            echo -e "Invalid option: '-$OPTARG'\n" >&2
            usage && exit 1
            ;;
        *)
            usage && exit 1
            ;;
    esac
done

function dump_vars(){
    echo "Args...."
    echo "NAMESPACE=$NAMESPACE"
    echo "SERVICE_TYPE=$SERVICE_TYPE"
    echo "DEBUG=$DEBUG"
    echo "Versions...."
    echo "V_OPERATOR=$V_OPERATOR"
    echo "V_MONGODB_EXPORTER=$V_MONGODB_EXPORTER"
    echo "V_MYSQL_EXPORTER=$V_MYSQL_EXPORTER"
}

if [ -n "$SERVICE_TYPE" ] ; then
    if [ [ $SERVICE_TYPE != "ClusterIP" ] || [ $SERVICE_TYPE != "NodePort" ] || [ $SERVICE_TYPE != "LoadBalancer" ] ] ; then
        echo "Wrong service type..."
    usage && exit 1
    fi
else
    SERVICE_TYPE="NodePort"
fi

if [ -n "$DEBUG" ] ; then
    set -x
fi

if [ -n "$DUMP_VARS" ] ; then
    dump_vars
fi

# Check if helm is installed
helm > /dev/null 2>&1
if [ $? != 0 ] ; then
    echo "Helm is not installed, installing ....."
    curl https://get.helm.sh/helm-v2.15.2-linux-amd64.tar.gz --output helm-v2.15.2.tar.gz
    tar -zxvf helm-v2.15.2.tar.gz
    sudo mv linux-amd64/helm /usr/local/bin/helm
    rm -r linux-amd64
    rm helm-v2.15.2.tar.gz
fi

echo "Checking if helm-tiller is installed..."
kubectl --namespace kube-system get serviceaccount tiller > /dev/null 2>&1
if [ $? == 1 ] ; then
    # tiller account for kubernetes
    kubectl --namespace kube-system create serviceaccount tiller
    kubectl create clusterrolebinding tiller-cluster-rule --clusterrole=cluster-admin --serviceaccount=kube-system:tiller
    # HELM initialization
    helm init --stable-repo-url https://charts.helm.sh/stable --service-account tiller

    # Wait for Tiller to be up and running
    while true
    do
    tiller_status=`kubectl -n kube-system get deployment.apps/tiller-deploy --no-headers |  awk '{print $2'}`
        if  [ ! -z "$tiller_status" ]
        then
            if [ $tiller_status == "1/1" ]
            then
                echo "Go...."
                break
            fi
        fi
        echo "Waiting for tiller READY...."
        sleep 2
    done
fi

# create monitoring namespace
echo "Creating namespace $NAMESPACE"
kubectl create namespace $NAMESPACE

# Prometheus operator installation
$HERE/change-charts-prometheus-operator.sh
echo "Creating stable/prometheus-operator"
helm install --namespace $NAMESPACE --version=$V_OPERATOR --name osm-monitoring --set kubelet.serviceMonitor.https=true,prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false,alertmanager.service.type=$SERVICE_TYPE,prometheus.service.type=$SERVICE_TYPE,grafana.serviceMonitor.selfMonitor=false $HERE/helm_charts/prometheus-operator

# Exporters installation

# MongoDB
# exporter
echo "Creating stable/prometheus-mongodb-exporter"
helm install --namespace $NAMESPACE --version=$V_MONGODB_EXPORTER --name osm-mongodb-exporter --set image.tag='0.10.0',mongodb.uri='mongodb://mongodb-k8s.osm:27017' stable/prometheus-mongodb-exporter
#dashboard:
kubectl -n $NAMESPACE apply -f $HERE/mongodb-exporter-dashboard.yaml

# Mysql
# exporter
echo "Creating stable/prometheus-mysql-exporter"
helm install --namespace $NAMESPACE --version=$V_MYSQL_EXPORTER --name osm-mysql-exporter --set serviceMonitor.enabled=true,mysql.user="root",mysql.pass=`kubectl -n osm get secret ro-db-secret -o yaml | grep MYSQL_ROOT_PASSWORD | awk '{print $2}' | base64 -d`,mysql.host="mysql.osm",mysql.port="3306" stable/prometheus-mysql-exporter
#dashboard:
kubectl -n $NAMESPACE apply -f $HERE/mysql-exporter-dashboard.yaml

# Kafka
# exporter
helm install --namespace $NAMESPACE --name osm-kafka-exporter $HERE/helm_charts/prometheus-kafka-exporter
# dashboard:
kubectl -n $NAMESPACE apply -f $HERE/kafka-exporter-dashboard.yaml

# Deploy summary dashboard
kubectl -n $NAMESPACE apply -f $HERE/summary-dashboard.yaml

# Deploy nodes dashboards
kubectl -n $NAMESPACE apply -f $HERE/nodes-dashboard.yaml

