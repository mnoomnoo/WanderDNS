#!/usr/bin/env python3
"""WanderDNS — update a cPanel Dynamic DNS entry with the current public IP."""

import argparse
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install requests python-dotenv")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR / ".env"
LAST_IP_FILE = SCRIPT_DIR / ".last_ip"
IP_SERVICE = "https://api.ipify.org?format=json"


def load_config():
    if not ENV_FILE.exists():
        print(f"Error: {ENV_FILE} not found.")
        print(f"Copy {SCRIPT_DIR / '.env.example'} to {ENV_FILE} and fill in your credentials.")
        sys.exit(1)

    load_dotenv(ENV_FILE)

    required = ["CPANEL_HOST", "CPANEL_USERNAME", "CPANEL_API_TOKEN", "CPANEL_DOMAIN"]
    config = {k: os.getenv(k) for k in required}
    missing = [k for k, v in config.items() if not v]
    if missing:
        print(f"Error: missing required variables in {ENV_FILE}: {', '.join(missing)}")
        sys.exit(1)

    host = config["CPANEL_HOST"]
    if not host.startswith(("http://", "https://")):
        host = "https://" + host
    parsed = urlparse(host)
    if not parsed.port:
        host = f"{parsed.scheme}://{parsed.hostname}:2083"
    config["CPANEL_HOST"] = host

    return config


def get_public_ip():
    try:
        resp = requests.get(IP_SERVICE, timeout=10)
        resp.raise_for_status()
        return resp.json()["ip"]
    except Exception as e:
        print(f"Error fetching public IP: {e}")
        sys.exit(1)


def read_cached_ip():
    if LAST_IP_FILE.exists():
        return LAST_IP_FILE.read_text().strip()
    return None


def write_cached_ip(ip):
    LAST_IP_FILE.write_text(ip)


def update_ddns(config, ip, dry_run=False):
    host = config["CPANEL_HOST"].rstrip("/")
    headers = {"Authorization": f"cpanel {config['CPANEL_USERNAME']}:{config['CPANEL_API_TOKEN']}"}

    # Step 1: list DDNS entries to find the per-domain update URL
    try:
        resp = requests.get(f"{host}/execute/DynamicDNS/list", headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"Error listing DDNS entries: {e}")
        sys.exit(1)

    if data.get("status") != 1:
        errors = data.get("errors") or data.get("messages") or data
        print(f"cPanel API error: {errors}")
        sys.exit(1)

    entries = data.get("data") or []
    entry = next((e for e in entries if e.get("domain") == config["CPANEL_DOMAIN"]), None)
    if not entry:
        available = [e.get("domain") for e in entries]
        print(f"Error: no Dynamic DNS entry found for '{config['CPANEL_DOMAIN']}'")
        print(f"Available entries: {available}")
        sys.exit(1)

    entry_id = entry["id"]

    # The webcall URL is self-authenticating — no auth headers needed
    webcall_url = f"{host}/cpanelwebcall/{entry_id}"

    if dry_run:
        print(f"[dry-run] Would call: GET {webcall_url}")
        return

    try:
        resp = requests.get(webcall_url, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"Error calling webcall URL: {e}")
        sys.exit(1)

    print(f"Success: {config['CPANEL_DOMAIN']} updated to {ip}")
    write_cached_ip(ip)


def main():
    parser = argparse.ArgumentParser(description="Update cPanel Dynamic DNS with current public IP.")
    parser.add_argument("--force", action="store_true", help="Update even if IP has not changed.")
    parser.add_argument("--dry-run", action="store_true", help="Detect IP but do not call cPanel.")
    args = parser.parse_args()

    config = load_config()
    current_ip = get_public_ip()
    print(f"Current public IP: {current_ip}")

    if not args.force and not args.dry_run:
        cached_ip = read_cached_ip()
        if cached_ip == current_ip:
            print(f"IP unchanged ({current_ip}), skipping update.")
            sys.exit(0)

    update_ddns(config, current_ip, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
