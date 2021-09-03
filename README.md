# hdns - Hetzner DNS CLI Tool

´´
NAME
    hdns - HDNS - CLI tool to administer Hetzner DNS via API - Version 1.0

SYNOPSIS
    hdns - COMMAND | VALUE

DESCRIPTION
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

COMMANDS
    COMMAND is one of the following:

     bulk_create_records
       Creates bulk records for zone

     create_primary_server
       Create primary server requires empty zone. This zone is after primary server is created a secondary zone.

     create_record
       Create new record in zone

     create_zone
       Create new Zone eg. hdns_cli create_zone --zone example.org

     delete_primary_server
       Delete an primary server

     delete_record
       Delete record if record is unique.

     delete_record_by_id
       Delete record with record_id if record is not unique

     delete_records
       Delete records which are identical

     delete_zone
       Delete complete zone

     export_zone
       Export zone to file

     import_zone
       Import zone file to zone, WARNING: everything will be overwritten!

     show_primary_servers
       Shows all primary servers configured

     show_records
       Shows records of given zone eg. hdns_cli show_records --zone example.org

     show_system
       Shows the current used system

     show_token
       Shows the current used token

     show_zones
       Show all zones eg. hdns_cli show_zones

     update_primary_server
       Update primary server

     update_record
       Update exsisting record, record_id required

     update_zone
       Update zone parameters

     validate_zonefile
       Validate zone file

VALUES
    VALUE is one of the following:

     API_TOKEN

     SYSTEM
´´



