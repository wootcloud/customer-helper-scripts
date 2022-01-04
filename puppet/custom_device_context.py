#!/usr/bin/env python

import argparse
import io
import json
import requests

from dataclasses import dataclass
from requests.auth import HTTPBasicAuth
from typing import List

API_URI = "https://api.wootuno.wootcloud.com/v1/integrations/custom_devicecontext"
SOURCE = "puppet"


@dataclass
class PuppetInterface:
    mac_address: str
    ip: str
    hostname: str
    manufacturer: str
    os: str
    username: str

    @classmethod
    def from_json(cls, data):
        return cls(
            mac_address=data.get("macaddress"),
            ip=data.get("ipaddress"),
            hostname=data.get("hostname"),
            manufacturer=data.get("manufacturer"),
            os=data.get("os", {}).get("name"),
            username=data.get("identity", {}).get("user")
        )


def read_data_file(file: io.TextIOWrapper) -> List[PuppetInterface]:
    interfaces = []
    with file as f:
        for record in json.load(f):
            for _, interface in record.items():
                interfaces.append(PuppetInterface.from_json(interface["facts"]))
    return interfaces


# Maps puppet data to payload and calls devicecontext API
def map_and_call_device_context_api(puppet_interfaces: List[PuppetInterface], client_id: str, secret_key: str):
    for puppet_interface in puppet_interfaces:
        api_payload = {
            "mac_address": puppet_interface.mac_address,
            "ip": puppet_interface.ip,
            "source": SOURCE,
            "hostname": puppet_interface.hostname,
            "manufacturer": puppet_interface.manufacturer,
            "os": puppet_interface.os,
            "username": puppet_interface.username,
            "use_asset": True
        }
        response = requests.post(API_URI, auth=HTTPBasicAuth(client_id, secret_key), json=api_payload)
        if response.status_code == 202:
            print(f"Accepted. MAC address: {puppet_interface.mac_address}")
        elif response.status_code in [401, 429]:
            print(f"Failed MAC address[{puppet_interface.mac_address}] with reason: {response.reason}")
        elif response.status_code == 400:
            response = response.json()
            print(f"Failed with reason: {response['message']}. Payload: {api_payload}")


def parse_args():
    parser = argparse.ArgumentParser(description="Script to push puppet data to WootCloud custom device context API")
    parser.add_argument("--client_id", type=str, required=True, help="WootCloud client id")
    parser.add_argument("--secret_key", type=str, required=True, help="WootCloud secret key")
    parser.add_argument("--file", type=open, required=True, help="Puppet data file")
    return parser.parse_args()


def main():
    args = parse_args()
    puppet_interfaces = read_data_file(args.file)
    map_and_call_device_context_api(puppet_interfaces, args.client_id, args.secret_key)


if __name__ == "__main__":
    main()
