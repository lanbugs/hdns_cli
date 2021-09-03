#!/usr/bin/env python3

import requests
import fire
import json
from loguru import logger
import tabulate
import yaml
from pprint import pprint
import os.path
from os.path import expanduser

########################################################################################################################
# Try to autoload settings
########################################################################################################################
def config_loader(file):
    """ Autoloader """
    try:
        import configparser
        config = configparser.ConfigParser()
        config.read(file)
        system = config.get('general', 'system')
        token = config.get('general', 'token')
        return system, token
    except Exception as e:
        logger.exception(e)

home = expanduser("~")

if os.path.isfile(f"{home}/.hdns/hdns.ini"):
    SYSTEM, TOKEN = config_loader(f"{home}/.hdns/hdns.ini")
elif os.path.isfile("/etc/hdns/hdns.ini"):
    SYSTEM, TOKEN = config_loader("/etc/hdns/hdns.ini")
elif os.path.isfile("./hdns.ini"):
    SYSTEM, TOKEN = config_loader("./hdns.ini")
else:
    SYSTEM = ""
    TOKEN = ""

########################################################################################################################
# CONSTANTS
########################################################################################################################
VALID_TYPES = ['A', 'AAAA', 'NS', 'MX', 'CNAME', 'RP', 'TXT', 'SOA', 'HINFO', 'SRV', 'DANE', 'TLSA', 'DS', 'CAA']

