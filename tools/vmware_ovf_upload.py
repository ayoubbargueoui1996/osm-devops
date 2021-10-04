# -*- coding: utf-8 -*-

# #
# Copyright 2016-2017 VMware Inc.
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
import os
from progressbar import Percentage, Bar, ETA, FileTransferSpeed, ProgressBar
from pyvcloud.vcd.client import BasicLoginCredentials, Client
from pyvcloud.vcd.org import Org
import re
import requests
import sys
import time
from xml.etree import ElementTree as XmlElementTree

API_VERSION = '5.6'


class vCloudconfig(object):

    def __init__(self, host=None, user=None, password=None, orgname=None, logger=None):
        self.url = host
        self.user = user
        self.password = password
        self.org = orgname
        self.logger = logging.getLogger('vmware_ovf_upload')
        self.logger.setLevel(10)

    def connect(self):
        """ Method connect as normal user to vCloud director.

            Returns:
                The return vca object that letter can be used to connect to vCloud director as admin for VDC
        """

        try:
            self.logger.debug("Logging in to a vcd {} as user {}".format(self.org,
                                                                         self.user))
            client = Client(self.url, verify_ssl_certs=False)
            client.set_credentials(BasicLoginCredentials(self.user, self.org, self.password))
        except Exception:
            raise Exception("Can't connect to a vCloud director org: "
                            "{} as user: {}".format(self.org, self.user))

        return client

    def get_catalog_id_from_path(self, catalog_name=None, path=None, progress=False):
        """
        Args
            catalog - catalog name to be created
            path: - valid path to OVF file.
            progress - boolean progress bar show progress bar.

        Return: if image uploaded correct method will provide image catalog UUID.
        """
        if not path:
            raise Exception("Image path can't be None.")

        if not os.path.isfile(path):
            raise Exception("Can't read file. File not found.")

        if not os.access(path, os.R_OK):
            raise Exception("Can't read file. Check file permission to read.")

        self.logger.debug("get_catalog_id_from_path() client requesting {} ".format(path))

        _, filename = os.path.split(path)
        _, file_extension = os.path.splitext(path)
        if file_extension != '.ovf':
            self.logger.debug("Wrong file extension {} connector support only OVF container.".format(file_extension))
            raise Exception("Wrong container.  vCloud director supports only OVF.")

        self.logger.debug("File name {} Catalog Name {} file path {} ".format(filename,
                                                                              catalog_name,
                                                                              path))
        try:
            client = self.connect()
            if not client:
                raise Exception("Failed to connect vCD")
            org = Org(client, resource=client.get_org())
            catalogs = org.list_catalogs()
        except Exception as exp:
            self.logger.debug("Failed get catalogs() with Exception {} ".format(exp))
            raise Exception("Failed get catalogs() with Exception {} ".format(exp))

        if len(catalogs) == 0:
            self.logger.info("Creating a new catalog entry {} in vcloud director".format(catalog_name))
            result = org.create_catalog(catalog_name, catalog_name)
            if result is None:
                raise Exception("Failed to create new catalog {} ".format(catalog_name))
            result = self.upload_ovf(org=org, catalog_name=catalog_name, image_name=filename.split(".")[0],
                                     media_file_name=path, description='medial_file_name', progress=progress)
            if not result:
                raise Exception("Failed to create vApp template for catalog {} ".format(catalog_name))
            return self.get_catalogid(catalog_name, catalogs)
        else:
            for catalog in catalogs:
                # search for existing catalog if we find same name we return ID
                if catalog['name'] == catalog_name:
                    self.logger.debug("Found existing catalog entry for {} "
                                      "catalog id {}".format(catalog_name,
                                                             self.get_catalogid(catalog_name, catalogs)))
                    return self.get_catalogid(catalog_name, catalogs)

        # if we didn't find existing catalog we create a new one and upload image.
        self.logger.debug("Creating new catalog entry {} - {}".format(catalog_name, catalog_name))
        result = org.create_catalog(catalog_name, catalog_name)
        if result is None:
            raise Exception("Failed to create new catalog {} ".format(catalog_name))

        result = self.upload_ovf(org=org, catalog_name=catalog_name, image_name=filename.split(".")[0],
                                 media_file_name=path, description='medial_file_name', progress=progress)
        if not result:
            raise Exception("Failed create vApp template for catalog {} ".format(catalog_name))

    def get_catalogid(self, catalog_name=None, catalogs=None):
        """  Method check catalog and return catalog ID in UUID format.

        Args
            catalog_name: catalog name as string
            catalogs:  list of catalogs.

        Return: catalogs uuid
        """

        for catalog in catalogs:
            if catalog['name'] == catalog_name:
                catalog_id = catalog['id']
                return catalog_id
        return None

    def upload_ovf(self, org=None, catalog_name=None, image_name=None, media_file_name=None,
                   description='', progress=False, chunk_bytes=128 * 1024):
        """
        Uploads a OVF file to a vCloud catalog

        org : organization object
        catalog_name: (str): The name of the catalog to upload the media.
        media_file_name: (str): The name of the local media file to upload.
        return: (bool) True if the media file was successfully uploaded, false otherwise.
        """
        client = self.connect()
        if not client:
            raise Exception("Failed to connect vCD!")

        os.path.isfile(media_file_name)
        statinfo = os.stat(media_file_name)

        #  find a catalog entry where we upload OVF.
        #  create vApp Template and check the status if vCD able to read OVF it will respond with appropirate
        #  status change.
        #  if VCD can parse OVF we upload VMDK file
        try:
            for catalog in org.list_catalogs():
                if catalog_name != catalog['name']:
                    continue
                catalog_href = "{}/api/catalog/{}/action/upload".format(self.url, catalog['id'])
                data = """
                <UploadVAppTemplateParams name="{}" xmlns="http://www.vmware.com/vcloud/v1.5"
                xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1">
                <Description>{} vApp Template</Description></UploadVAppTemplateParams>
                """.format(catalog_name, description)

                if client:
                    headers = {'Accept': 'application/*+xml;version=' + API_VERSION,
                               'x-vcloud-authorization': client._session.headers['x-vcloud-authorization']}
                    headers['Content-Type'] = 'application/vnd.vmware.vcloud.uploadVAppTemplateParams+xml'

                response = requests.post(url=catalog_href,
                                         headers=headers,
                                         data=data,
                                         verify=False)
                if response.status_code != 201:
                    self.logger.debug("Failed to create vApp template")
                    raise Exception("Failed to create vApp template")

                if response.status_code == requests.codes.created:
                    catalogItem = XmlElementTree.fromstring(response.content)
                    entity = [child for child in catalogItem if
                              child.get("type") == "application/vnd.vmware.vcloud.vAppTemplate+xml"][0]
                    href = entity.get('href')
                    template = href

                    response = requests.get(url=href,
                                            headers=headers,
                                            verify=False)
                    if response.status_code == requests.codes.ok:
                        headers['Content-Type'] = 'Content-Type text/xml'
                        result = re.search('rel="upload:default"\shref="(.*?\/descriptor.ovf)"', response.content)
                        if result:
                            transfer_href = result.group(1)

                        response = requests.put(url=transfer_href, headers=headers,
                                                data=open(media_file_name, 'rb'),
                                                verify=False)

                        if response.status_code != requests.codes.ok:
                            self.logger.debug(
                                "Failed create vApp template for catalog name {} and image {}".format(
                                    catalog_name,
                                    media_file_name))
                            return False

                    # TODO fix this with aync block
                    time.sleep(5)

                    self.logger.debug("vApp template for catalog name {} and image {}".format(
                        catalog_name,
                        media_file_name))

                    # uploading VMDK file
                    # check status of OVF upload and upload remaining files.

                    response = requests.get(url=template,
                                            headers=headers,
                                            verify=False)

                    if response.status_code == requests.codes.ok:
                        result = re.search('rel="upload:default"\s*href="(.*?vmdk)"', response.content)
                        if result:
                            link_href = result.group(1)
                        # we skip ovf since it already uploaded.
                        if 'ovf' in link_href:
                            continue
                        # The OVF file and VMDK must be in a same directory
                        head, _ = os.path.split(media_file_name)
                        file_vmdk = head + '/' + link_href.split("/")[-1]
                        if not os.path.isfile(file_vmdk):
                            return False
                        statinfo = os.stat(file_vmdk)
                        if statinfo.st_size == 0:
                            return False
                        hrefvmdk = link_href
                        if progress:
                            widgets = ['Uploading file: ', Percentage(), ' ', Bar(), ' ', ETA(), ' ',
                                       FileTransferSpeed()]
                            progress_bar = ProgressBar(widgets=widgets, maxval=statinfo.st_size).start()

                        bytes_transferred = 0
                        f = open(file_vmdk, 'rb')
                        while bytes_transferred < statinfo.st_size:
                            my_bytes = f.read(chunk_bytes)
                            if len(my_bytes) <= chunk_bytes:
                                headers['Content-Range'] = 'bytes %s-%s/%s' % (
                                    bytes_transferred, len(my_bytes) - 1, statinfo.st_size)
                                headers['Content-Length'] = str(len(my_bytes))
                                response = requests.put(url=hrefvmdk,
                                                        headers=headers,
                                                        data=my_bytes,
                                                        verify=False)
                                if response.status_code == requests.codes.ok:
                                    bytes_transferred += len(my_bytes)
                                    if progress:
                                        progress_bar.update(bytes_transferred)
                                else:
                                    self.logger.debug(
                                        'file upload failed with error: [%s] %s' % (response.status_code,
                                                                                    response.content))

                                    f.close()
                                    return False
                        f.close()
                        if progress:
                            progress_bar.finish()
                            time.sleep(60)
                    return True
                else:
                    self.logger.debug("Failed retrieve vApp template for catalog name {} for OVF {}".
                                      format(catalog_name, media_file_name))
                    return False
        except Exception as exp:
            self.logger.debug("Failed while uploading OVF to catalog {} for OVF file {} with Exception {}"
                              .format(catalog_name, media_file_name, exp))
            raise Exception(
                "Failed while uploading OVF to catalog {} for OVF file {} with Exception {}"
                .format(catalog_name, media_file_name, exp))
        self.logger.debug("Failed to retrieve catalog name {} for OVF file {}".format(catalog_name, media_file_name))
        return False


if __name__ == "__main__":

    print("This file is deprecated.  Please use ovf_uplader_cli instead.")

    # vmware vcloud director credentials
    vcd_hostname = sys.argv[1]
    vcd_username = sys.argv[2]
    vcd_password = sys.argv[3]
    orgname = sys.argv[4]
    # OVF image path to be upload to vCD
    ovf_file_path = sys.argv[5]

    logging.basicConfig(filename='ovf_upload.log', level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    obj = vCloudconfig(vcd_hostname, vcd_username, vcd_password, orgname, logger)

    dirpath, filename = os.path.split(ovf_file_path)
    filename_name, file_extension = os.path.splitext(filename)

    # Get image name from cirros vnfd
    cirros_yaml = '../descriptor-packages/vnfd/cirros_vnf/src/cirros_vnfd.yaml'
    rh = open(cirros_yaml, 'r')
    match = re.search("image:\s'(.*?)'\n", rh.read())
    if match:
        catalog = match.group(1)

    if file_extension == '.ovf':
        obj.get_catalog_id_from_path(catalog_name=catalog, path=ovf_file_path,
                                     progress=True)
