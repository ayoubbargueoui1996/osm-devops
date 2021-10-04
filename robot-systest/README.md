<!--
 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
-->

# Robot Framework: Test usage

## Requirements

- OSM client installed (<https://osm.etsi.org/docs/user-guide/03-installing-osm.html#installing-standalone-osm-client>)
- devops repository cloned in home (<https://osm.etsi.org/gerrit/#/admin/projects/osm/devops>)
- The descriptor packages used on each test are expected to be in `${PACKAGES_FOLDER}`.
- A set of environment variables (there is an example file located at devops/robot-systest/environment.rc):
  - `OSM_HOSTNAME`: IP address of target OSM.
  - `OS_CLOUD`: Cloud credentialss.
  - `VIM_TARGET`: VIM where tests will be run.
  - `VIM_MGMT_NET`: VIM management network, reachable from robot.
  - `PACKAGES_FOLDER`: Path where descriptor packages repository are cloned: https://osm.etsi.org/gitlab/vnf-onboarding/osm-packages/
  - `ROBOT_DEVOPS_FOLDER`: Where the devops repository is located.
  - `ROBOT_REPORT_FOLDER`: Where robot outpul will be placed.

## Installation

```bash
sudo -H python3 -m pip install --ignore-installed haikunator requests pyvcloud progressbar pathlib robotframework robotframework-seleniumlibrary robotframework-requests robotframework-SSHLibrary
sudo snap install yq
sudo apt-get install -y python3-openstackclient  # Installs Queens by default
```

## Usage

Example using hackfest basic test. 

```bash

# Set your environment variables in environment.rc as specified in requirements
source environment.rc

cd ~/devops/robot-systest
robot -d ${ROBOT_REPORT_FOLDER} testsuite/hackfest_basic.robot
```