########################################################################################################################
# HDNS CLI
########################################################################################################################
class Hdns_cli(object):
    """HDNS - CLI tool to administer Hetzner DNS via API - Version 1.0.0\n
    Hetzner provides an DNS service completely manageable via API,
    this tool gives you easy access to the functions.

    To use define --system dns.hetzner.com --token <your_api_key> or simply store
    it in an config ini file.

    You have the following options:
    - ~/.hdns/hdns.ini
    - /etc/hdns/hdns.ini
    - ./hdns.ini

    Content:
    [general]
    system=dns.hetzner.com
    token=<your_token>

    ---
    Written by Maximilian Thoma 2021, released under GNU General Public License v3.0
    More on https://lanbugs.de or https://github.com/lanbugs/hdns_cli
    :param token: Token for authentication
    :param system: FQDN of the DNS System used, eg. dns.hetzner.com
    """

    def __init__(self, token=TOKEN, system=SYSTEM):
        self.API_TOKEN = token
        self.SYSTEM = system

    def show_token(self):
        """ Shows the current used token """
        print(self.API_TOKEN)

    def show_system(self):
        """ Shows the current used system """
        print(self.SYSTEM)

    def _get_zone_id(self, zone_name):
        """ PRIVATE: Get the zone id to work with names in records add, mod, remove """
        try:
            response = requests.get(
                url=f"https://{self.SYSTEM}/api/v1/zones",
                headers={"Auth-API-Token": self.API_TOKEN}
            )

            status_code = response.status_code
            content = json.loads(response.content)

            if status_code == 200:
                for zone in content['zones']:
                    if zone_name == zone['name']:
                        return zone['id']

            return False

        except requests.exceptions.RequestException as e:
            logger.exception(e)

    def _get_record_id(self, zone, name, type, value):
        """ PRIVATE: Get the record id if record is unique """
        try:
            zone_id = self._get_zone_id(zone)

            # get all records of domain
            response = requests.get(
                url=f"https://{self.SYSTEM}/api/v1/records",
                params={
                    "zone_id": zone_id,
                },
                headers={
                    "Auth-API-Token": self.API_TOKEN,
                },
            )

            status_code = response.status_code
            content = json.loads(response.content)

            if status_code == 200:
                records = content['records']
                matches = 0
                result = 0

                for rr in records:
                    if rr['name'] == name and rr['type'] == type and rr['value'] == value:
                        result = rr['id']
                        matches += 1

                if matches == 1:
                    return result
                else:
                    return False

            else:
                print("Error occured")
                print(content)

        except requests.exceptions.RequestException as e:
            logger.exception(e)

    def _get_all_record_ids(self, zone, name, type, value):
        """ PRIVATE: Get the record ids for all identical records """
        try:
            zone_id = self._get_zone_id(zone)

            # get all records of domain
            response = requests.get(
                url=f"https://{self.SYSTEM}/api/v1/records",
                params={
                    "zone_id": zone_id,
                },
                headers={
                    "Auth-API-Token": self.API_TOKEN,
                },
            )

            status_code = response.status_code
            content = json.loads(response.content)

            if status_code == 200:
                records = content['records']
                result = []

                for rr in records:
                    if rr['name'] == name and rr['type'] == type and rr['value'] == value:
                        result.append(rr['id'])
                return result

            else:
                print("Error occured")
                print(content)

        except requests.exceptions.RequestException as e:
            logger.exception(e)

    def _get_primary_server_id(self, zone, address, port=53):
        try:
            zone_id = self._get_zone_id(zone)

            response = requests.get(
                url=f"https://{self.SYSTEM}/api/v1/primary_servers",
                headers={
                    "Auth-API-Token": self.API_TOKEN,
                },
            )

            status_code = response.status_code
            content = json.loads(response.content)

            if status_code == 200:
                for ps in content['primary_servers']:
                    if ps['zone_id'] == zone_id and ps['address'] == address and ps['port'] == port:
                        return ps['id']
            else:
                return False

        except requests.exceptions.RequestException as e:
            logger.exception(e)
    ####################################################################################################################
    # Everything regarding zones

    def show_zones(self):
        """ Show all zones eg. hdns_cli show_zones """
        try:
            response = requests.get(
                url=f"https://{self.SYSTEM}/api/v1/zones",
                headers={"Auth-API-Token": self.API_TOKEN}
            )

            status_code = response.status_code
            content = json.loads(response.content)

            if status_code == 200:
                result_header = ['ID', 'Zone', 'Secondary?', 'NS']
                results = []

                for zone in content['zones']:
                    results.append(
                        [
                            zone['id'],
                            zone['name'],
                            zone['is_secondary_dns'],
                            ", ".join(zone['ns'])
                        ]
                    )

                print(f"*** Zones @ {self.SYSTEM} " + "*"*80)
                print(tabulate.tabulate(results, result_header))

        except requests.exceptions.RequestException as e:
            logger.exception(e)

    def create_zone(self, zone, ttl=86400):
        """
        Create new Zone eg. hdns_cli create_zone --zone example.org
        :param zone: Name of the zone, eg. example.org
        :param ttl: Time to live, default: 86400
        """
        try:
            response = requests.post(
                url=f"https://{self.SYSTEM}/api/v1/zones",
                headers={
                    "Content-Type": "application/json",
                    "Auth-API-Token": self.API_TOKEN,
                },
                data=json.dumps({
                    "name": zone,
                    "ttl": ttl
                })
            )

            status_code = response.status_code
            content = json.loads(response.content)

            if status_code == 200:
                print(f"zone {zone} created.")
            else:
                print(content['error']['message'])

        except requests.exceptions.RequestException as e:
            logger.exception(e)

    def update_zone(self, zone, ttl):
        """
        Update zone parameters
        :param zone: Name of the zone, eg. example.org
        :param ttl: Time to Live

        """
        try:
            zone_id = self._get_zone_id(zone)

            response = requests.put(
                url=f"https://{self.SYSTEM}/api/v1/zones/{zone_id}",
                headers={
                    "Content-Type": "application/json",
                    "Auth-API-Token": self.API_TOKEN,
                },
                data=json.dumps({
                    "name": zone,
                    "ttl": ttl
                })
            )

            status_code = response.status_code
            content = json.loads(response.content)

            if status_code == 200:
                print(f"zone {zone} updated.")
            else:
                print(content['error']['message'])

        except requests.exceptions.RequestException as e:
            logger.exception(e)

    def delete_zone(self, zone, force=False):
        """
        Delete complete zone
        :param zone: Name of the zone, eg. example.org
        :param force: If set to True no safety question applied, zone will be deleted directly
        """
        zone_id = self._get_zone_id(zone)
        doit = False
        try:
            if force is False:
                print(f"Are you really want to delete the complete zone {zone}, confirm with 'YES'?")
                question = input()

                if question == 'YES':
                    doit = True
            else:
                doit = True

            if doit is True:
                response = requests.delete(
                    url=f"https://{self.SYSTEM}/api/v1/zones/{zone_id}",
                    headers={
                        "Auth-API-Token": self.API_TOKEN,
                    },
                )

                status_code = response.status_code
                content = json.loads(response.content)

                if status_code == 200:
                    print(f"zone {zone} deleted.")
                else:
                    pprint(content)

            else:
                print(f"Delete zone {zone} aborted ...")

        except requests.exceptions.RequestException as e:
            logger.exception(e)


    ####################################################################################################################
    # Everything regarding records

    def show_records(self, zone, id=False):
        """
        Shows records of given zone eg. hdns_cli show_records --zone example.org
        :param zone: Name of the zone, eg. example.org
        :param id: Show record ids if True
        """
        zone_id = self._get_zone_id(zone)

        try:
            response = requests.get(
                url=f"https://{self.SYSTEM}/api/v1/records?zone_id={zone_id}",
                headers={"Auth-API-Token": self.API_TOKEN}
            )

            status_code = response.status_code
            content = json.loads(response.content)

            print(f"*** Records @ {zone} " + "*" * 80)
            if status_code == 200:
                records = content['records']

                # Build beautiful list
                if id is False:
                    header = ['Name', 'Type', 'Value']
                else:
                    header = ['ID', 'Name', 'Type', 'Value']
                rows = []

                for rr in records:
                    if id is False:
                        rows.append(
                            [rr['name'], rr['type'], rr['value']]
                        )
                    else:
                        rows.append(
                            [rr['id'], rr['name'], rr['type'], rr['value']]
                        )

                print(tabulate.tabulate(rows, header))

        except requests.exceptions.RequestException as e:
            logger.exception(e)

    def create_record(self, zone, name, type, value, ttl=0):
        """
        Create new record in zone
        :param zone: Name of the zone, eg. example.org
        :param name: Name of the record, eg. www
        :param type: Type of record eg. A, valid are A, AAAA, NS, MX, CNAME, RP, TXT, SOA, HINFO, SRV, DANE, TLSA, DS, CAA
        :param value: Value of the record eg. 1.1.1.1
        :param ttl: Time to live default 0
        """
        try:
            zone_id = self._get_zone_id(zone)

            if type in VALID_TYPES:
                response = requests.post(
                    url=f"https://{self.SYSTEM}/api/v1/records",
                    headers={
                        "Content-Type": "application/json",
                        "Auth-API-Token": self.API_TOKEN,
                    },
                    data=json.dumps({
                        "value": value,
                        "ttl": ttl,
                        "type": type,
                        "name": name,
                        "zone_id": zone_id
                    })
                )

                status_code = response.status_code
                content = json.loads(response.content)

                if status_code == 200:
                    print("record successful created.")
                else:
                    print(content['error']['message'])


            else:
                print(f"Given type {type} is not supported.")
        except requests.exceptions.RequestException as e:
            logger.exception(e)

    def bulk_create_records(self, yaml_file):
        """
        Creates bulk records for zone
        :param yaml_file: Name of the yaml definition file
        """
        try:
            with open(yaml_file, 'r') as f:
                records = yaml.load(f.read(), Loader=yaml.FullLoader)

            for rr in records['records']:
                self.create_record(rr['zone'], rr['name'], rr['type'], rr['value'])

        except Exception as e:\
            logger.exception(e)

    def update_record(self, zone, name, type, value, name_new=None, value_new=None, record_id=None):
        """
        Update exsisting record, record_id required
        :param zone: Name of the zone, eg. example.org
        :param name: Name of the record, eg. www
        :param type: Type of record eg. A, valid are A, AAAA, NS, MX, CNAME, RP, TXT, SOA, HINFO, SRV, DANE, TLSA, DS, CAA
        :param value: Value of the record eg. 1.1.1.1
        :param name_new: New name of the record, eg. www
        :param value_new: New value of the record eg. 1.1.1.1
        :param record_id: Record ID if record is not unique. Get record_id with show_records --zone example.org --id True
        """
        try:
            zone_id = self._get_zone_id(zone)

            if record_id is None:
                record_id = self._get_record_id(zone, name, type, value)

            if name_new is None:
                name_new = name

            if value_new is None:
                value_new = value

            response = requests.put(
                url=f"https://{self.SYSTEM}/api/v1/records/{record_id}",
                headers={
                    "Content-Type": "application/json",
                    "Auth-API-Token": self.API_TOKEN,
                },
                data=json.dumps({
                    "value": value_new,
                    "ttl": 0,
                    "type": type,
                    "name": name_new,
                    "zone_id": zone_id
                })
            )

            status_code = response.status_code
            content = json.loads(response.content)

            if status_code == 200:
                print("record successful updated.")
            else:
                print(content['error']['message'])

        except requests.exceptions.RequestException as e:
            logger.exception(e)

    def delete_record(self, zone, name, type, value):
        """
        Delete record if record is unique.
        :param zone: Name of the zone, eg. example.org
        :param name: Name of the record, eg. www
        :param type: Type of record eg. A, valid are A, AAAA, NS, MX, CNAME, RP, TXT, SOA, HINFO, SRV, DANE, TLSA, DS, CAA
        :param value: Value of the record eg. 1.1.1.1
        """
        try:
            record_id = self._get_record_id(zone, name, type, value)

            response = requests.delete(
                url=f"https://{self.SYSTEM}/api/v1/records/{record_id}",
                headers={
                    "Auth-API-Token": self.API_TOKEN,
                },
            )

            status_code = response.status_code
            content = json.loads(response.content)

            if status_code == 200:
                print("record successfully deleted.")
            else:
                print(content)

        except requests.exceptions.RequestException as e:
            logger.exception(e)

    def delete_records(self, zone, name, type, value):
        """
        Delete records which are identical
        :param zone: Name of the zone, eg. example.org
        :param name: Name of the record, eg. www
        :param type: Type of record eg. A, valid are A, AAAA, NS, MX, CNAME, RP, TXT, SOA, HINFO, SRV, DANE, TLSA, DS, CAA
        :param value: Value of the record eg. 1.1.1.1
        """
        try:
            record_id = self._get_all_record_ids(zone, name, type, value)
            for r in record_id:
                response = requests.delete(
                    url=f"https://{self.SYSTEM}/api/v1/records/{r}",
                    headers={
                        "Auth-API-Token": self.API_TOKEN,
                    },
                )

                status_code = response.status_code
                content = json.loads(response.content)

                if status_code == 200:
                    print("record successfully deleted.")
                else:
                    print(content)

        except requests.exceptions.RequestException as e:
            logger.exception(e)

    def delete_record_by_id(self, record_id):
        """
        Delete record with record_id if record is not unique
        :param record_id: Record ID you can get the record id via show_records
        """
        try:
            response = requests.delete(
                url=f"https://{self.SYSTEM}/api/v1/records/{record_id}",
                headers={
                    "Auth-API-Token": self.API_TOKEN,
                },
            )

            status_code = response.status_code
            content = json.loads(response.content)

            if status_code == 200:
                print("record successfully deleted.")
            else:
                print(content)

        except requests.exceptions.RequestException as e:
            logger.exception(e)

    ####################################################################################################################
    # Everything regarding zone_files

    def import_zone(self, zone, file):
        """
        Import zone file to zone, WARNING: everything will be overwritten!
        :param zone: Name of the zone, eg. example.org
        :param file: Zone file which should be imported
        """
        try:
            zone_id = self._get_zone_id(zone)

            with open(file, "r") as f:
                content = f.read()

            response = requests.post(
                url=f"https://{self.SYSTEM}/api/v1/zones/{zone_id}/import",
                headers={
                    "Content-Type": "text/plain",
                    "Auth-API-Token": self.API_TOKEN,
                },
                data=content
            )

            status_code = response.status_code
            content = json.loads(response.content)

            if status_code == 200:
                print(f"zone file successfully imported in zone {zone}.")
            else:
                print(content['error']['message'])

        except requests.exceptions.RequestException as e:
            logger.exception(e)

    def export_zone(self, zone, file=None):
        """
        Export zone to file
        :param zone: Name of the zone, eg. example.org
        :param file: Name of file where the zone should be exported, if no file defined zone will be printed out
        """
        try:
            zone_id = self._get_zone_id(zone)

            response = requests.get(
                url=f"https://{self.SYSTEM}/api/v1/zones/{zone_id}/export",
                headers={
                    "Auth-API-Token": self.API_TOKEN,
                    "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
                },
                data={
                },
            )

            status_code = response.status_code
            content = response.content

            if status_code == 200 and not len(content) == 0:
                if file is None:
                    print(content.decode("utf-8"))
                else:
                    with open(file, "w") as f:
                        f.write(content.decode("utf-8"))

            if len(content) == 0:
                print("error occured, no zone data recieved")

        except requests.exceptions.RequestException as e:
            logger.exception(e)

    def validate_zonefile(self, file):
        """
        Validate zone file
        :param file: Zone file which should be validated
        """
        try:

            with open(file, 'r') as f:
                data = f.read()

            response = requests.post(
                url=f"https://{self.SYSTEM}/api/v1/zones/file/validate",
                headers={
                    "Content-Type": "text/plain",
                    "Auth-API-Token": self.API_TOKEN,
                },
                data=data
            )

            status_code = response.status_code
            content = json.loads(response.content)

            if status_code == 200:
                print("Zone file OK!")
                print(f"parsed records: {content['parsed_records']}")
                print(f"valid records: {content['valid_records']}")
            else:
                print("Zone file NOT ok!")
                print(content['error']['message'])

        except requests.exceptions.RequestException as e:
            logger.exception(e)

    ####################################################################################################################
    # Everything regarding secondary zones
    def show_primary_servers(self, id=False):
        """
        Shows all primary servers configured
        :param id: Show ids of primary servers if True
        """
        try:
            response = requests.get(
                url=f"https://{self.SYSTEM}/api/v1/primary_servers",
                headers={"Auth-API-Token": self.API_TOKEN}
            )

            status_code = response.status_code
            content = json.loads(response.content)

            if status_code == 200:
                response_zone = requests.get(
                    url=f"https://{self.SYSTEM}/api/v1/zones",
                    headers={"Auth-API-Token": self.API_TOKEN}
                )
                status_code_zone = response_zone.status_code
                content_zone = json.loads(response_zone.content)

                if status_code_zone == 200:

                    if id is False:
                        header = ['Zone', 'IP', 'Port']
                    else:
                        header = ['ID', 'Zone', 'IP', 'Port']

                    rows = []

                    for ps in content['primary_servers']:
                        # get zone name
                        for z in content_zone['zones']:
                            if ps['zone_id'] == z['id']:
                                zone_name = z['name']

                        if id is False:
                            rows.append(
                                [zone_name, ps['address'], ps['port']]
                            )
                        else:
                            rows.append(
                                [ps['id'], zone_name, ps['address'], ps['port']]
                            )

                    print(tabulate.tabulate(rows, header))
                else:
                    print("no records")
            else:
                print("no records")

        except requests.exceptions.RequestException as e:
            logger.exception(e)

    def create_primary_server(self, zone, address, port=53):
        """
        Create primary server requires empty zone. This zone is after primary server is created a secondary zone.
        :param zone: Name of the zone, eg. example.org
        :param address: IPv4 or IPv6 address
        :param port: Port of DNS server
        """
        try:
            zone_id = self._get_zone_id(zone)
            response = requests.post(
                url=f"https://{self.SYSTEM}/api/v1/primary_servers",
                headers={
                    "Content-Type": "application/json",
                    "Auth-API-Token": self.API_TOKEN,
                },
                data=json.dumps({
                    "address": address,
                    "port": port,
                    "zone_id": zone_id
                })
            )

            status_code = response.status_code
            content = json.loads(response.content)

            if status_code == 200:
                print(f"primary_server {address}:{port} for zone {zone} created.")
            else:
                print(content['error']['message'])

        except requests.exceptions.RequestException as e:
            logger.exception(e)

    def update_primary_server(self, zone, address, port=53, address_new=None, port_new=None):
        """
        Update primary server
        :param zone: Name of the zone, eg. example.org
        :param address: Current address IPv4 or IPv6
        :param port: Current port eg. 53
        :param address_new: New address IPv4 or IPv6
        :param port_new: New port eg. 53
        """
        try:
            ps_id = self._get_primary_server_id(zone, address, port)
            zone_id = self._get_zone_id(zone)

            if address_new is None:
                address_new = address

            if port_new is None:
                port_new = port

            response = requests.put(
                url=f"https://{self.SYSTEM}/api/v1/primary_servers/{ps_id}",
                headers={
                    "Content-Type": "application/json",
                    "Auth-API-Token": self.API_TOKEN,
                },
                data=json.dumps({
                    "address": address_new,
                    "port": port_new,
                    "zone_id": zone_id
                })
            )

            status_code = response.status_code
            content = json.loads(response.content)

            if status_code == 200:
                print(f"primary server {address}:{port} for zone {zone} updated.")
            else:
                print(content['error']['message'])

        except requests.exceptions.RequestException as e:
            logger.exception(e)

    def delete_primary_server(self, zone, address, port=53):
        """ Delete an primary server """
        try:
            ps_id = self._get_primary_server_id(zone, address, port)

            response = requests.delete(
                url=f"https://{self.SYSTEM}/api/v1/primary_servers/{ps_id}",
                headers={
                    "Auth-API-Token": self.API_TOKEN,
                },
            )

            status_code = response.status_code
            content = json.loads(response.content)

            if status_code == 200:
                print("primary server successfully deleted.")
            else:
                print(content['error']['message'])

        except requests.exceptions.RequestException as e:
            logger.exception(e)


########################################################################################################################
# MAIN
@logger.catch
def main():
    fire.Fire(Hdns_cli)


if __name__ == '__main__':
    main()

