#!/usr/bin/env bash

##
# Copyright 2019 ETSI
#
# All Rights Reserved.
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


# Set the Juju env variables for building a layer
export JUJU_REPOSITORY=`pwd`
export INTERFACE_PATH=$JUJU_REPOSITORY/interfaces
export LAYER_PATH=$JUJU_REPOSITORY/layers
