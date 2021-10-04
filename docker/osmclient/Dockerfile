#######################################################################################
# Copyright ETSI Contributors and Others.
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
#######################################################################################

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
    libcurl4-openssl-dev=7.58.0-2ubuntu3.13 \
    libssl-dev=1.1.1-1ubuntu2.1~18.04.9

ARG PYTHON3_OSMCLIENT_URL
ARG PYTHON3_OSM_IM_URL

RUN curl $PYTHON3_OSMCLIENT_URL -o osmclient.deb
RUN dpkg -i ./osmclient.deb

RUN curl $PYTHON3_OSM_IM_URL -o osm_im.deb
RUN dpkg -i ./osm_im.deb

RUN pip3 install \
    -r /usr/lib/python3/dist-packages/osmclient/requirements.txt \
    -r /usr/lib/python3/dist-packages/osm_im/requirements.txt

FROM ubuntu:18.04 as FINAL

RUN DEBIAN_FRONTEND=noninteractive apt-get --yes update && \
    DEBIAN_FRONTEND=noninteractive apt-get --yes install python3-minimal=3.6.7-1~18.04

COPY --from=INSTALL /usr/lib/python3/dist-packages /usr/lib/python3/dist-packages
COPY --from=INSTALL /usr/local/lib/python3.6/dist-packages  /usr/local/lib/python3.6/dist-packages

ENV OSM_SOL005=True
ENV OSM_HOSTNAME=nbi:9999
