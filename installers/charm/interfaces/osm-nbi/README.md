<!--
Copyright 2020 Canonical Ltd.
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
    http://www.apache.org/licenses/LICENSE-2.0
    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License. -->

# Overview

This interface layer handles communication between Mongodb and its clients.

## Usage

### Provides

To implement this relation to offer an nbi:

In your charm's metadata.yaml:

```yaml
provides:
    nbi:
        interface: osm-nbi
```

reactive/mynbi.py:

```python
@when('nbi.joined')
def send_config(nbi):
    nbi.send_connection(
        unit_get('private-address'),
        get_nbi_port()
    )
```

### Requires

If you would like to use an nbi from your charm:

metadata.yaml:

```yaml
requires:
    nbi:
        interface: osm-nbi
```

reactive/mycharm.py:

```python
@when('nbi.ready')
def nbi_ready():
    nbi = endpoint_from_flag('nbi.ready')
    if nbi:
        for unit in nbi.nbis():
            add_nbi(unit['host'], unit['port'])
```
