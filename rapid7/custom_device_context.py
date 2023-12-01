#!/usr/bin/env python

import argparse
import csv
import requests

from requests.auth import HTTPBasicAuth
from typing import Dict, List, Optional

API_URI = "https://api.wootuno.wootcloud.com/v2/integrations/custom_devicecontext"
SOURCE = "rapid7"

# User can update values
REPORT_ID = "Scan report"
REPORT_TIMESTAMP = "2021-08-26T00:58:58Z"


# User has to find out mac address based on IP and pass to custom device context API

# Gets scan report details using Rapid7 InsightVM API
def get_report(username: str, pwd: str, report_id: int, instance: str, host: str, port: int) -> str:
    # Report download API https://help.rapid7.com/insightvm/en-us/api/index.html#operation/downloadReport
    download_api_url = f"https://{host}:{port}/api/3/reports/{report_id}/history/{instance}/output"
    download_response = requests.get(download_api_url, auth=HTTPBasicAuth(username, pwd))
    return download_response.text


def convert_csv_str_to_dict(report: str) -> List[Dict]:
    return [dict(row) for row in csv.DictReader(report.split("\n"))]


def push_data(client_id: str, secret_key: str, transaction_id: str, devices:List[Dict]):
    api_payload = {"transaction_id": transaction_id, "data": devices}
    response = requests.post(API_URI,
                             auth=HTTPBasicAuth(client_id, secret_key),
                             json=api_payload)
    if response.status_code == 202:
        print(f"Accepted")
    elif response.status_code in [401, 429]:
        print(f"Failed with reason: {response.reason}")
    elif response.status_code == 400:
        response = response.json()
        print(f"Failed with reason: {response['message']}. Payload: {api_payload}")


# Parses report and push to devicecontext API
def map_and_call_device_context_api(report: str, client_id: str, secret_key: str, transaction_id: str):
    report = convert_csv_str_to_dict(report)
    count = 0
    devices = []
    for row in report:
        devices.append({
            # Added mac address here just to show payload, mac address is MANDATORY field
            "mac_address": "",
            "ip": row['Asset IP Address'],
            "use_scan": True,
            "scan": {
                "report_id": REPORT_ID,
                "timestamp": REPORT_TIMESTAMP,
                "vulnerabilities": [{
                    "port": row['Service Port'],
                    "severity":float(row['Vulnerability Severity Level']),
                    "cve":row['Vulnerability CVE IDs'],
                    "vulnerability_id":row['Vulnerability ID'],
                    "vulnerability_name":row['Vulnerability Title']
                }]
            }
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
    parser = argparse.ArgumentParser(description="Script to use WootCloud custom device context API")
    parser.add_argument("--client_id", type=str, required=True, help="WootCloud client id")
    parser.add_argument("--secret_key", type=str, required=True, help="WootCloud secret key")
    parser.add_argument("--username", type=str, required=True, help="Rapid7 InsightVM username")
    parser.add_argument("--pwd", type=str, required=True, help="Rapid7 InsightVM password")
    parser.add_argument("--report_id", type=int, required=True, help="Identifier of Rapid7 report")
    parser.add_argument("--instance", type=str, required=True, help="Identifier of the Rapid7 report instance")
    parser.add_argument("--host", type=str, required=True, help="Host to access InsightVM")
    parser.add_argument("--port", type=int, help="Port to access InsightVM", default=3780)
    return parser.parse_args()


def main():
    args = parse_args()
    report = get_report(args.username, args.pwd, args.report_id, args.instance, args.host, args.port)
    transaction_id = start_transaction(args.client_id, args.secret_key)
    map_and_call_device_context_api(report, args.client_id, args.secret_key, transaction_id)
    close_transaction(args.client_id, args.secret_key, transaction_id)


if __name__ == "__main__":
    main()
