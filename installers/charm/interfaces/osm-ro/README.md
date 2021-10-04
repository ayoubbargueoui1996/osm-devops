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

This interface layer handles communication between OSM's RO and its clients.

## Usage

### Provides

To implement this relation to offer an ro:

In your charm's metadata.yaml:

```yaml
provides:
    ro:
        interface: osm-ro
```

reactive/myro.py:

```python
@when('ro.joined')
def send_config(ro):
    ro.send_connection(
        unit_get('private-address'),
        get_ro_port()
    )
```

### Requires

If you would like to use a rodb from your charm:

metadata.yaml:

```yaml
requires:
    ro:
        interface: osm-ro
```

reactive/mycharm.py:

```python
@when('ro.ready')
def ro_ready():
    ro = endpoint_from_flag('ro.ready')
    if ro:
        for unit in ro.ros():
            add_ro(unit['host'], unit['port'])
```
