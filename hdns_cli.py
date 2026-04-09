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
VALID_TYPES = ['A', 'AAAA', 'NS', 'MX', 'CNAME', 'RP', 'TXT', 'SOA', 'HINFO', 'SRV', 'DANE', 'TLSA', 'DS', 'CAA',
               'HTTPS', 'SVCB', 'PTR']

########################################################################################################################
# HDNS CLI
########################################################################################################################
class Hdns_cli(object):
    """HDNS - CLI tool to administer Hetzner DNS via API - Version 2.0.0\n
    Hetzner provides an DNS service completely manageable via API,
    this tool gives you easy access to the functions.

    To use define --system api.hetzner.cloud --token <your_api_key> or simply store
    it in an config ini file.

    You have the following options:
    - ~/.hdns/hdns.ini
    - /etc/hdns/hdns.ini
    - ./hdns.ini

    Content:
    [general]
    system=api.hetzner.cloud
    token=<your_token>

    Note: API tokens must be created in the Hetzner Cloud Console,
    not the old DNS Console. Old tokens are not compatible.

    ---
    Written by Maximilian Thoma 2021, released under GNU General Public License v3.0
    More on https://lanbugs.de or https://github.com/lanbugs/hdns_cli
    :param token: Token for authentication
    :param system: FQDN of the DNS System used, eg. api.hetzner.cloud
    """

    def __init__(self, token=TOKEN, system=SYSTEM):
        self.API_TOKEN = token
        self.SYSTEM = system

    def _auth_header(self):
        return {"Authorization": f"Bearer {self.API_TOKEN}"}

    def show_token(self):
        """ Shows the current used token """
        print(self.API_TOKEN)

    def show_system(self):
        """ Shows the current used system """
        print(self.SYSTEM)

    def _get_all_rrsets(self, zone_id):
        """ PRIVATE: Fetch all RRsets of a zone, handling pagination """
        rrsets = []
        page = 1
        while True:
            response = requests.get(
                url=f"https://{self.SYSTEM}/v1/zones/{zone_id}/rrsets",
                params={"page": page, "per_page": 100},
                headers=self._auth_header(),
            )
            content = json.loads(response.content)
            if response.status_code != 200:
                raise RuntimeError(content.get('error', {}).get('message', str(content)))
            rrsets.extend(content.get('rrsets', []))
            pagination = content.get('meta', {}).get('pagination', {})
            if page >= pagination.get('last_page', 1):
                break
            page += 1
        return rrsets

    def _get_all_records(self, zone_id):
        """ PRIVATE: Fetch all records by flattening RRsets into individual record objects """
        records = []
        for rrset in self._get_all_rrsets(zone_id):
            for record in rrset.get('records', []):
                records.append({
                    'id': f"{rrset['name']}/{rrset['type']}",
                    'name': rrset['name'],
                    'type': rrset['type'],
                    'ttl': rrset.get('ttl', 0),
                    'value': record['value'],
                })
        return records

    def _get_rrset(self, zone_id, name, type):
        """ PRIVATE: Fetch a single RRset by name and type, returns None if not found """
        response = requests.get(
            url=f"https://{self.SYSTEM}/v1/zones/{zone_id}/rrsets/{name}/{type}",
            headers=self._auth_header(),
        )
        if response.status_code == 200:
            return json.loads(response.content).get('rrset')
        return None

    def _put_rrset(self, zone_id, name, type, records, ttl=0):
        """ PRIVATE: Replace an existing RRset (must already exist) """
        response = requests.put(
            url=f"https://{self.SYSTEM}/v1/zones/{zone_id}/rrsets/{name}/{type}",
            headers={"Content-Type": "application/json", **self._auth_header()},
            data=json.dumps({"ttl": ttl, "records": records}),
        )
        return response

    def _post_rrset(self, zone_id, name, type, records, ttl=0):
        """ PRIVATE: Create a new RRset """
        response = requests.post(
            url=f"https://{self.SYSTEM}/v1/zones/{zone_id}/rrsets",
            headers={"Content-Type": "application/json", **self._auth_header()},
            data=json.dumps({"name": name, "type": type, "ttl": ttl, "records": records}),
        )
        return response

    def _delete_rrset(self, zone_id, name, type):
        """ PRIVATE: Delete an entire RRset """
        return requests.delete(
            url=f"https://{self.SYSTEM}/v1/zones/{zone_id}/rrsets/{name}/{type}",
            headers=self._auth_header(),
        )

    def _get_zone_id(self, zone_name):
        """ PRIVATE: Get the zone id to work with names in records add, mod, remove """
        try:
            response = requests.get(
                url=f"https://{self.SYSTEM}/v1/zones",
                params={"name": zone_name},
                headers=self._auth_header()
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

    ####################################################################################################################
    # Everything regarding zones

    def show_zones(self):
        """ Show all zones eg. hdns show_zones """
        try:
            response = requests.get(
                url=f"https://{self.SYSTEM}/v1/zones",
                headers=self._auth_header()
            )

            status_code = response.status_code
            content = json.loads(response.content)

            if status_code == 200:
                result_header = ['ID', 'Zone', 'Mode', 'NS']
                results = []

                for zone in content['zones']:
                    # Support both old (is_secondary_dns) and new (mode) field names
                    if 'mode' in zone:
                        mode = zone['mode']
                    else:
                        mode = 'secondary' if zone.get('is_secondary_dns') else 'primary'

                    # Support both old (ns) and new (authoritative_nameservers) field names
                    ns_list = zone.get('ns', zone.get('authoritative_nameservers', []))
                    ns = ", ".join(ns_list) if ns_list else ''

                    results.append([zone['id'], zone['name'], mode, ns])

                print(f"*** Zones @ {self.SYSTEM} " + "*"*80)
                print(tabulate.tabulate(results, result_header))

        except requests.exceptions.RequestException as e:
            logger.exception(e)

    def create_zone(self, zone, ttl=86400):
        """
        Create new Zone eg. hdns create_zone --zone example.org
        :param zone: Name of the zone, eg. example.org
        :param ttl: Time to live, default: 86400
        """
        try:
            response = requests.post(
                url=f"https://{self.SYSTEM}/v1/zones",
                headers={
                    "Content-Type": "application/json",
                    **self._auth_header(),
                },
                data=json.dumps({
                    "name": zone,
                    "ttl": ttl,
                    "mode": "primary"
                })
            )

            status_code = response.status_code
            content = json.loads(response.content)

            if status_code in (200, 201):
                print(f"zone {zone} created.")
            else:
                print(content.get('error', {}).get('message', str(content)))

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
                url=f"https://{self.SYSTEM}/v1/zones/{zone_id}",
                headers={
                    "Content-Type": "application/json",
                    **self._auth_header(),
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
                print(content.get('error', {}).get('message', str(content)))

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
                    url=f"https://{self.SYSTEM}/v1/zones/{zone_id}",
                    headers=self._auth_header(),
                )

                status_code = response.status_code

                if status_code in (200, 204):
                    print(f"zone {zone} deleted.")
                else:
                    pprint(json.loads(response.content))

            else:
                print(f"Delete zone {zone} aborted ...")

        except requests.exceptions.RequestException as e:
            logger.exception(e)


    ####################################################################################################################
    # Everything regarding records

    def show_records(self, zone, id=False):
        """
        Shows records of given zone eg. hdns show_records --zone example.org
        :param zone: Name of the zone, eg. example.org
        :param id: Show record ids if True
        """
        zone_id = self._get_zone_id(zone)

        try:
            records = self._get_all_records(zone_id)

            print(f"*** Records @ {zone} " + "*" * 80)
            if records is not None:

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

            if type not in VALID_TYPES:
                print(f"Given type {type} is not supported.")
                return

            rrset = self._get_rrset(zone_id, name, type)
            if rrset:
                # RRset exists: add value to it via PUT
                existing_values = [r['value'] for r in rrset.get('records', [])]
                if value in existing_values:
                    print(f"Record {name} {type} {value} already exists.")
                    return
                response = self._put_rrset(zone_id, name, type,
                                           [{"value": v} for v in existing_values + [value]],
                                           rrset.get('ttl', ttl))
            else:
                # RRset does not exist: create via POST
                response = self._post_rrset(zone_id, name, type, [{"value": value}], ttl)

            if response.status_code in (200, 201):
                print("record successful created.")
            else:
                print(json.loads(response.content).get('error', {}).get('message', str(response.content)))

        except (requests.exceptions.RequestException, RuntimeError) as e:
            logger.exception(e)

    def set_zone_ttl(self, zone, ttl=0):
        """
        Set TTL for all records in a zone at once.
        Use ttl=0 to reset to Hetzner global TTL (zone default).
        Useful before IP changes (set low TTL) or to revert afterwards.
        :param zone: Name of the zone, eg. example.org
        :param ttl: TTL value in seconds, 0 = use zone default (Hetzner global TTL)
        """
        try:
            zone_id = self._get_zone_id(zone)
            records = self._get_all_records(zone_id)
            updated = 0
            failed = 0

            for rrset in self._get_all_rrsets(zone_id):
                r = self._put_rrset(zone_id, rrset['name'], rrset['type'],
                                    rrset.get('records', []), ttl)
                if r.status_code == 200:
                    updated += 1
                else:
                    failed += 1
                    print(f"Failed to update {rrset['name']} {rrset['type']}: {r.content}")

            ttl_label = f"{ttl}s" if ttl > 0 else "zone default"
            print(f"TTL set to {ttl_label} for {updated} records in {zone}" +
                  (f", {failed} failed." if failed else "."))

        except (requests.exceptions.RequestException, RuntimeError) as e:
            logger.exception(e)

    def replace_ip(self, zone, old_ip, new_ip):
        """
        Replace an IP address in all A/AAAA records of a zone.
        Useful when a server IP changes and needs to be updated everywhere.
        :param zone: Name of the zone, eg. example.org
        :param old_ip: IP address to replace, eg. 1.2.3.4
        :param new_ip: New IP address, eg. 5.6.7.8
        """
        try:
            zone_id = self._get_zone_id(zone)
            matches = [rrset for rrset in self._get_all_rrsets(zone_id)
                       if rrset['type'] in ('A', 'AAAA')
                       and any(r['value'] == old_ip for r in rrset.get('records', []))]

            if not matches:
                print(f"No A/AAAA records with value {old_ip} found in {zone}.")
                return

            updated = 0
            failed = 0

            for rrset in matches:
                new_records = [{"value": new_ip if r['value'] == old_ip else r['value']}
                               for r in rrset.get('records', [])]
                r = self._put_rrset(zone_id, rrset['name'], rrset['type'],
                                    new_records, rrset.get('ttl', 0))
                if r.status_code == 200:
                    print(f"  {rrset['name']} {rrset['type']}: {old_ip} -> {new_ip}")
                    updated += 1
                else:
                    print(f"  Failed to update {rrset['name']} {rrset['type']}: {r.content}")
                    failed += 1

            print(f"Replaced {old_ip} with {new_ip} in {updated} record(s)" +
                  (f", {failed} failed." if failed else "."))

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

        except Exception as e:
            logger.exception(e)

    def update_record(self, zone, name, type, value, name_new=None, value_new=None):
        """
        Update existing record by replacing a specific value within its RRset.
        :param zone: Name of the zone, eg. example.org
        :param name: Name of the record, eg. www
        :param type: Type of record eg. A, valid are A, AAAA, NS, MX, CNAME, RP, TXT, SOA, HINFO, SRV, DANE, TLSA, DS, CAA
        :param value: Current value of the record eg. 1.1.1.1
        :param name_new: New name of the record (moves to a different RRset)
        :param value_new: New value of the record eg. 2.2.2.2
        """
        try:
            zone_id = self._get_zone_id(zone)

            if name_new is None:
                name_new = name
            if value_new is None:
                value_new = value

            rrset = self._get_rrset(zone_id, name, type)
            if not rrset:
                print(f"RRset {name} {type} not found in zone {zone}.")
                return

            current_values = [r['value'] for r in rrset.get('records', [])]
            if value not in current_values:
                print(f"Value {value} not found in {name} {type}.")
                return

            if name_new == name:
                # Same RRset: replace value in-place
                new_records = [{"value": value_new if v == value else v} for v in current_values]
                response = self._put_rrset(zone_id, name, type, new_records, rrset.get('ttl', 0))
            else:
                # Different name: remove from old RRset, add to new RRset
                remaining = [{"value": v} for v in current_values if v != value]
                if remaining:
                    self._put_rrset(zone_id, name, type, remaining, rrset.get('ttl', 0))
                else:
                    self._delete_rrset(zone_id, name, type)

                target_rrset = self._get_rrset(zone_id, name_new, type)
                target_values = [r['value'] for r in target_rrset.get('records', [])] if target_rrset else []
                target_ttl = target_rrset.get('ttl', rrset.get('ttl', 0)) if target_rrset else rrset.get('ttl', 0)
                response = self._put_rrset(zone_id, name_new, type,
                                           [{"value": v} for v in target_values + [value_new]], target_ttl)

            if response.status_code == 200:
                print("record successful updated.")
            else:
                print(json.loads(response.content).get('error', {}).get('message', str(response.content)))

        except (requests.exceptions.RequestException, RuntimeError) as e:
            logger.exception(e)

    def delete_record(self, zone, name, type, value):
        """
        Delete a specific value from an RRset. If no values remain, the RRset is deleted.
        :param zone: Name of the zone, eg. example.org
        :param name: Name of the record, eg. www
        :param type: Type of record eg. A, valid are A, AAAA, NS, MX, CNAME, RP, TXT, SOA, HINFO, SRV, DANE, TLSA, DS, CAA
        :param value: Value of the record eg. 1.1.1.1
        """
        try:
            zone_id = self._get_zone_id(zone)
            rrset = self._get_rrset(zone_id, name, type)
            if not rrset:
                print(f"RRset {name} {type} not found in zone {zone}.")
                return

            remaining = [{"value": r['value']} for r in rrset.get('records', []) if r['value'] != value]

            if len(remaining) == len(rrset.get('records', [])):
                print(f"Value {value} not found in {name} {type}.")
                return

            if remaining:
                response = self._put_rrset(zone_id, name, type, remaining, rrset.get('ttl', 0))
            else:
                response = self._delete_rrset(zone_id, name, type)

            if response.status_code in (200, 204):
                print("record successfully deleted.")
            else:
                print(json.loads(response.content))

        except (requests.exceptions.RequestException, RuntimeError) as e:
            logger.exception(e)

    def delete_records(self, zone, name, type, value):
        """
        Alias for delete_record. In the RRset model duplicates cannot exist.
        :param zone: Name of the zone, eg. example.org
        :param name: Name of the record, eg. www
        :param type: Type of record eg. A
        :param value: Value of the record eg. 1.1.1.1
        """
        self.delete_record(zone, name, type, value)

    def delete_record_by_id(self, zone, record_id):
        """
        Delete an entire RRset by its ID (format: name/type, eg. www/A).
        The ID is shown when using show_records --id True.
        :param zone: Name of the zone, eg. example.org
        :param record_id: RRset ID in name/type format, eg. www/A
        """
        try:
            zone_id = self._get_zone_id(zone)
            # record_id is "name/type", split on last "/"
            parts = record_id.rsplit('/', 1)
            if len(parts) != 2:
                print(f"Invalid record_id format '{record_id}'. Expected name/type, eg. www/A.")
                return
            name, rtype = parts

            response = self._delete_rrset(zone_id, name, rtype)
            if response.status_code in (200, 204):
                print("record successfully deleted.")
            else:
                print(json.loads(response.content))

        except (requests.exceptions.RequestException, RuntimeError) as e:
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
                url=f"https://{self.SYSTEM}/v1/zones/{zone_id}/actions/import_zonefile",
                headers={
                    "Content-Type": "text/plain",
                    **self._auth_header(),
                },
                data=content
            )

            status_code = response.status_code
            content = json.loads(response.content)

            if status_code in (200, 201):
                print(f"zone file successfully imported in zone {zone}.")
            else:
                print(content.get('error', {}).get('message', str(content)))

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
                url=f"https://{self.SYSTEM}/v1/zones/{zone_id}/zonefile",
                headers=self._auth_header(),
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
                url=f"https://{self.SYSTEM}/v1/zones/file/validate",
                headers={
                    "Content-Type": "text/plain",
                    **self._auth_header(),
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
                print(content.get('error', {}).get('message', str(content)))

        except requests.exceptions.RequestException as e:
            logger.exception(e)

    ####################################################################################################################
    # Everything regarding secondary zones
    def show_primary_servers(self, id=False):
        """
        Shows all primary servers configured for secondary zones
        :param id: Show zone ids if True
        """
        try:
            response = requests.get(
                url=f"https://{self.SYSTEM}/v1/zones",
                headers=self._auth_header()
            )

            status_code = response.status_code
            content = json.loads(response.content)

            if status_code == 200:
                if id is False:
                    header = ['Zone', 'IP', 'Port']
                else:
                    header = ['Zone ID', 'Zone', 'IP', 'Port']

                rows = []

                for zone in content['zones']:
                    is_secondary = zone.get('mode') == 'secondary' or zone.get('is_secondary_dns', False)
                    if not is_secondary:
                        continue

                    for ps in zone.get('primary_nameservers', []):
                        address = ps.get('address', ps.get('ip', ''))
                        port = ps.get('port', 53)
                        if id is False:
                            rows.append([zone['name'], address, port])
                        else:
                            rows.append([zone['id'], zone['name'], address, port])

                print(tabulate.tabulate(rows, header))
            else:
                print("no records")

        except requests.exceptions.RequestException as e:
            logger.exception(e)

    def create_primary_server(self, zone, address, port=53):
        """
        Configure zone as secondary with a primary server.
        :param zone: Name of the zone, eg. example.org
        :param address: IPv4 or IPv6 address of the primary server
        :param port: Port of DNS server
        """
        try:
            zone_id = self._get_zone_id(zone)
            response = requests.put(
                url=f"https://{self.SYSTEM}/v1/zones/{zone_id}",
                headers={
                    "Content-Type": "application/json",
                    **self._auth_header(),
                },
                data=json.dumps({
                    "mode": "secondary",
                    "primary_nameservers": [{"address": address, "port": port}]
                })
            )

            status_code = response.status_code
            content = json.loads(response.content)

            if status_code == 200:
                print(f"primary_server {address}:{port} for zone {zone} created.")
            else:
                print(content.get('error', {}).get('message', str(content)))

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
            zone_id = self._get_zone_id(zone)

            if address_new is None:
                address_new = address

            if port_new is None:
                port_new = port

            # Fetch current zone to get existing primary servers
            response_zone = requests.get(
                url=f"https://{self.SYSTEM}/v1/zones/{zone_id}",
                headers=self._auth_header(),
            )
            zone_data = json.loads(response_zone.content).get('zone', {})
            primary_servers = zone_data.get('primary_nameservers', [])

            updated = False
            new_primary_servers = []
            for ps in primary_servers:
                ps_address = ps.get('address', ps.get('ip', ''))
                ps_port = ps.get('port', 53)
                if ps_address == address and ps_port == port:
                    new_primary_servers.append({"address": address_new, "port": port_new})
                    updated = True
                else:
                    new_primary_servers.append(ps)

            if not updated:
                print(f"Primary server {address}:{port} not found in zone {zone}.")
                return

            response = requests.put(
                url=f"https://{self.SYSTEM}/v1/zones/{zone_id}",
                headers={
                    "Content-Type": "application/json",
                    **self._auth_header(),
                },
                data=json.dumps({
                    "primary_nameservers": new_primary_servers
                })
            )

            status_code = response.status_code
            content = json.loads(response.content)

            if status_code == 200:
                print(f"primary server {address}:{port} for zone {zone} updated.")
            else:
                print(content.get('error', {}).get('message', str(content)))

        except requests.exceptions.RequestException as e:
            logger.exception(e)

    def delete_primary_server(self, zone, address, port=53):
        """ Delete a primary server from zone """
        try:
            zone_id = self._get_zone_id(zone)

            # Fetch current zone to get existing primary servers
            response_zone = requests.get(
                url=f"https://{self.SYSTEM}/v1/zones/{zone_id}",
                headers=self._auth_header(),
            )
            zone_data = json.loads(response_zone.content).get('zone', {})
            primary_servers = zone_data.get('primary_nameservers', [])

            new_primary_servers = [
                ps for ps in primary_servers
                if not (ps.get('address', ps.get('ip', '')) == address and ps.get('port', 53) == port)
            ]

            if len(new_primary_servers) == len(primary_servers):
                print(f"Primary server {address}:{port} not found in zone {zone}.")
                return

            new_mode = "secondary" if new_primary_servers else "primary"

            response = requests.put(
                url=f"https://{self.SYSTEM}/v1/zones/{zone_id}",
                headers={
                    "Content-Type": "application/json",
                    **self._auth_header(),
                },
                data=json.dumps({
                    "mode": new_mode,
                    "primary_nameservers": new_primary_servers
                })
            )

            status_code = response.status_code
            content = json.loads(response.content)

            if status_code == 200:
                print("primary server successfully deleted.")
            else:
                print(content.get('error', {}).get('message', str(content)))

        except requests.exceptions.RequestException as e:
            logger.exception(e)


########################################################################################################################
# MAIN
@logger.catch
def main():
    fire.Fire(Hdns_cli)


if __name__ == '__main__':
    main()
