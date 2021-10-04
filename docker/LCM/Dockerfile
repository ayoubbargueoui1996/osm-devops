##
# Copyright 2019 ETSI
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
##

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
    apt-transport-https=1.6.12ubuntu0.2 \
    gnupg2=2.2.4-1ubuntu1.4 \
    openssh-client

RUN curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - \
    && echo "deb https://apt.kubernetes.io/ kubernetes-xenial main" | tee -a /etc/apt/sources.list.d/kubernetes.list \
    && apt-get update && apt-get install -y kubectl=1.20.4-00

RUN curl https://get.helm.sh/helm-v2.17.0-linux-amd64.tar.gz --output helm-v2.17.0.tar.gz \
    && tar -zxvf helm-v2.17.0.tar.gz \
    && mv linux-amd64/helm /usr/local/bin/helm \
    && rm -r linux-amd64/

RUN curl https://get.helm.sh/helm-v3.3.4-linux-amd64.tar.gz --output helm-v3.3.4.tar.gz \
    && tar -zxvf helm-v3.3.4.tar.gz \
    && mv linux-amd64/helm /usr/local/bin/helm3 \
    && rm -r linux-amd64/


ARG PYTHON3_OSM_COMMON_URL
ARG PYTHON3_OSM_LCM_URL
ARG PYTHON3_N2VC_URL

RUN curl $PYTHON3_OSM_COMMON_URL -o osm_common.deb
RUN dpkg -i ./osm_common.deb

RUN curl $PYTHON3_OSM_LCM_URL -o osm_lcm.deb
RUN dpkg -i ./osm_lcm.deb

RUN curl $PYTHON3_N2VC_URL -o osm_n2vc.deb
RUN dpkg -i ./osm_n2vc.deb

RUN pip3 install \
    -r /usr/lib/python3/dist-packages/osm_common/requirements.txt \
    -r /usr/lib/python3/dist-packages/osm_lcm/requirements.txt \
    -r /usr/lib/python3/dist-packages/n2vc/requirements.txt

FROM ubuntu:18.04

RUN DEBIAN_FRONTEND=noninteractive apt-get --yes update && \
    DEBIAN_FRONTEND=noninteractive apt-get --yes install python3-minimal=3.6.7-1~18.04

RUN DEBIAN_FRONTEND=noninteractive apt-get --yes install \
    ca-certificates

COPY --from=INSTALL /usr/lib/python3/dist-packages /usr/lib/python3/dist-packages
COPY --from=INSTALL /usr/local/lib/python3.6/dist-packages  /usr/local/lib/python3.6/dist-packages

COPY --from=INSTALL /usr/bin/kubectl /usr/bin/kubectl
COPY --from=INSTALL /usr/local/bin/helm /usr/local/bin/helm
COPY --from=INSTALL /usr/local/bin/helm3 /usr/local/bin/helm3
COPY --from=INSTALL /usr/bin/scp /usr/bin/scp
COPY --from=INSTALL /usr/bin/ssh-keygen /usr/bin/ssh-keygen
COPY --from=INSTALL /usr/bin/ssh /usr/bin/ssh
COPY --from=INSTALL /usr/lib/x86_64-linux-gnu/ /usr/lib/x86_64-linux-gnu/
COPY --from=INSTALL /lib/x86_64-linux-gnu/ /lib/x86_64-linux-gnu/

########################################################################

# Used for local storage
VOLUME /app/storage
# Used for logs
VOLUME /app/log

# The following ENV can be added with "docker run -e xxx' to configure LCM
ENV OSMLCM_RO_HOST         ro
ENV OSMLCM_RO_PORT         9090
ENV OSMLCM_RO_TENANT       osm

# VCA
ENV OSMLCM_VCA_HOST        vca
ENV OSMLCM_VCA_PORT       17070
ENV OSMLCM_VCA_USER       admin
ENV OSMLCM_VCA_SECRET     secret
# ENV OSMLCM_VCA_PUBKEY     pubkey
# ENV OSMLCM_VCA_CACERT     cacert
# ENV OSMLCM_VCA_ENABLEOSUPGRADE false
# ENV OSMLCM_VCA_APTMIRROR  http://archive.ubuntu.com/ubuntu/

# database
ENV OSMLCM_DATABASE_DRIVER mongo
ENV OSMLCM_DATABASE_URI    mongodb://mongo:27017
#ENV OSMLCM_DATABASE_HOST    mongo
#ENV OSMLCM_DATABASE_PORT    27017


ENV OSMLCM_STORAGE_DRIVER  local
ENV OSMLCM_STORAGE_PATH    /app/storage

# message
ENV OSMLCM_MESSAGE_DRIVER  kafka
ENV OSMLCM_MESSAGE_HOST    kafka
ENV OSMLCM_MESSAGE_PORT    9092

# k8s
ENV OSMLCM_VCA_HELMPATH    /usr/local/bin/helm
ENV OSMLCM_VCA_KUBECTLPATH /usr/bin/kubectl
ENV OSMLCM_VCA_JUJUPATH    /usr/local/bin/juju

# helm
ENV OSMLCM_VCA_STABLEREPOURL https://charts.helm.sh/stable

# logs
# ENV OSMLCM_GLOBAL_LOGFILE  /app/log/lcm.log
# ENV OSMLCM_GLOBAL_LOGLEVEL DEBUG

HEALTHCHECK --start-period=120s --interval=30s --timeout=30s --retries=1 \
  CMD python3 -m osm_lcm.lcm_hc || exit 1


# Run app.py when the container launches
CMD python3 -m osm_lcm.lcm

