Charm Generator
===============

This tool was designed to help bootstrap the process of charm creation.
It should help beginners to have a charm working in a matter of minutes.

The charm generator takes as input an initialized charm and some scripts
or description of HTTP requests and transforms it into a functional charm
with all the metadata filled in.

The main flow is the following:

1) charm create <name of the charm>
2) copy the scripts or the requests definition into a specific directory
3) run the generator
4) charm build

What types of charms can be generated?
--------------------------------------

Currently, the Charm Generator only supports Ansible scripts.

In the roadmap, the following charms are planned:

* HTTP Requests
* SOL002 Requests
* Python Scripts

How to run the Charm Generator?
-------------------------------

To run the Charm Generator, you should do the following steps:

1) Download the OSM Devops git repository
2) Install the requirements.txt
3) Run the generator.py in the charm that you want to generate

The only mandatory parameter is what type of charm you want to
generate:

* Ansible (--ansible)
* HTTP Requests (--http) - not implemented
* SOL002 Requests (--sol002) - not implemented
* Python Scripts (--scripts) - not implemented

There are some recommended parameters, such as:

* Summary - summary of what the charm does (--summary)
* Maintainer - the name and email of the maintainer (--maintainer)
* Description - description of what the charm does (--description)
* Company - company name to be include in the license headers (--company)
* Email - email of the company/developer to be included in the license headers (--email)

Specifics of the Ansible option
-------------------------------

In order to create an Ansible charm, you need to create a directory
inside the charm and name it playbooks. Inside that directory, you 
should put all the playbooks that are going to be executed in the charm.

Note: the playbooks extension must be .yaml

Your charm should look like this before running the generator:

~~~
.
├── config.yaml
├── icon.svg
├── layer.yaml
├── metadata.yaml
├── playbooks
│   ├── pb-1.yaml
│   ├── playbook2.yaml
│   └── playbook_3.yaml
├── reactive
│   └── testch.py
├── README.ex
└── tests
    ├── 00-setup
    └── 10-deploy
~~~