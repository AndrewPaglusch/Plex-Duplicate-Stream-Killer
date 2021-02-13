# Plex Duplicate Stream Killer
Automatically ban users who share their Plex account with others. **This requires an active [PlexPass](https://www.plex.tv/plex-pass/) subscription to work.**

# What It Does
This script will query your Plex server every 10 seconds (default) and get a list of current streams. It will automatically kill all streams for a user if two or more of their streams are coming from different IP addresses. 

# Requirements
- Python 3.X
- Python `requests` module
- Active [PlexPass](https://www.plex.tv/plex-pass/) subscription

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
# Build & Run (Docker)

```bash
git clone https://github.com/AndrewPaglusch/Plex-Duplicate-Stream-Killer.git
cd Plex-Duplicate-Stream-Killer
cp docker-compose.yml.EXAMPLE docker-compose.yml # Change the environment variables as necessary
docker-compose up -d
```

