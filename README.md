# Plex Duplicate Stream Killer

Automatically ban users who share their Plex account with others using two detection methods. **This requires an active [PlexPass](https://www.plex.tv/plex-pass/) subscription to work.**

# What It Does

This script will query your Plex server every 30 seconds (configurable) and get a list of current streams. It employs two methods to detect account sharing:

1. Real-time IP address analysis: The script will automatically kill all streams for a user if two (configurable) or more of their streams are coming from different IP addresses.
2. Historical IP address analysis (optional): The script can also track user streaming history and ban a user if they have used more than a set limit of IP addresses over a specified time period.

# Requirements

- Docker
- Docker Compose
- Active [PlexPass](https://www.plex.tv/plex-pass/) subscription

## Examples

### Example 1 - John has three streams:

- **Stream 1:** IP Address 1.2.3.4
- **Stream 2:** IP Address 1.2.3.4
- **Stream 3:** IP Address: 9.8.7.6

The script will see that John's account is being used from two unique locations (two IP addresses) using the real-time IP address analysis. All of John's streams will be killed, and John will be added to the ban list for 48 hours (default). All of John's attempts to stream will be blocked until his ban has expired.

### Example 2 - Mary has two streams:

- **Stream 1:** IP Address 1.2.3.4
- **Stream 2:** IP Address 1.2.3.4

The script will see that Mary's account is being used from only one unique IP address. Unless Mary's already banned or has too many unique IP addresses in her streaming history (if historical IP address analysis is enabled), she'll be allowed to keep streaming.

### Example 3 - Alice has one stream:

- **Stream 1:** IP Address 1.2.3.4

Alice has only one active stream, so she is not flagged by the real-time IP address analysis. However, if history-based banning is enabled and Alice has used more unique IP addresses than allowed within the specified time period, she will be banned.

In this case, let's say Alice has streamed from five different IP addresses in the last 12 hours, exceeding the allowed limit. As a result, Alice will be added to the ban list for 48 hours. All her attempts to stream will be blocked until her ban has expired.

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
      LOOP_DELAY_SECONDS: 30
      MAX_UNIQUE_STREAMS: 2
      USER_HISTORY_BAN_ENABLED: true
      USER_HISTORY_LENGTH_HRS: 12
      USER_HISTORY_BAN_IP_THRESH: 4
      BAN_LENGTH_HRS: 48
      BAN_MSG: YOU HAVE BEEN BANNED FROM PLEX FOR 48 HOURS FOR ACCOUNT SHARING. This is an automated message.
      USER_WHITELIST: joeuser55 bobross123
      NETWORK_WHITELIST: 10.15.16.0/24 192.168.0.0/16
      PLEX_URL: http://my-plex-server:32400
      PLEX_TOKEN: myplextokenhere
      TELEGRAM_BOT_KEY: 123456789:foobarbizbazfoobarbizbaz
      TELEGRAM_CHAT_ID: -123456789
```

# Configuration (Environment Variables)
 **All variables are required**
  - `LOOP_DELAY_SECONDS`: This is the delay in seconds between each check of the Plex server for active streams.
  - `MAX_UNIQUE_STREAMS`: This variable sets the maximum number of unique IP addresses a user is allowed to have for their active streams before being considered for account sharing.
  - `USER_HISTORY_BAN_ENABLED`: This variable is a boolean flag that enables or disables the history-based banning feature. Set to "true" to enable history-based banning, and "false" to disable it. On a busy server, this can potentially consume a large amount of memory, especially if `LOOP_DELAY_SECONDS` is set very low, or `USER_HISTORY_LENGHT_HRS` is set very high.
  - `USER_HISTORY_LENGTH_HRS`: This variable specifies the duration in hours for which the user's streaming history should be considered when evaluating for history-based banning.
  - `USER_HISTORY_BAN_IP_THRESH`: This variable sets the maximum number of unique IP addresses a user is allowed to have in their streaming history within the specified `USER_HISTORY_LENGTH_HRS` before being considered for account sharing.
  - `BAN_LENGTH_HRS`: This variable specifies the duration of the ban in hours. Users will be banned for this amount of time if they are flagged for account sharing.
  - `BAN_MSG`: This is the message displayed to the user when their streams are killed, and they are banned from the Plex server.
  - `USER_WHITELIST`: This is a space-separated list of Plex usernames that are exempt from being checked for account sharing. For example: "joeuser55 bobross123".
  - `NETWORK_WHITELIST`: This is a space-separated list of IP addresses or subnets in CIDR notation that are considered "safe" and exempt from account sharing checks. For example: "10.15.16.0/24 192.168.0.0/16".
  - `PLEX_URL`: This is the URL of your Plex server, including the protocol (http or https) and port number. For example: "http://my-plex-server:32400".
  - `PLEX_TOKEN`: This is your Plex server's authentication token. Replace "myplextokenhere" with your actual token.
  - `TELEGRAM_BOT_KEY`: This variable is the API key for your Telegram bot, so you can receive notifications about banned users via Telegram. Replace "123456789:foobarbizbazfoobarbizbaz" with your actual bot API key.
  - `TELEGRAM_CHAT_ID`: This variable is the unique identifier for the chat where the bot will send notifications. Replace "-123456789" with your actual chat ID.
