# Copyright 2020 Arctos Labs Scandinavia AB
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
ARG PYTHON3_OSM_PLA_URL

RUN curl $PYTHON3_OSM_COMMON_URL -o osm_common.deb
RUN dpkg -i ./osm_common.deb

RUN curl $PYTHON3_OSM_PLA_URL -o osm_pla.deb
RUN dpkg -i ./osm_pla.deb

RUN pip3 install \
    -r /usr/lib/python3/dist-packages/osm_common/requirements.txt \
    -r /usr/lib/python3/dist-packages/osm_pla/requirements.txt

ADD https://github.com/MiniZinc/MiniZincIDE/releases/download/2.4.2/MiniZincIDE-2.4.2-bundle-linux-x86_64.tgz /minizinc.tgz

RUN tar -zxf /minizinc.tgz && \
    mv /MiniZincIDE-2.4.2-bundle-linux /minizinc

FROM ubuntu:18.04
LABEL authors="Lars-Göran Magnusson"

RUN DEBIAN_FRONTEND=noninteractive apt-get --yes update && \
    DEBIAN_FRONTEND=noninteractive apt-get --yes install python3-minimal=3.6.7-1~18.04

COPY --from=INSTALL /usr/lib/python3/dist-packages /usr/lib/python3/dist-packages
COPY --from=INSTALL /usr/local/lib/python3.6/dist-packages  /usr/local/lib/python3.6/dist-packages
COPY --from=INSTALL /usr/bin/osm* /usr/bin/
COPY --from=INSTALL /minizinc /minizinc

RUN mkdir /entry_data \
    && mkdir /entry_data/mzn-lib \
    && ln -s /entry_data/mzn-lib /minizinc/share/minizinc/exec

COPY scripts/ scripts/
RUN mkdir /placement

ENV OSMPLA_MESSAGE_DRIVER kafka
ENV OSMPLA_MESSAGE_HOST kafka
ENV OSMPLA_MESSAGE_PORT 9092

ENV OSMPLA_DATABASE_DRIVER mongo
ENV OSMPLA_DATABASE_URI mongodb://mongo:27017

ENV OSMPLA_SQL_DATABASE_URI sqlite:///pla_sqlite.db

ENV OSMPLA_GLOBAL_LOG_LEVEL INFO

ENV FZNEXEC "/entry_data/fzn-exec"
ENV PATH "/minizinc/bin:${PATH}"
ENV LD_LIBRARY_PATH "/minizinc/lib:${LD_LIBRARY_PATH}"

# No healtcheck yet...
#HEALTHCHECK --start-period=120s --interval=10s --timeout=5s --retries=5 \
#  CMD osm-pla-healthcheck || exit 1

CMD /bin/bash scripts/start.sh
