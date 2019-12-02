# Plex Duplicate Stream Killer
Automatically ban users who share their Plex account with others.

# What It Does
This script will query your Plex server every 10 seconds (default) and get a list of current streams. It will automatically kill all streams for a user if two or more of their streams are coming different IP addresses. 

# Requirements
- Python 3.X
- Python `requests` module

## Examples

### Example 1 - John has three streams:

 - **Stream 1:** IP Address 1.2.3.4
 - **Stream 2:** IP Address 1.2.3.4
 - **Stream 3:** IP Address: 9.8.7.6
 
 The script will see that John's account is being used from two unique locations (two IP addresses). All of John's streams will be killed and John will be added to the ban list for 48 hours (default). All of John's attempts to stream will be blocked until his ban has expired.
 
 ### Example 2 - Mary has two streams:
 
  - **Stream 1:** IP Address 1.2.3.4
  - **Stream 2:** IP Address 1.2.3.4
  
  The script will see that Mary's account is being used from only one unique IP address. Unless Mary's already banned, she'll be allowed to keep streaming.
  
# Install & Run (Systemd)

```bash
mkdir /opt/dup-stream-killer
cd !$
git clone https://github.com/AndrewPaglusch/Plex-Duplicate-Stream-Killer .
mv config.ini.example config.ini
vim config.ini # edit config file

cat > /etc/systemd/system/dup-stream-killer.service << EOF
[Unit]
Description=Plex Duplicate Stream Killer
After=network.target

[Service]
WorkingDirectory=/opt/dup-stream-killer
Type=simple
ExecStart=/usr/bin/python3 -u /opt/dup-stream-killer/dupStreamKiller.py
Restart=always
RestartSec=15

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable dup-stream-killer --now
journalctl -u dup-stream-killer -f
```

