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

ARG PYTHON3_OSM_COMMON_URL
ARG PYTHON3_OSM_IM_URL
ARG PYTHON3_OSM_NBI_URL

RUN curl $PYTHON3_OSM_COMMON_URL -o osm_common.deb
RUN dpkg -i ./osm_common.deb

RUN curl $PYTHON3_OSM_IM_URL -o osm_im.deb
RUN dpkg -i ./osm_im.deb

RUN curl $PYTHON3_OSM_NBI_URL -o osm_nbi.deb
RUN dpkg -i ./osm_nbi.deb

RUN pip3 install \
    -r /usr/lib/python3/dist-packages/osm_common/requirements.txt \
    -r /usr/lib/python3/dist-packages/osm_im/requirements.txt \
    -r /usr/lib/python3/dist-packages/osm_nbi/requirements.txt

FROM ubuntu:18.04 as FINAL

RUN DEBIAN_FRONTEND=noninteractive apt-get --yes update && \
    DEBIAN_FRONTEND=noninteractive apt-get --yes install python3-minimal=3.6.7-1~18.04

COPY --from=INSTALL /usr/lib/python3/dist-packages /usr/lib/python3/dist-packages
COPY --from=INSTALL /usr/local/lib/python3.6/dist-packages  /usr/local/lib/python3.6/dist-packages

RUN mkdir -p /app/storage/kafka && mkdir -p /app/log

WORKDIR /app/osm_nbi

EXPOSE 9999

RUN cp -R /usr/lib/python3/dist-packages/osm_nbi/html_public /app/osm_nbi/html_public
RUN cp /usr/lib/python3/dist-packages/osm_nbi/nbi.cfg /app/osm_nbi/
RUN cp -R /usr/lib/python3/dist-packages/osm_nbi/http /app/osm_nbi/

# Used for local storage
VOLUME /app/storage
# Used for logs
VOLUME /app/log

# The following ENV can be added with "docker run -e xxx' to configure
# server
ENV OSMNBI_SOCKET_HOST     0.0.0.0
ENV OSMNBI_SOCKET_PORT     9999
ENV OSMNBI_SERVER_SSL_CERTIFICATE               /app/osm_nbi/http/cert.pem
ENV OSMNBI_SERVER_SSL_PRIVATE_KEY               /app/osm_nbi/http/privkey.pem
# storage
ENV OSMNBI_STORAGE_PATH    /app/storage
# database
ENV OSMNBI_DATABASE_DRIVER mongo
ENV OSMNBI_DATABASE_URI   mongodb://mongo:27017
#ENV OSMNBI_DATABASE_HOST   mongo
#ENV OSMNBI_DATABASE_PORT   27017

# web
ENV OSMNBI_STATIC_DIR      /app/osm_nbi/html_public
# message
ENV OSMNBI_MESSAGE_DRIVER  kafka
ENV OSMNBI_MESSAGE_HOST    kafka
ENV OSMNBI_MESSAGE_PORT    9092
# logs
ENV OSMNBI_LOG_FILE        /app/log/nbi.log
ENV OSMNBI_LOG_LEVEL       DEBUG
# authentication
ENV OSMNBI_AUTHENTICATION_BACKEND               internal
#ENV OSMNBI_AUTHENTICATION_BACKEND               keystone
#ENV OSMNBI_AUTHENTICATION_AUTH_URL              keystone
#ENV OSMNBI_AUTHENTICATION_AUTH_PORT             5000
#ENV OSMNBI_AUTHENTICATION_USER_DOMAIN_NAME      default
#ENV OSMNBI_AUTHENTICATION_PROJECT_DOMAIN_NAME   default
#ENV OSMNBI_AUTHENTICATION_SERVICE_USERNAME      nbi
#ENV OSMNBI_AUTHENTICATION_SERVICE_PASSWORD      nbi
#ENV OSMNBI_AUTHENTICATION_SERVICE_PROJECT       service
#prometheus
ENV OSMNBI_PROMETHEUS_HOST                      prometheus
ENV OSMNBI_PROMETHEUS_PORT                      9090

HEALTHCHECK --start-period=120s --interval=10s --timeout=5s --retries=5 \
  CMD curl -k https://localhost:9999/osm/ | grep Welcome || exit 1

# Run app.py when the container launches
CMD python3 -m osm_nbi.nbi

