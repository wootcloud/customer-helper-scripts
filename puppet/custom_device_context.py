#!/usr/bin/env python

import argparse
import io
import json
import requests

from dataclasses import dataclass
from requests.auth import HTTPBasicAuth
from typing import Dict, List, Optional

API_URI = "https://api.wootuno.wootcloud.com/v2/integrations/custom_devicecontext"
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


# Calls devicecontext API
def push_data(client_id: str, secret_key: str, transaction_id: str, devices:List[Dict]):
    api_payload = {"transaction_id": transaction_id, "data": devices}
    response = requests.post(API_URI, auth=HTTPBasicAuth(client_id, secret_key), json=api_payload)
    if response.status_code == 202:
        print(f"Accepted")
    elif response.status_code in [401, 429]:
        print(f"Failed with reason: {response.reason}")
    elif response.status_code == 400:
        response = response.json()
        print(f"Failed with reason: {response['message']}. Payload: {api_payload}")


# Maps puppet data to payload
def map_and_call_device_context_api(puppet_interfaces: List[PuppetInterface], client_id: str, secret_key: str,
                                    transaction_id: str):
    count = 0
    devices = []
    for puppet_interface in puppet_interfaces:
        devices.append({
            "mac_address": puppet_interface.mac_address,
            "ip": puppet_interface.ip,
            "hostname": puppet_interface.hostname,
            "manufacturer": puppet_interface.manufacturer,
            "os": puppet_interface.os,
            "username": puppet_interface.username,
            "use_asset": True
        })
        count += 1
        if count % 10 == 0:
            push_data(client_id, secret_key, transaction_id, devices)
            devices = []
    # Check if any devices are left and push
    if devices:
        push_data(client_id, secret_key, transaction_id, devices)


def start_transaction(client_id: str, secret_key: str) -> Optional[str]:
    response = requests.post(API_URI,
                             auth=HTTPBasicAuth(client_id, secret_key),
                             json={"source": SOURCE})
    if response.status_code == 200:
        print("Transaction started")
        response = response.json()
        return response["transaction_id"]
    elif response.status_code == 400:
        response = response.json()
        print("Transaction start failed: %s" % response["message"])


def close_transaction(client_id: str, secret_key: str, transaction_id: str):
    response = requests.post(API_URI,
                             auth=HTTPBasicAuth(client_id, secret_key),
                             json={"transaction_id": transaction_id, "data": []})
    if response.status_code == 200:
        print("Transaction closed")
    elif response.status_code == 400:
        response = response.json()
        print("Transaction close failed: %s" % response["message"])


def parse_args():
    parser = argparse.ArgumentParser(description="Script to push puppet data to WootCloud custom device context API")
    parser.add_argument("--client_id", type=str, required=True, help="WootCloud client id")
    parser.add_argument("--secret_key", type=str, required=True, help="WootCloud secret key")
    parser.add_argument("--file", type=open, required=True, help="Puppet data file")
    return parser.parse_args()


def main():
    args = parse_args()
    puppet_interfaces = read_data_file(args.file)
    transaction_id = start_transaction(args.client_id, args.secret_key)
    map_and_call_device_context_api(puppet_interfaces, args.client_id, args.secret_key, transaction_id)
    close_transaction(args.client_id, args.secret_key, transaction_id)


if __name__ == "__main__":
    main()
