<!-- Copyright 2021 Canonical Ltd.

Licensed under the Apache License, Version 2.0 (the "License"); you may
not use this file except in compliance with the License. You may obtain
a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.

For those usages not covered by the Apache License, Version 2.0 please
contact: legal@canonical.com

To get in touch with the maintainers, please contact:
osm-charmers@lists.launchpad.net -->

# Overview

Mongo for Juju CAAS

## Actions

### Backup

Execute the following steps to do a backup.

```bash
$ juju run-action mongodb-k8s/0 backup --wait
unit-mongodb-k8s-0:
  UnitId: mongodb-k8s/0
  id: "7"
  results:
    Stderr: "2020-02-26T14:13:56.448+0000\twriting admin.system.version to archive
      '/data/backup.archive'\n2020-02-26T14:13:56.451+0000\tdone dumping admin.system.version
      (1 document)\n"
    copy:
      cmd: kubectl cp mongo-ha/mongodb-k8s-0:/data/backup.archive backup.archive
    restore:
      cmd: kubectl cp backup.archive mongo-ha/mongodb-k8s-0:/data/backup.archive
      juju: juju action mongodb-k8s/0 restore --wait
  status: completed
  timing:
    completed: 2020-02-26 14:13:57 +0000 UTC
    enqueued: 2020-02-26 14:13:55 +0000 UTC
    started: 2020-02-26 14:13:56 +0000 UTC
$ kubectl cp mongo-ha/mongodb-k8s-0:/data/backup.archive backup.archive
```

> Additional note: You can add `--string-args target=PRIMARY|SECONDARY` if you want this action to be run in a specific mongo unit. If `SECONDARY` is set, but the mongo unit isn't the `SECONDARY`, the action will fail.

### Restore

When the backup function is executed, you will see the commands you need to execute for restoring from a backup.

```bash
$ kubectl cp backup.archive mongo-ha/mongodb-k8s-0:/data/backup.archive
Defaulting container name to mongodb-k8s.
$ juju run-action mongodb-k8s/0 restore --wait
unit-mongodb-k8s-0:
  UnitId: mongodb-k8s/0
  id: "8"
  results:
    Stderr: "2020-02-26T14:17:00.300+0000\tpreparing collections to restore from\n2020-02-26T14:17:00.312+0000\t0
      document(s) restored successfully. 0 document(s) failed to restore.\n"
  status: completed
  timing:
    completed: 2020-02-26 14:17:01 +0000 UTC
    enqueued: 2020-02-26 14:16:57 +0000 UTC
    started: 2020-02-26 14:17:00 +0000 UTC
```

### Remove backup

When a backup is made, it is stored in the unit. To easily remove the backup, execute this action:

```bash
$ juju run-action mongodb-k8s/0 remove-backup --wait
unit-mongodb-k8s-0:
  UnitId: mongodb-k8s/0
  id: "4"
  results:
    Stdout: |
      Backup successfully removed!
  status: completed
  timing:
    completed: 2020-02-26 16:31:11 +0000 UTC
    enqueued: 2020-02-26 16:31:08 +0000 UTC
    started: 2020-02-26 16:31:10 +0000 UTC
```

### Is primary?

To check if the unit is primary:

```bash
$ juju run-action mongodb-k8s/0 is-primary --wait
unit-mongodb-k8s-0:
  UnitId: mongodb-k8s/0
  id: "5"
  results:
    unit:
      ip: 10.1.31.92
      primary: "true"
  status: completed
  timing:
    completed: 2020-02-26 16:32:10 +0000 UTC
    enqueued: 2020-02-26 16:32:08 +0000 UTC
    started: 2020-02-26 16:32:09 +0000 UTC
$ juju run-action mongodb-k8s/1 is-primary --wait
unit-mongodb-k8s-1:
  UnitId: mongodb-k8s/1
  id: "6"
  results:
    unit:
      ip: 10.1.31.93
      primary: "false"
  status: completed
  timing:
    completed: 2020-02-26 16:32:34 +0000 UTC
    enqueued: 2020-02-26 16:32:32 +0000 UTC
    started: 2020-02-26 16:32:33 +0000 UTC
```

## Backup remotely

If we want to perform a backup remotely, follow the next steps:

```bash
$ sudo apt install mongo-tools-y
$ juju status mongodb-k8s
Model     Controller          Cloud/Region        Version  SLA          Timestamp
mongo-ha  microk8s-localhost  microk8s/localhost  2.7.2    unsupported  16:26:02+01:00

App          Version       Status  Scale  Charm        Store  Rev  OS          Address        Notes
mongodb-k8s  mongo:latest  active      2  mongodb-k8s  local    0  kubernetes  10.152.183.90  

Unit            Workload  Agent  Address     Ports      Message
mongodb-k8s/0*  active    idle   10.1.31.75  27017/TCP  ready
mongodb-k8s/1   active    idle   10.1.31.76  27017/TCP  ready
$ mongodump --host 10.152.183.90 --port 27017 --gzip --archive=backup.archive --forceTableScan
2020-02-26T16:41:23.777+0100    writing admin.system.version to archive 'backup.archive'
2020-02-26T16:41:23.779+0100    done dumping admin.system.version (1 document)
$ mongorestore --host 10.152.183.90 --port 27017 --gzip --archive=backup.archive
```

## Testing

The tests of this charm are done using tox and Zaza.

### Prepare environment

The machine in which the tests are run needs access to a juju k8s controller. The easiest way to approach this is by executing the following commands:

```bash
sudo apt install tox -y
sudo snap install microk8s --classic
sudo snap install juju

microk8s.status --wait-ready
microk8s.enable storage dashboard dns

juju bootstrap microk8s k8s-cloud
```

### Test charm with Tox

```bash
tox -e black    # Check syntax
tox -e build    # Build the charm
tox -e func     # Test charm
```
