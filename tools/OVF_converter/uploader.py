# #
# Copyright 2019 VMware Inc.
# This file is part of ETSI OSM
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
#
# For those usages not covered by the Apache License, Version 2.0 please
# contact:  osslegalrouting@vmware.com
# #

import logging
from lxml import etree
import os
from pyvcloud.vcd.client import BasicLoginCredentials, Client, QueryResultFormat, ResourceType, TaskStatus, ApiVersion
from pyvcloud.vcd.exceptions import EntityNotFoundException, InternalServerException
from pyvcloud.vcd.org import Org
import sys
import tarfile
import time

MODULE_DIR = os.path.dirname(__file__)

# Set logger
LOG_FILE = os.path.join(MODULE_DIR, "logs/ovf_uploader.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logger = logging.getLogger(__name__)
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.INFO)
logger.addHandler(stdout_handler)
logger.setLevel(10)
logging.captureWarnings(True)

__version__ = "1.0"
__description__ = "Initial Release"


def get_version():
    """ get version of this application"""
    version = str(__version__) + " - " + str(__description__)
    return version


def report_progress(bytes_written, total_size):
    percent_complete = int((bytes_written * 100) / total_size)
    print("{}% complete  \r".format(percent_complete), end='')


class OVFUploader(object):
    """ Class to convert input image into OVF format """

    def __init__(self, ovf_file, vcd_url=None, username=None, password=None, orgname=None):
        self.ovf_file = os.path.abspath(ovf_file)
        self.vcd_url = vcd_url
        self.username = username
        self.password = password
        self.orgname = orgname
        try:
            client = Client(self.vcd_url, verify_ssl_certs=False, api_version=ApiVersion.VERSION_32.value,
                            log_requests=True,
                            log_headers=True,
                            log_bodies=True,
                            log_file=LOG_FILE)
            # sclient.set_highest_supported_version()
            client.set_credentials(BasicLoginCredentials(self.username, self.orgname,
                                                         self.password))
            logger.info("Logged into {} using version {}".format(self.vcd_url, client.get_api_version()))
            self.client = client
            self.org = Org(self.client, resource=self.client.get_org())

        except Exception as exp:
            problem = Exception("Failed to connect to vCD at {}, org {}, username {}:\n{}".format(
                self.vcd_url, self.orgname, self.username, exp))
            logger.error(problem)
            raise problem

        try:
            # Retrieve the VM name from the OVF.  We will use this as both the image and catalog name
            OVF_tree = etree.parse(self.ovf_file)
            root = OVF_tree.getroot()
            nsmap = {k: v for k, v in root.nsmap.items() if k}
            nsmap["xmlns"] = "http://schemas.dmtf.org/ovf/envelope/1"

            virtuasystem = root.find('xmlns:VirtualSystem', nsmap)
            name_tag = virtuasystem.find('xmlns:Name', nsmap)
            self.image_name = name_tag.text
            info_tag = virtuasystem.find('xmlns:Info', nsmap)
            self.image_description = info_tag.text

            references = root.find('xmlns:References', nsmap)
            file = references.find('xmlns:File', nsmap)
            self.vmdk_file = "{}/{}".format(
                os.path.dirname(self.ovf_file),
                file.attrib['{http://schemas.dmtf.org/ovf/envelope/1}href'])
            logger.info("Loaded VM {}: {}".format(self.image_name, self.image_description))

        except Exception as exp:
            problem = Exception("Failed to fetch VirtualSystem Name element from OVF {}:\n{}".format(
                self.ovf_file, exp))
            logger.error(problem)
            raise problem

    def make_catalog(self):
        self.catalog_id = None
        try:
            for catalog in self.org.list_catalogs():
                if catalog['name'] == self.image_name:
                    self.catalog_id = catalog['id']
            if self.catalog_id is None:
                logger.info("Creating a new catalog entry {} in vCD".format(self.image_name))
                result = self.org.create_catalog(self.image_name, self.image_description)
                if result is None:
                    raise Exception("Failed to create new catalog entry")
                self.catalog_id = result.attrib['id'].split(':')[-1]
                self.org.reload()

            logger.debug("Using catalog {}, id {}".format(self.image_name, self.catalog_id))

        except Exception as exp:
            problem = Exception("Failed to fetch catalog for {}:\n{} ".format(self.image_name, exp))
            logger.error(problem)
            raise problem

    def upload_ovf(self):

        ova_tarfilename, _ = os.path.splitext(self.ovf_file)
        ova_tarfilename += '.ova'
        try:
            # Check if the content already exists:
            resource_type = ResourceType.CATALOG_ITEM.value
            q = self.client.get_typed_query(
                resource_type,
                query_result_format=QueryResultFormat.ID_RECORDS,
                equality_filter=('catalogName', self.image_name))
            for item in list(q.execute()):
                if item.get('name') == self.image_name:
                    logger.info("Removing old version from catalog")
                    try:
                        self.org.delete_catalog_item(self.image_name, self.image_name)
                    except InternalServerException as exp:
                        problem = Exception(
                            "Cannot delete vAppTemplate {}. Please check in vCD if "
                            "the content is still being imported into the catalog".format(
                                self.image_name))
                        raise problem

            # Create a single OVA bundle
            ova = tarfile.open(name=ova_tarfilename,
                               mode='w')
            ova.add(self.ovf_file, arcname=os.path.basename(self.ovf_file))
            ova.add(self.vmdk_file, arcname=os.path.basename(self.vmdk_file))
            ova.close()
            logger.info("Uploading content to vCD")
            self.org.upload_ovf(self.image_name,
                                ova_tarfilename,
                                item_name=self.image_name,
                                description=self.image_description,
                                callback=report_progress)
        except Exception as exp:
            problem = Exception("Failed to upload OVF {}:\n{} ".format(self.ovf_file, exp))
            logger.error(problem)
            raise problem
        finally:
            if os.path.exists(ova_tarfilename):
                os.remove(ova_tarfilename)

    def wait_for_task_completion(self):

        logger.info("Importing content to vCD")
        try:

            query = self.client.get_typed_query(
                query_type_name=ResourceType.TASK.value,
                qfilter='ownerName==' + self.username + ';(status==queued,status==preRunning,status==running)',
                query_result_format=QueryResultFormat.REFERENCES)

            upload_task = None
            tasks = list(query.execute())
            for task in tasks:
                if task.get('name') == 'VDC_UPLOAD_OVF_CONTENTS':
                    upload_task = self.client.get_resource(task.get('href'))
                    break

            bad_statuses = [
                TaskStatus.ABORTED,
                TaskStatus.CANCELED,
                TaskStatus.ERROR
            ]

        except Exception as exp:
            problem = Exception("Failed to import OVF {}:\n{} ".format(self.ovf_file, exp))
            logger.error(problem)
            raise problem

        while(True):
            task_status = upload_task.get('status').lower()
            if(hasattr(upload_task, 'Progress')):
                print("{}% complete  \r".format(upload_task.Progress), end='')

            for status in bad_statuses:
                if task_status == status.value.lower():
                    problem = Exception(
                        "vCD failed to import OVF {}:\n{}: {} ".format(self.ovf_file,
                                                                       task_status,
                                                                       upload_task.Error.get('Message')))
                    logger.error(problem)
                    raise problem
            if task_status == str(TaskStatus.SUCCESS.value).lower():
                break

            time.sleep(2)
            upload_task = self.client.get_resource(upload_task.get('href'))

        logger.info("OVF upload and import complete, content is ready to use")
