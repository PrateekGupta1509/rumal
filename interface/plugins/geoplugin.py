#!/usr/bin/env python
#
# GeoPlugin.py
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA  02111-1307  USA
#
# Author:   Tarun Kumar <reach.tarun.here@gmail.com>
#
# This product includes GeoLite2 data created by MaxMind, available from
# http://www.maxmind.com
#
# Plugin for collection Geo Data for Rumal. This plugin works using local dbs.
# In future if a web version is written. An effort must be made to make sure that
# it stores data in a compatiable format.
#
# ToDO: Write comments on storage scheme.

import sys
import os.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))

from interface.plug import *
import geoip2.database



class GeoPlugin(PluginBase):
    @property
    def dependencies(self):
        """List of dependencies - put class names of required plugins here.
           Return blank list if none."""
        return []

    @property
    def module_dependencies(self):
        """List of non-standard lib module dependencies
           - put module names as keys and versions as
           values.Return blank list if none."""
        return
        {
            "geoip2": "2.2.0",
            "ipaddr": "2.1.11",
            "maxminddb": "1.2.0",
            "requests": "2.7.0",
        }

    def config_plugin(self):
        """ Use data in self.config_dict to configure required settings
            also create reader object as creation is expensive.
        """
        self.readers = {}
        # Now check which dbs are enabled.
        self.enabled_dbs = []
        db_path_dict = self.config_dict["db_path"]
        for name, value in self.config_dict["dbs"].iteritems():
            if value == "True":
                self.enabled_dbs.append(name)
                db_path = db_path_dict[name]
                self.readers[name] = geoip2.database.Reader(db_path)

    def pretty_response(self,response,db_type):
        pretty_response = {}
        if db_type == "city":
            pretty_response["Country ISO"] = response.country.iso_code
            pretty_response["Country"] = response.country.name
            pretty_response["City"] = response.city.name
            pretty_response["Postal Code"] = response.postal.code
            pretty_response["Latitude"] = response.location.latitude
            pretty_response["Longitude"] = response.location.longitude
        elif db_type == "anonymous_ip":
            # define parameters after collecting info
            pass
        elif db_type == "connection_type":
            pretty_response["Connection Type"] = response.connection_type
        elif db_type == "domain":
            pretty_response["Domain"] = response.domain
        elif db_type == "isp":
            pretty_response["Autonomus System Number"] = response.autonomous_system_number
            pretty_response["Autonomus System Org"] = response.autonomous_system_organization
            pretty_response["ISP"] = response.isp
            pretty_response["Org"] = response.organization
        # pretty_response["raw"] = response.__dict__ # find fix for this
        return pretty_response

    def get_geo(self, ip, db_type):
        """Fetch data from local DB"""
        if db_type == "city":
            try:
                response = self.readers["city"].city(ip)
            except AddressNotFoundError:
                response = {}
        elif db_type == "anonymous_ip":
            try:
                response = self.readers["anonymous_ip"].anonymous_ip(ip)
            except AddressNotFoundError:
                response = {}
        elif db_type == "connection_type":
            try:
                response = self.readers["connection_type"].connection_type(ip)
            except AddressNotFoundError:
                response = {}
        elif db_type == "domain":
            try:
                response = self.readers["domain"].domain(ip)
            except AddressNotFoundError:
                response = {}
        elif db_type == "isp":
            try:
                response = self.readers["isp"].isp(ip)
            except AddressNotFoundError:
                response = {}
        if response == {}:
            return response
        else:
            return self.pretty_response(response, db_type)

    def run(self):
        """Run and make changes to data"""
        self.check_dependencies()
        self.config_plugin()
        # 2. Append all changes to x.data["flat_tree"]["url_link/node"]["plugin_name"]
        for db_type in self.enabled_dbs:  # will be set in config method
            ip_geo_map = {}  # keys are IPs and values contain respective geo data.
            # Reset ip_geo_map for each DB run.
            for node in self.data["flat_tree"]:
                node_ip = node["ip"]
                if node_ip == None:
                    node["GeoPlugin"][db_type] = {}
                    continue
                if "GeoPlugin" not in node.keys():
                    node["GeoPlugin"] = {}  # To avoid key error as further data is according to db.
                if node_ip in ip_geo_map.keys():
                    node["GeoPlugin"][db_type] = ip_geo_map[node_ip]
                else:
                    node["GeoPlugin"][db_type] = self.get_geo(node_ip, db_type)
                    ip_geo_map[node_ip] = node["GeoPlugin"][db_type]
            # 3. Call save data
        return self.save_data()
