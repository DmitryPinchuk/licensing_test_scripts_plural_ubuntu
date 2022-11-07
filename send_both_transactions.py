import json
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


def online_run(country, container_id, scenario, app_id, os, product_type, product_version, api_version,
               core_version, core_mode, tag, session_count, transactions_per_session, product_id, requests_count, user_id):
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
               core_version, core_mode, tag, session_count, transactions_per_session, product_id, requests_count, user_id))


def main():
    global container_id_all
    container_id_all = []
    run("online", online_run)


if __name__ == "__main__":
    main()