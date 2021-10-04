#!/usr/bin/python3
# Copyright 2021 Canonical Ltd.
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
# contact: legal@canonical.com
#
# To get in touch with the maintainers, please contact:
# osm-charmers@lists.launchpad.net
##

import unittest
import zaza.model as model
from pymongo import MongoClient


def get_mongo_uri():
    mongo_uri = "mongodb://"
    mongo_units = model.get_status().applications["mongodb-k8s"]["units"]
    for i, unit_name in enumerate(mongo_units.keys()):
        if i:
            mongo_uri += ","
        unit_ip = mongo_units[unit_name]["address"]
        unit_port = mongo_units[unit_name]["opened-ports"][0].split("/")[0]
        mongo_uri += "{}:{}".format(unit_ip, unit_port)

    return mongo_uri


class BasicDeployment(unittest.TestCase):
    def test_get_mongo_uri(self):
        get_mongo_uri()

    def test_mongodb_connection(self):
        mongo_uri = get_mongo_uri()
        client = MongoClient(mongo_uri)
        client.server_info()

    def test_mongodb_create_empty_database_collection(self):
        mongo_uri = get_mongo_uri()
        client = MongoClient(mongo_uri)
        DB_NAME = "test_database"
        COLLECTION_NAME = "test_collection"

        db = client[DB_NAME]
        _ = client.list_database_names()

        collection = db[COLLECTION_NAME]
        _ = db.list_collection_names()

        data = {}

        id = collection.insert_one(data)

        for x in collection.find({"_id": id.inserted_id}):
            self.assertEqual(id.inserted_id, x["_id"])

    def test_mongodb_insert_one(self):
        mongo_uri = get_mongo_uri()
        client = MongoClient(mongo_uri)
        DB_NAME = "test_database"
        COLLECTION_NAME = "test_collection"

        db = client[DB_NAME]
        _ = client.list_database_names()

        collection = db[COLLECTION_NAME]
        _ = db.list_collection_names()

        data = {
            "name": "Canonical LTD",
            "address": "5th Floor of the Blue Fin Building",
        }

        id = collection.insert_one(data)

        for x in collection.find({"_id": id.inserted_id}):
            self.assertEqual(id.inserted_id, x["_id"])

    def test_mongodb_insert_many(self):
        mongo_uri = get_mongo_uri()
        client = MongoClient(mongo_uri)
        DB_NAME = "test_database"
        COLLECTION_NAME = "test_collection"

        db = client[DB_NAME]
        _ = client.list_database_names()

        collection = db[COLLECTION_NAME]
        _ = db.list_collection_names()

        data = [
            {"name": "Amy", "address": "Apple st 652"},
            {"name": "Hannah", "address": "Mountain 21"},
            {"name": "Michael", "address": "Valley 345"},
            {"name": "Sandy", "address": "Ocean blvd 2"},
            {"name": "Betty", "address": "Green Grass 1"},
            {"name": "Richard", "address": "Sky st 331"},
            {"name": "Susan", "address": "One way 98"},
            {"name": "Vicky", "address": "Yellow Garden 2"},
            {"name": "Ben", "address": "Park Lane 38"},
            {"name": "William", "address": "Central st 954"},
            {"name": "Chuck", "address": "Main Road 989"},
            {"name": "Viola", "address": "Sideway 1633"},
        ]

        ids = collection.insert_many(data)

        for id in ids.inserted_ids:
            x = collection.find_one({"_id": id})
            self.assertEqual(x["_id"], id)
