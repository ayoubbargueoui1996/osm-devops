# Copyright 2018 Whitestack, LLC
# *************************************************************

# This file is part of OSM Monitoring module
# All Rights Reserved to Whitestack, LLC

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at

#         http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# For those usages not covered by the Apache License, Version 2.0 please
# contact: bdiaz@whitestack.com or glavado@whitestack.com
##

FROM ubuntu:20.04 as INSTALL

RUN DEBIAN_FRONTEND=noninteractive apt-get --yes update && \
    DEBIAN_FRONTEND=noninteractive apt-get --yes install \
    curl=7.68.0-1ubuntu2.5 \
    gcc=4:9.3.0-1ubuntu2 \
    python3=3.8.2-0ubuntu2 \
    python3-setuptools=45.2.0-1 \
    python3-dev=3.8.2-0ubuntu2 && \
    python3 -m easy_install pip==21.0.1

RUN DEBIAN_FRONTEND=noninteractive apt-get --yes install \
    mysql-client-core-8.0=8.0.25-0ubuntu0.20.04.1

ARG PYTHON3_OSM_COMMON_URL
ARG PYTHON3_OSM_POLICY_MODULE_URL

RUN curl $PYTHON3_OSM_COMMON_URL -o osm_common.deb
RUN dpkg -i ./osm_common.deb

RUN curl $PYTHON3_OSM_POLICY_MODULE_URL -o osm_policy_module.deb
RUN dpkg -i ./osm_policy_module.deb

RUN pip3 install \
    -r /usr/lib/python3/dist-packages/osm_common/requirements.txt \
    -r /usr/lib/python3/dist-packages/osm_policy_module/requirements.txt

FROM ubuntu:20.04 as FINAL

RUN DEBIAN_FRONTEND=noninteractive apt-get --yes update && \
    DEBIAN_FRONTEND=noninteractive apt-get --yes install python3-minimal=3.8.2-0ubuntu2

COPY --from=INSTALL /usr/lib/python3/dist-packages /usr/lib/python3/dist-packages
COPY --from=INSTALL /usr/local/lib/python3.8/dist-packages  /usr/local/lib/python3.8/dist-packages
COPY --from=INSTALL /usr/bin/osm* /usr/bin/
COPY --from=INSTALL /usr/bin/mysql /usr/bin/
COPY --from=INSTALL /usr/bin/mysqladmin /usr/bin/
COPY --from=INSTALL /usr/bin/mysqlshow /usr/bin/
COPY --from=INSTALL /usr/lib/x86_64-linux-gnu/libedit.so.2 /usr/lib/x86_64-linux-gnu/
COPY --from=INSTALL /usr/lib/x86_64-linux-gnu/libbsd.so.0 /usr/lib/x86_64-linux-gnu/

COPY scripts/ scripts/

ENV OSMPOL_MESSAGE_DRIVER kafka
ENV OSMPOL_MESSAGE_HOST kafka
ENV OSMPOL_MESSAGE_PORT 9092

ENV OSMPOL_DATABASE_DRIVER mongo
ENV OSMPOL_DATABASE_URI mongodb://mongo:27017

ENV OSMPOL_SQL_DATABASE_URI sqlite:///mon_sqlite.db

ENV OSMPOL_GLOBAL_LOG_LEVEL INFO

HEALTHCHECK --start-period=120s --interval=10s --timeout=5s --retries=5 \
  CMD osm-pol-healthcheck || exit 1

CMD /bin/bash scripts/start.sh
