# hdns - Hetzner DNS CLI Tool

## Description
Hetzner provides an DNS service completely manageable via API,
this tool gives you easy access via CLI to the functions.

---
Written by Maximilian Thoma 2021, released under GNU General Public License v3.0

More on https://lanbugs.de or https://github.com/lanbugs/hdns_cli

## Installation

### via PIP
```
pip install hdns_cli
```

### from Source
```
python -m venv venv
source venv/bin/activate
git clone git@github.com:lanbugs/hdns_cli.git
cd hdns_cli
pip install -r requirements.txt
python setup.py install
```

## Server & API Token

You have the following options to create an INI file:
- In your home directory ~/.hdns/hdns.ini
- In your /etc directory /etc/hdns/hdns.ini
- In the program path ./hdns.ini

You can also start hdns with parameters:
```
hdns --system dns.hetzner.com --token <your_api_key> show_records thoma-lab.de
```

## Commands
All examples are made with domain exmaple.org.

### Available commands
```
Usage: hdns - <command|value>
  available commands:    bulk_create_records | create_primary_server |
                         create_record | create_zone | delete_primary_server |
                         delete_record | delete_record_by_id | delete_records |
                         delete_zone | export_zone | import_zone |
                         show_primary_servers | show_records | show_system |
                         show_token | show_zones | update_primary_server |
                         update_record | update_zone | validate_zonefile
  available values:      API_TOKEN | SYSTEM
```

### show_zones
Show all zones.

#### Example
```
$ hdns show_zones
*** Zones @ dns.hetzner.com ********************************************************************************
ID                      Zone           Secondary?    NS
----------------------  -------------  ------------  --------------------------------------------------------------------
xxxxxxxxxxxxxxxxxxxxxx  example.org    False         hydrogen.ns.hetzner.com, oxygen.ns.hetzner.com, helium.ns.hetzner.de
```

### create_zone
Create a new zone. If you define no primary servers the zone is a master zone. 

#### Example
```
Usage: hdns create_zone ZONE <flags>
  optional flags:        --ttl

hdns create_zone --zone example.org

or

hdns create_zone example.org
```

### update_zone
Update zone parameters.

#### Example
```
Usage: hdns update_zone ZONE TTL

hdns update_zone --zone example.org --ttl 600

or

hdns update_zone example.org 600
```

### delete_zone
Delete complete zone.

Per default the program asks you if you really want to delete the zone. The complete zone and records will be deleted. If you want to force this you can use the parameter --force True

#### Example
```
Usage: hdns delete_zone ZONE <flags>
  optional flags:        --force

hdns delete_zone --zone example.org [--force True]

or

hdns delete_zone example.org [--force True]
```

### import_zone
Import zone file to zone, **WARNING: everything will be overwritten!** The zone file must be in bind format.

#### Example
```
Usage: hdns import_zone ZONE FILE

hdns import_zone --zone example.org --file example_org.zone

or 

hdns import_zone example.org example_org.zone
```

### export_zone
Export zone to file or show it on CLI.

#### Example
```
Usage: hdns export_zone ZONE <flags>
  optional flags:        --file

hdns export_zone --zone example.org [--file example_org.zone]

or 

hdns export_zone example.org [--file example_org.zone]
```

### validate_zonefile
Validate zone file.

#### Example
```
Usage: hdns validate_zonefile FILE

hdns hdns validate_zonefile --file test.zone

or

hdns validate_zonefile test.zone
```

### create_record
Create new record in zone.

#### Example
```
hdns create_record --zone example.org --name www --type A --value 1.1.1.1

or

hdns create_record example.org www A 1.1.1.1
```

### show_records
Shows records of given zone.

#### Example
```
Usage: hdns show_records ZONE <flags>
  optional flags:        --id
  
hdns show_records --zone example.org

or 

hdns show_records example.org
```

### update_record
Update exsisting record, unique record or record_id required.

#### Example 
```
Usage: hdns update_record ZONE NAME TYPE VALUE <flags>
  optional flags:        --name_new | --value_new | --record_id

hdns update_record --zone example.org --name www --type A --value 1.1.1.1 --value_new 1.0.0.1

or 

hdns update_record example.org www A 1.1.1.1 --value_new 1.0.0.1
```

### delete_record
Delete record if record is unique.

##### Example 
```
Usage: hdns delete_record ZONE NAME TYPE VALUE

hdns delete_record --zone example.org --name www --type A --value 1.1.1.1

or 

hdns delete_record example.org www A 1.1.1.1
```

### delete_records
Delete records which are identical. For example you have several identical records by error.

#### Example 
```
Usage: hdns delete_records ZONE NAME TYPE VALUE

hdns delete_records --zone example.org --name www --type A --value 1.1.1.1

or 

hdns delete_records example.org www A 1.1.1.1
```


### delete_record_by_id
Delete record with record_id if record is not unique.

####Example
```
Usage: hdns delete_record_by_id RECORD_ID

hdns delete_record_by_id --record_id xxxxxxxxxxxxxxxxxxxxx

or

hdns delete_record_by_id xxxxxxxxxxxxxxxxxxxxx
```
### bulk_create_records
Creates bulk records for zone the records file must be presented in YAML style.

#### Example
YAML File:
```
---
records:
  - name: www
    type: A
    value: 1.1.1.1
    zone: thoma-lab.de
  - name: www
    type: AAAA
    value: 2001::1
    zone: thoma-lab.de
```

To create all records start hdns with the following parametes.
```
hdns bulk_create_records --file records.yaml

or

hdns bulk_create_records records.yaml
```

### show_primary_servers
Shows all primary servers configured.

#### Example
```
hdns show_primary_servers

Zone           IP              Port
-------------  ------------  ------
example.org    1.1.1.1       53
example.net    1.0.0.1       5353
```
### create_primary_server
Create primary server requires empty zone. This zone is after primary server is created a secondary zone.
You can only define a primary server if the zone is emtpy.

#### Example
```
Usage: hdns create_primary_server ZONE ADDRESS <flags>
  optional flags:        --port

hdns create_primary_server --zone example.org --address 1.1.1.1 [--port 53]  

or

hdns create_primary_server example.org 1.1.1.1 [--port 53]
```

### update_primary_server
Update primary server.

#### Example
```
Usage: hdns update_primary_server ZONE ADDRESS <flags>
  optional flags:        --port | --address_new | --port_new

hdns update_primary_server --zone example.org --address 1.1.1.1 --address_new 1.0.0.1

or 

hdns update_primary_server example.org 1.1.1.1 --address_new 1.0.0.1
```

### delete_primary_server
Delete a primary server. Default port 53 is set, parameter only needed if not default port.

#### Example
```
Usage: hdns delete_primary_server ZONE ADDRESS <flags>
  optional flags:        --port
  
hdns delete_primary_server --zone example.org --address 1.1.1.1 [--port 5353]

or

hdns delete_primary_server example.org 1.1.1.1 [--port 5353]
```
### show_system
Shows the current used system.

#### Example
```
hdns show_system
dns.hetzner.com
```
### show_token
Shows the current used token.
#### Example
```
hdns show_token
xxxxxxxxxxxxxxxxxxxxxxx
```
