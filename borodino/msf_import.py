#!/usr/bin/env python3
"""Import nmap XML scan results into Metasploit via msfrpc (db.import_data)."""
import sys
import os
import msgpack
import requests
import urllib3

urllib3.disable_warnings()

MSF_HOST = os.getenv('MSF_HOST', 'msf-teamserver')
MSF_PORT = int(os.getenv('MSF_PORT', '55553'))
MSF_PASS  = os.getenv('MSF_RPC_PASS', 'totototo')


def main():
    if len(sys.argv) < 2:
        print('[ERROR] Usage: msf_import.py <xml_file>', file=sys.stderr)
        sys.exit(1)

    xml_file = sys.argv[1]
    if not os.path.exists(xml_file):
        print(f'[WARN] XML file not found: {xml_file}', file=sys.stderr)
        sys.exit(0)

    with open(xml_file, 'r', errors='replace') as f:
        xml_data = f.read()

    if '<nmaprun' not in xml_data:
        print('[WARN] Empty/invalid nmap XML, skipping import')
        sys.exit(0)

    # Skip import if no hosts were found (saves RPC overhead)
    if '<host ' not in xml_data and '<host>' not in xml_data:
        print('[INFO] No hosts up in scan, skipping import')
        sys.exit(0)

    url = f'https://{MSF_HOST}:{MSF_PORT}/api/1.0/'

    # Authentification
    r = requests.post(url,
        data=msgpack.dumps([b'auth.login', 'msf', MSF_PASS]),
        headers={'Content-Type': 'binary/message-pack'},
        verify=False, timeout=30)
    result = msgpack.loads(r.content)
    token = result.get(b'token') or result.get('token')
    if not token:
        print(f'[ERROR] MSF auth failed: {result}', file=sys.stderr)
        sys.exit(1)

    # Import XML
    r = requests.post(url,
        data=msgpack.dumps([b'db.import_data', token, {b'data': xml_data}]),
        headers={'Content-Type': 'binary/message-pack'},
        verify=False, timeout=300)
    result = msgpack.loads(r.content)

    # Logout
    requests.post(url,
        data=msgpack.dumps([b'auth.logout', token, token]),
        headers={'Content-Type': 'binary/message-pack'},
        verify=False, timeout=10)

    status = result.get(b'result') or result.get('result', b'?')
    print(f'[INFO] MSF import: {status}')


if __name__ == '__main__':
    main()
