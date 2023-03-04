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

# Docker Compose Example

**docker-compose.yml**
```yaml
version: "3.8"
services:
  dupstreamkiller:
     image: ghcr.io/andrewpaglusch/plex-duplicate-stream-killer:v2
     container_name: dupstreamkiller
     restart: always
     volumes:
       - ./plex-duplicate-stream-killer/data:/data
     environment:
       LOOP_DELAY_SECONDS: 10
       MAX_UNIQUE_STREAMS: 1
       BAN_LENGTH_HRS: 48
       BAN_MSG: YOU HAVE BEEN BANNED FROM PLEX FOR 48 HOURS FOR ACCOUNT SHARING. This is an automated message.
       USER_WHITELIST: joeuser55 bobross123
       NETWORK_WHITELIST: 10.15.16.0/24 192.168.0.0/16
       PLEX_URL: http://my-plex-server:32400
       PLEX_TOKEN: myplextokenhere
       TELEGRAM_BOT_KEY: 123456789:foobarbizbazfoobarbizbaz
       TELEGRAM_CHAT_ID: -123456789
```

