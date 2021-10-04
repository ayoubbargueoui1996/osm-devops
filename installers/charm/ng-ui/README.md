<!-- #   Copyright 2020 Canonical Ltd.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License. -->

# NG-UI Charm

## How to deploy

```bash
juju deploy . # cs:~charmed-osm/ng-ui --channel edge
juju relate ng-ui nbi
```

## How to expose the NG-UI through ingress

```bash
juju config ng-ui site_url=ng.<k8s_worker_ip>.xip.io
juju expose ng-ui
```

> Note: The <k8s_worker_ip> is the IP of the K8s worker node. With microk8s, you can see the IP with `microk8s.config`. It is usually the IP of your host machine.

## How to scale

```bash
    juju scale-application ng-ui 3
```


## Config Examples

```bash
juju config ng-ui image=opensourcemano/ng-ui:<tag>
juju config ng-ui port=80
juju config server_name=<name>
juju config max_file_size=25
```
