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
    genisoimage=9:1.1.11-3ubuntu2 netbase=5.4

ARG PYTHON3_OSM_COMMON_URL
ARG PYTHON3_OSM_NG_RO_URL
ARG PYTHON3_OSM_RO_PLUGIN_URL
ARG PYTHON3_OSM_ROSDN_ARISTA_CLOUDVISION_URL
ARG PYTHON3_OSM_ROSDN_DPB_URL
ARG PYTHON3_OSM_ROSDN_DYNPAC_URL
ARG PYTHON3_OSM_ROSDN_FLOODLIGHTOF_URL
ARG PYTHON3_OSM_ROSDN_IETFL2VPN_URL
ARG PYTHON3_OSM_ROSDN_JUNIPER_CONTRAIL_URL
ARG PYTHON3_OSM_ROSDN_ODLOF_URL
ARG PYTHON3_OSM_ROSDN_ONOSOF_URL
ARG PYTHON3_OSM_ROSDN_ONOS_VPLS_URL
ARG PYTHON3_OSM_ROVIM_AWS_URL
ARG PYTHON3_OSM_ROVIM_AZURE_URL
ARG PYTHON3_OSM_ROVIM_FOS_URL
ARG PYTHON3_OSM_ROVIM_OPENNEBULA_URL
ARG PYTHON3_OSM_ROVIM_OPENSTACK_URL
ARG PYTHON3_OSM_ROVIM_OPENVIM_URL
ARG PYTHON3_OSM_ROVIM_VMWARE_URL

RUN for URL in \
    $PYTHON3_OSM_COMMON_URL \
    $PYTHON3_OSM_NG_RO_URL \
    $PYTHON3_OSM_RO_PLUGIN_URL \
    $PYTHON3_OSM_ROSDN_ARISTA_CLOUDVISION_URL \
    $PYTHON3_OSM_ROSDN_DPB_URL \
    $PYTHON3_OSM_ROSDN_DYNPAC_URL \
    $PYTHON3_OSM_ROSDN_FLOODLIGHTOF_URL \
    $PYTHON3_OSM_ROSDN_IETFL2VPN_URL \
    $PYTHON3_OSM_ROSDN_JUNIPER_CONTRAIL_URL \
    $PYTHON3_OSM_ROSDN_ODLOF_URL \
    $PYTHON3_OSM_ROSDN_ONOSOF_URL \
    $PYTHON3_OSM_ROSDN_ONOS_VPLS_URL \
    $PYTHON3_OSM_ROVIM_AWS_URL \
    $PYTHON3_OSM_ROVIM_AZURE_URL \
    $PYTHON3_OSM_ROVIM_FOS_URL \
    $PYTHON3_OSM_ROVIM_OPENNEBULA_URL \
    $PYTHON3_OSM_ROVIM_OPENSTACK_URL \
    $PYTHON3_OSM_ROVIM_OPENVIM_URL \
    $PYTHON3_OSM_ROVIM_VMWARE_URL ; do \
        curl -s $URL -O ; \
    done

RUN dpkg -i *.deb

RUN pip3 install \
    -r /usr/lib/python3/dist-packages/osm_common/requirements.txt \
    -r /usr/lib/python3/dist-packages/osm_ng_ro/requirements.txt

FROM ubuntu:18.04

RUN DEBIAN_FRONTEND=noninteractive apt-get --yes update && \
    DEBIAN_FRONTEND=noninteractive apt-get --yes install python3-minimal=3.6.7-1~18.04

COPY --from=INSTALL /usr/lib/python3/dist-packages /usr/lib/python3/dist-packages
COPY --from=INSTALL /usr/local/lib/python3.6/dist-packages  /usr/local/lib/python3.6/dist-packages
COPY --from=INSTALL /usr/bin/genisoimage /usr/bin/genisoimage
COPY --from=INSTALL /etc/protocols /etc/protocols

VOLUME /var/log/osm

EXPOSE 9090

# Two mysql databases are needed (DB and DB_OVIM). Can be hosted on same or separated containers
# These ENV must be provided
ENV RO_DB_HOST=""
ENV RO_DB_OVIM_HOST=""
    # if empty RO_DB_HOST is assumed

# These ENV should be provided first time for creating database. It will create and init only if empty!
ENV RO_DB_ROOT_PASSWORD=""
ENV RO_DB_OVIM_ROOT_PASSWORD=""
    # if empty RO_DB_ROOT_PASSWORD is assumed

# These ENV can be provided, but default values are ok
ENV RO_DB_USER=mano
ENV RO_DB_OVIM_USER=mano
ENV RO_DB_PASSWORD=manopw
ENV RO_DB_OVIM_PASSWORD=manopw
ENV RO_DB_PORT=3306
ENV RO_DB_OVIM_PORT=3306
ENV RO_DB_NAME=mano_db
ENV RO_DB_OVIM_NAME=mano_vim_db
ENV OPENMANO_TENANT=osm

# database
ENV OSMRO_DATABASE_DRIVER mongo
ENV OSMRO_DATABASE_URI mongodb://mongo:27017
# ENV OSMRO_DATABASE_COMMONKEY  xxx
# ENV OSMRO_DATABASE_USER  xxx
# ENV OSMRO_DATABASE_PASSWORD  xxx

# message
ENV OSMRO_MESSAGE_DRIVER  kafka
ENV OSMRO_MESSAGE_HOST    kafka
ENV OSMRO_MESSAGE_PORT    9092

# logs
ENV OSMRO_LOG_LEVEL       INFO

HEALTHCHECK --start-period=130s --interval=10s --timeout=5s --retries=12 \
  CMD curl --silent --fail http://localhost:9090/ro || exit 1

CMD ["python3", "-u", "-m", "osm_ng_ro.ro_main"]

