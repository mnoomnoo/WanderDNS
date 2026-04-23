# WanderDNS

Keep your cPanel Dynamic DNS record in sync with your current public IP.

## How it works

WanderDNS fetches your current public IP from [ipify](https://www.ipify.org/) and compares it against the last known value. If the IP has changed (or `--force` is used), it calls the cPanel DynamicDNS API to update the record. Unchanged IPs are skipped, making it safe to run frequently via cron.

## Prerequisites

- Python 3.6+
- A cPanel account with Dynamic DNS enabled and an API token

## Installation

```bash
git clone https://github.com/obochsler/WanderDNS.git
cd WanderDNS
pip install requests python-dotenv
cp .env.example .env
# Edit .env with your credentials
```

## Configuration

All configuration is via a `.env` file in the project directory:

| Variable | Description | Example |
|---|---|---|
| `CPANEL_HOST` | Full URL to your cPanel server (including port) | `https://cpanel.example.com:2083` |
| `CPANEL_USERNAME` | Your cPanel username | `yourusername` |
| `CPANEL_API_TOKEN` | API token generated in cPanel | `ABC123...` |
| `CPANEL_DOMAIN` | The subdomain to keep updated | `home.yourdomain.com` |

To generate an API token: cPanel → **Security** → **Manage API Tokens**.

## Usage

```bash
# Normal run — skips update if IP is unchanged
./update_ddns.py

# Force update even if IP has not changed
./update_ddns.py --force

# Detect IP and show what would happen without calling cPanel
./update_ddns.py --dry-run

# Show help
./update_ddns.py --help
```

## Automation

Add a crontab entry to run every 5 minutes:

```bash
crontab -e
```

```
*/5 * * * * cd /path/to/WanderDNS && /usr/bin/python3 update_ddns.py >> /var/log/wanderdns.log 2>&1
```

## License

MIT — see [LICENSE](LICENSE).
