import base64
import json
import os
import uuid
import time
from ctypes import CDLL

import requests
import urllib3

from common import LicCryptoLib, FsKeysStore

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

products_types = {
    "doc": 1,
    "face": 41
}

host = "https://v2license-test-ingest-alb-euc1-1540784074.eu-central-1.elb.amazonaws.com"
dll_path = "./libSecure.so"
lic_crypto = LicCryptoLib(CDLL(dll_path), FsKeysStore())


def send_transaction(session_id, container_id, scenario, product_id, app_id, os, product_version, api_version,
                     core_version, core_mode, tag):
    lic_request = {
        'container_id': container_id,
        'session_id': session_id,
        'trans_id': uuid.uuid1().hex,
        "processParam": {"scenario": scenario},
        "product_id": product_id,
        "appId": app_id,
        "os": os,
        "product_version": product_version,
        "apiVersion": api_version,
        "coreVersion": core_version,
        "coreMode": core_mode,
        "tag": tag

    }

    enc_lic_request = lic_crypto.encrypt(json.dumps(lic_request))
    return requests.post(f"{host}/validate", json=enc_lic_request, verify=False)


def register_session(container_id, scenario, product_id, app_id, os, product_version, api_version, core_version,
                     core_mode, tag):
    session_id = uuid.uuid1().hex
    session_request = {
        'container_id': container_id,
        'session_id': session_id,
        "processParam": {"scenario": scenario},
        "product_id": product_id,
        "appId": app_id,
        "os": os,
        "product_version": product_version,
        "apiVersion": api_version,
        "coreVersion": core_version,
        "coreMode": core_mode,
        "tag": tag
    }
    enc_session_request = lic_crypto.encrypt(json.dumps(session_request))

    for _ in range(3):
        session_response = requests.post(f"{host}/session/register", json=enc_session_request, verify=False)

        if session_response.status_code == 200:
            return session_id

        time.sleep(1)


def vpn(country):
    if country:
        vpn_output = os.popen(f'windscribe connect {country}').read()

        if (vpn_output.split('\n')[-2]) == "Failed to connect":
            print("\nSomething went wrong. VPN has not been connected\n")
        else:
            print("\nVPN has been connected\n")
    else:
        vpn_output = os.popen('windscribe disconnect').read()

        if (vpn_output.split('\n')[-2]) == "DISCONNECTED":
            print("\nVPN has been disconnected\n")
        else:
            print("\nSomething went wrong. VPN has not been disconnected\n")


def offline_run(country, container_id, scenario, app_id, os, product_type, product_version, api_version,
                core_version, core_mode, tag, session_count, transactions_per_session, product_id, requests_count,
                user_id):
    # vpn(country)

    print(f'Country: {country}\n'
          f'Container ID: {container_id} \n'
          f'App ID: {app_id} \n'
          f'OS: {os} \n'
          f'Product Version: {product_version} \n'
          f'Api Version: {api_version} \n'
          f'Core Version: {core_version} \n'
          f'Core Mode: {core_mode} \n'
          f'Tag: {tag} \n'
          f'Requests count: {requests_count} \n'
          f'User ID: {user_id if user_id else "null"}')

    host = "https://v2license-test-ingest-alb-euc1-1540784074.eu-central-1.elb.amazonaws.com"

    sum_200 = 0
    for i in range(requests_count):
        print(f"{i + 1}/{requests_count}")

        b64_lic_file = "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"
        lic_file = base64.b64decode(b64_lic_file)
        params = {
            "userId": user_id if user_id else f"{uuid.uuid4()}",
            "appId": app_id,
            "os": os,
            "product_version": product_version,
            "apiVersion": api_version,
            "coreVersion": core_version,
            "coreMode": core_mode,
            "tag": tag
        }

        response = requests.post(f"{host}/offlineUpdate?containerId={container_id}",
                                 params=params, data=lic_file, verify=False)

        if response.status_code == 200:
            sum_200 += 1

    print(f"Summary: {sum_200} of {requests_count} requests was successful")

    return container_id


def online_run(country, container_id, scenario, app_id, os, product_type, product_version, api_version,
               core_version, core_mode, tag, session_count, transactions_per_session, product_id, requests_count,
               user_id):
    # vpn(country)

    print(f'Country: {country}\n'
          f'Container ID: {container_id}\n'
          f'Scenario: {scenario} \n'
          f'App ID: {app_id} \n'
          f'OS: {os}\n'
          f'Product Type: {product_type} \n'
          f'Product Version: {product_version} \n'
          f'Api Version: {api_version} \n'
          f'Core Version: {core_version} \n'
          f'Core Mode: {core_mode} \n'
          f'Tag: {tag} \n'
          f'Session count: {session_count}\n'
          f'Transactions per session: {transactions_per_session}')

    sessions_sum_200_transactions = []
    sessions_200 = 0

    for session in range(session_count):
        sessions_sum_200_transactions.append(0)

        session_id = register_session(container_id, scenario, product_id, app_id, os, product_version, api_version,
                                      core_version, core_mode, tag)
        if session_id:
            sessions_200 += 1
            for transaction in range(transactions_per_session):
                print(
                    f"Session: {session + 1}/{session_count}. Transaction {transaction + 1}/{transactions_per_session}")

                response = send_transaction(session_id, container_id, scenario, product_id, app_id, os,
                                            product_version, api_version, core_version, core_mode, tag)

                if response.status_code in (200, 406):
                    sessions_sum_200_transactions[session] += 1

    print(f"Successfully registered sessions: {sessions_200} of {session_count}")
    print(f"Successful transactions per each session: {sessions_sum_200_transactions}")

    return container_id


def get_variables(config):
    global country, container_id, scenario, app_id, os, product_type, product_version, api_version, core_version, core_mode, tag, session_count, transactions_per_session, product_id, requests_count, user_id

    if not config:
        return

    country = config.get("country")
    vpn(country)

    container_id = config.get("container_id")
    scenario = config.get("scenario")
    app_id = config.get("app_id")
    os = config.get("os")
    product_type = config.get("product_type")
    product_id = products_types.get(config.get("product_type"))
    product_version = config.get("product_version")
    api_version = config.get("api_version")
    core_version = config.get("core_version")
    core_mode = config.get("core_mode")
    tag = config.get("tag")
    session_count = config.get("session_count")
    transactions_per_session = config.get("transactions_per_session")

    requests_count = config.get("requests_count")
    if requests_count:
        requests_count = int(requests_count)

    user_id = config.get("user_id", None)


def get_config(transaction_type):
    try:
        with open(f"{transaction_type}_config.json", "r") as conf_file:
            return json.load(conf_file)
    except FileNotFoundError:
        print(f"Please provide {transaction_type}_config.json file")
        return
    except json.JSONDecodeError:
        print(f"{transaction_type}_config.json file is not valid json")
        return


def run(transaction_type, run_function):
    config = get_config(transaction_type)

    for i in range(len(config)):
        get_variables(config[i])
        container_id_all.append(
            run_function(country, container_id, scenario, app_id, os, product_type, product_version, api_version,
                         core_version, core_mode, tag, session_count, transactions_per_session, product_id,
                         requests_count, user_id))


def main():
    global container_id_all
    container_id_all = []
    # run("online", online_run)
    run("offline", offline_run)


if __name__ == "__main__":
    main()
