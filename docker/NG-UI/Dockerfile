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

FROM ubuntu:18.04

RUN DEBIAN_FRONTEND=noninteractive apt-get --yes update && \
    DEBIAN_FRONTEND=noninteractive apt-get --yes install \
    apt-transport-https=1.6.12ubuntu0.2 \
    curl=7.58.0-2ubuntu3.13 \
    gnupg2=2.2.4-1ubuntu1.4 \
    nginx=1.14.0-0ubuntu1.9 \
    software-properties-common=0.96.24.32.14 \
    xz-utils=5.2.2-1.3

RUN curl -s https://deb.nodesource.com/gpgkey/nodesource.gpg.key | apt-key add - && \
    echo "deb https://deb.nodesource.com/node_10.x xenial main" | tee -a /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y nodejs=10.24.1-1nodesource1

ARG OSM_NGUI_URL

RUN curl $OSM_NGUI_URL -o osm_ngui.deb
RUN dpkg -i ./osm_ngui.deb

WORKDIR /usr/share/osm-ngui
RUN npm install

# Building app.
RUN npm run build
RUN cp /usr/share/osm-ngui/nginx/nginx.conf /etc/nginx/sites-available/default

# Removing the Nginx default page.
RUN rm -rf /usr/share/nginx/html/*

# Copying angular build to Nginx default page.
RUN cp -r /usr/share/osm-ngui/dist/osm/* /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --start-period=130s --interval=10s --timeout=5s --retries=12 \
  CMD curl --silent --fail localhost:80 || exit 1

# Starting server.
CMD ["nginx", "-g", "daemon off;"]
