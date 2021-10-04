# Copyright 2020 ETSI
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

########################################################################

FROM ubuntu:18.04 as INSTALL

RUN DEBIAN_FRONTEND=noninteractive apt-get --yes update && \
    DEBIAN_FRONTEND=noninteractive apt-get --yes install \
    gcc=4:7.4.0-1ubuntu2.3 \
    python3=3.6.7-1~18.04 \
    python3-dev=3.6.7-1~18.04 \
    python3-setuptools=39.0.1-2 \
    curl=7.58.0-2ubuntu3.13 && \
    python3 -m easy_install pip==21.0.1

RUN DEBIAN_FRONTEND=noninteractive apt-get --yes install \
    gettext-base \
    git=1:2.17.1-1ubuntu0.8 \
    iputils-ping=3:20161105-1ubuntu3 \
    jq=1.5+dfsg-2 \
    libcurl4-openssl-dev=7.58.0-2ubuntu3.13 \
    libssl-dev=1.1.1-1ubuntu2.1~18.04.9

ARG OSM_TESTS_URL
ARG PYTHON3_OSM_IM_URL
ARG PYTHON3_OSMCLIENT_URL

# Installing Juju
ARG JUJU_VERSION_M=2.8
ARG JUJU_VERSION_R=11
ARG JUJU_VERSION=$JUJU_VERSION_M.$JUJU_VERSION_R

RUN curl --output /tmp/juju-$JUJU_VERSION-linux-amd64.tar.xz -LO \
    https://launchpad.net/juju/$JUJU_VERSION_M/$JUJU_VERSION/+download/juju-$JUJU_VERSION-linux-amd64.tar.xz && \
    tar -xf /tmp/juju-$JUJU_VERSION-linux-amd64.tar.xz -C /tmp && \
    install /tmp/juju /usr/local/bin/juju && \
    rm /tmp/juju /tmp/juju-$JUJU_VERSION-linux-amd64.tar.xz

RUN curl $PYTHON3_OSM_IM_URL -o osm_im.deb
RUN dpkg -i ./osm_im.deb

RUN curl $PYTHON3_OSMCLIENT_URL -o osmclient.deb
RUN dpkg -i ./osmclient.deb

RUN curl $OSM_TESTS_URL -o osm_tests.deb
RUN dpkg -i ./osm_tests.deb

RUN pip3 install \
    -r /usr/lib/python3/dist-packages/osm_im/requirements.txt \
    -r /usr/lib/python3/dist-packages/osmclient/requirements.txt \
    -r /usr/share/osm-tests/requirements.txt

RUN mv /usr/share/osm-tests/robot-systest /robot-systest
RUN mv /usr/share/osm-tests/charm.sh /usr/sbin/charm

RUN git clone \
    https://osm.etsi.org/gitlab/vnf-onboarding/osm-packages.git \
    --recurse-submodules \
    /robot-systest/osm-packages

WORKDIR /robot-systest

# Folder where Robot tests are stored
ENV ROBOT_DEVOPS_FOLDER=/robot-systest

# Folder to save alternative DUT environments (optional)
ENV ENVIRONMENTS_FOLDER=environments

# Folder where all required packages are stored
ENV PACKAGES_FOLDER=/robot-systest/osm-packages

# Folder where test results should be exported
ENV ROBOT_REPORT_FOLDER=/robot-systest/results

# Kubeconfig file
ENV K8S_CREDENTIALS=/root/.kube/config

# Juju data folder
ENV JUJU_DATA=/root/.local/share/juju

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

ENTRYPOINT [ "/robot-systest/run_test.sh"]
