# Copyright 2018 Whitestack, LLC
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
#
# For those usages not covered by the Apache License, Version 2.0 please
# contact: esousa@whitestack.com or glavado@whitestack.com
##

FROM ubuntu:16.04

LABEL Maintainer="esousa@whitestack.com" \
      Description="Openstack Keystone Instance" \
      Version="1.0" \
      Author="Eduardo Sousa"

EXPOSE 5000

WORKDIR /keystone

COPY scripts/start.sh /keystone/start.sh

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get autoremove -y && \
    apt-get install -y software-properties-common && \
    add-apt-repository -y cloud-archive:pike && \
    apt-get update && apt dist-upgrade -y && \
    apt-get install -y python-openstackclient keystone apache2 libapache2-mod-wsgi net-tools mysql-client dnsutils && \
    apt-get install -y python-pip build-essential python-dev libldap2-dev libsasl2-dev libssl-dev libffi-dev libxml2-dev libxslt1-dev zlib1g-dev ldap-utils && \
    pip install python-ldap ldappool && \
    rm -rf /var/lib/apt/lists/* && \
    chmod +x start.sh

# database
ENV DB_HOST                 keystone-db
ENV DB_PORT                 3306
ENV ROOT_DB_USER            root
ENV ROOT_DB_PASSWORD        admin
ENV KEYSTONE_DB_PASSWORD    admin
# keystone
ENV REGION_ID               RegionOne
ENV KEYSTONE_HOST           keystone
# admin user
ENV ADMIN_USERNAME          admin
ENV ADMIN_PASSWORD          admin
ENV ADMIN_PROJECT           admin
# nbi service user
ENV SERVICE_USERNAME        nbi
ENV SERVICE_PASSWORD        nbi
ENV SERVICE_PROJECT         service
# ldap
# ENV LDAP_AUTHENTICATION_DOMAIN_NAME     no default
# ENV LDAP_URL                            ldap://localhost
# ENV LDAP_BIND_USER                      no default
# ENV LDAP_BIND_PASSWORD                  no default
# ENV LDAP_CHASE_REFERRALS                no default
# ENV LDAP_PAGE_SIZE                      0
# ENV LDAP_USER_TREE_DN                   no default
# ENV LDAP_USER_OBJECTCLASS               inetOrgPerson
# ENV LDAP_USER_ID_ATTRIBUTE              cn
# ENV LDAP_USER_NAME_ATTRIBUTE            sn
# ENV LDAP_USER_PASS_ATTRIBUTE            userPassword
# ENV LDAP_USER_FILTER                    no default
# ENV LDAP_USER_ENABLED_ATTRIBUTE         enabled
# ENV LDAP_USER_ENABLED_MASK              0
# ENV LDAP_USER_ENABLED_DEFAULT           true
# ENV LDAP_USER_ENABLED_INVERT            false
# ENV LDAP_GROUP_OBJECTCLASS              groupOfNames
# ENV LDAP_GROUP_TREE_DN                  no default
# ENV LDAP_USE_STARTTLS                   false
# ENV LDAP_TLS_CACERT_BASE64              no default
# ENV LDAP_TLS_REQ_CERT                   demand

ENTRYPOINT ./start.sh
