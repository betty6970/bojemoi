#!/usr/bin/env python3
"""
VulnX Wrapper - Daemon pour écouter les commandes de scan via Redis
"""

import os
import sys
import json
import subprocess
import time
import re
import logging
from datetime import datetime
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
RESULTS_DIR = Path(os.environ.get('RESULTS_DIR', '/results'))
VULNX_PATH = '/opt/vulnx/vulnx.py'

RESULTS_DIR.mkdir(exist_ok=True)


def run_vulnx_scan(target: str, scan_type: str = 'cms') -> dict:
    """Exécute un scan VulnX"""
    scan_id = f"vulnx_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_file = RESULTS_DIR / f"{scan_id}.json"

    logger.info(f"[VulnX] Starting {scan_type} scan on {target}")

    cmd = ['python', VULNX_PATH, '-u', target]

    if scan_type == 'cms':
        cmd.append('--cms')
    elif scan_type == 'full':
        cmd.extend(['--full', '-w', '-e'])
    elif scan_type == 'wordpress':
        cmd.extend(['--wp', '-w', '-e'])
    elif scan_type == 'joomla':
        cmd.extend(['--joom', '-e'])
    elif scan_type == 'drupal':
        cmd.extend(['--drupal', '-e'])
    elif scan_type == 'subdomain':
        cmd.append('--sub')

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600
        )

        output = result.stdout + result.stderr

        # Parse les résultats
        cms_detected = None
        cms_patterns = {
            'wordpress': r'WordPress',
            'joomla': r'Joomla',
            'drupal': r'Drupal',
            'magento': r'Magento',
            'prestashop': r'PrestaShop'
        }

        for cms, pattern in cms_patterns.items():
            if re.search(pattern, output, re.IGNORECASE):
                cms_detected = cms
                break

        vulns = []
        vuln_patterns = [r'\[VULN\].*', r'\[EXPLOIT\].*', r'\[CRITICAL\].*']
        for pattern in vuln_patterns:
            vulns.extend(re.findall(pattern, output, re.IGNORECASE))

        scan_result = {
            'scan_id': scan_id,
            'target': target,
            'scan_type': scan_type,
            'cms_detected': cms_detected,
            'vulnerabilities': vulns[:50],
            'raw_output': output[:10000],
            'status': 'completed',
            'timestamp': datetime.now().isoformat()
        }

        # Sauvegarde les résultats
        with open(output_file, 'w') as f:
            json.dump(scan_result, f, indent=2)

        logger.info(f"[VulnX] Scan completed: {scan_id}")
        return scan_result

    except subprocess.TimeoutExpired:
        return {
            'scan_id': scan_id,
            'target': target,
            'status': 'timeout',
            'error': 'Scan timeout (10 min)'
        }
    except Exception as e:
        logger.error(f"[VulnX] Error: {e}")
        return {
            'scan_id': scan_id,
            'target': target,
            'status': 'error',
            'error': str(e)
        }


def run_daemon():
    """Mode daemon - écoute Redis pour les commandes"""
    try:
        import redis
    except ImportError:
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', 'redis', '--break-system-packages'
        ])
        import redis

    logger.info(f"[VulnX] Daemon starting - Redis {REDIS_HOST}:{REDIS_PORT}")
    channel = 'vulnx:commands'

    while True:
        try:
            r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
            pubsub = r.pubsub()
            pubsub.subscribe(channel)
            logger.info(f"[VulnX] Listening on channel: {channel}")

            for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        target = data.get('target')
                        scan_type = data.get('type', 'cms')

                        if target:
                            result = run_vulnx_scan(target, scan_type)
                            r.publish('pentest:results', json.dumps({
                                'tool': 'vulnx',
                                **result
                            }))
                        else:
                            logger.warning("[VulnX] Missing target in command")

                    except json.JSONDecodeError as e:
                        logger.error(f"[VulnX] Invalid JSON: {e}")

        except redis.ConnectionError as e:
            logger.warning(f"[VulnX] Redis connection lost: {e}, reconnecting...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"[VulnX] Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='VulnX Wrapper')
    parser.add_argument('--daemon', action='store_true', help='Run in daemon mode')
    parser.add_argument('-t', '--target', help='Target URL')
    parser.add_argument('-s', '--scan-type', default='cms',
                       choices=['cms', 'full', 'wordpress', 'joomla', 'drupal', 'subdomain'])

    args = parser.parse_args()

    if args.daemon:
        run_daemon()
    elif args.target:
        result = run_vulnx_scan(args.target, args.scan_type)
        print(json.dumps(result, indent=2))
    else:
        parser.print_help()
