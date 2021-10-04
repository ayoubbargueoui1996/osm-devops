#!/bin/sh

# Copyright 2019 ETSI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

WAIT_TIME=340  # LCM healthcheck needs 2x(30+140) senconds
SERVICES_WITH_HEALTH="nbi ro zookeeper lcm mon pol kafka"
NUM_SERVICES_WITH_HEALTH=$(echo $SERVICES_WITH_HEALTH | wc -w)
WAIT_FINAL=30
OSM_DEPLOYMENT="nbi lcm ro mon pol keystone"
OSM_STATEFULSET="zookeeper kafka mongo mysql prometheus"
NUM_K8S_PODS=$(echo $OSM_DEPLOYMENT $OSM_STATEFULSET | wc -w)

while getopts "w:s:n:c:k" o; do
    case "${o}" in
        w)
            WAIT_TIME=${OPTARG}
            ;;
        s)
            STACK_NAME=${OPTARG}
            ;;
        n)
            NUM_SERVICES_WITH_HEALTH=${OPTARG}
            ;;
        c)
            SERVICES_WITH_HEALTH="${OPTARG}"
            ;;
        k)
            KUBERNETES="y"
            ;;
    esac
done


time=0
step=2
while [ $time -le "$WAIT_TIME" ]; do
    if [ -n "$KUBERNETES" ]; then
        if [ "$(kubectl get pods -n "${STACK_NAME}" | grep -i running | wc -l)" -ge "$NUM_K8S_PODS" ]; then
            #all pods are running now.
            sleep $WAIT_FINAL
            exit 0
        fi
    else
        if [ "$(sg docker -c "docker ps" | grep " ${STACK_NAME}_" | grep -i healthy | wc -l)" -ge "$NUM_SERVICES_WITH_HEALTH" ]; then
            # all dockers are healthy now.
            # final sleep is needed until more health checks are added to validate system is ready to handle requests
            sleep $WAIT_FINAL
            exit 0
        fi
    fi

    sleep $step
    time=$((time+step))
done

if [ -n "$KUBERNETES" ]; then
    echo "Not all pods are running"
    kubectl get pods -n "${STACK_NAME}"
    for POD in $OSM_DEPLOYMENT $OSM_STATEFULSET; do
        kubectl get pods -n "${STACK_NAME}" | grep -i running | grep -q ^"${POD}-" && continue
        echo
        echo BEGIN LOGS of pods ${POD} not running
        LOG_POD=$(kubectl get pods -n "${STACK_NAME}" | grep -e ^"${POD}-" | awk '{print $1}' )
        [ -z "$LOG_POD" ] && echo "${POD} Failed to deploy" || kubectl logs ${LOG_POD} -n $STACK_NAME 2>&1 | tail -n 100
        echo END LOGS of services $POD not running
    done
else
    echo "Not all Docker services are healthy"
    sg docker -c "docker ps" | grep " ${STACK_NAME}_"
    for S_WITH_HEALTH in $SERVICES_WITH_HEALTH ; do
        sg docker -c "docker ps" | grep " ${STACK_NAME}_" | grep -i healthy | grep -q "_${S_WITH_HEALTH}."  && continue
        echo
        echo BEGIN LOGS of container ${S_WITH_HEALTH} not healthy
        sg docker -c "docker service logs ${STACK_NAME}_${S_WITH_HEALTH} 2>&1" | tail -n 100
        echo END LOGS of container ${S_WITH_HEALTH} not healthy
        echo
    done
fi

exit 1
