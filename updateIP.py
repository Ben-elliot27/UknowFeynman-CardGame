import requests
import socket

# GoDaddy API credentials
API_KEY = "h1UeTTxoUDCK_AyDnvkBnVi8mefoYtcnzqC"
API_SECRET = "Ka1vqr7Ay7F39ZRgRtYtKg"

# Your domain and DNS record details
DOMAIN = "www.uknowfeynman.co.uk"
RECORD_TYPE = "A"  # Usually an 'A' record
RECORD_NAME = "@"  # Use '@' for root or specify a subdomain like 'www'

# GoDaddy API URL
API_URL = f"https://api.godaddy.com/v1/domains/{DOMAIN}/records/{RECORD_TYPE}/{RECORD_NAME}"

def get_public_ip():
    """Get the current public IP address."""
    return requests.get('https://api.ipify.org').text

def update_dns_record(ip):
    """Update the GoDaddy DNS record with the new IP."""
    headers = {
        "Authorization": f"sso-key {API_KEY}:{API_SECRET}",
        "Content-Type": "application/json",
    }
    data = [{"data": ip}]
    response = requests.put(API_URL, json=data, headers=headers)

    if response.status_code == 200:
        print(f"DNS record updated successfully: {ip}")
    else:
        print(f"Failed to update DNS record: {response.status_code}, {response.text}")

def main():
    try:
        current_ip = get_public_ip()
        print(f"Current public IP: {current_ip}")
        update_dns_record(current_ip)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()

"""
crontab -e
*/10 * * * * /usr/bin/python3 /path/to/script.py
"""