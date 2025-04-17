# deeRip

deeRip is a personal music exporter for Spotify and Deezer, built with Python and Textual (shoutout!). It runs entirely in your terminal. Run the commands below to get started.


## System Requirements
- Python 3.12

## Install

```
pip install -r requirements.txt
```

## Running 
```
textual run run.py
```
## Credentials
deeRip requires access tokens for Spotify and Deezer to interact with their APIs. You must supply your own credentials.

### Spotify
Create a developer app at Spotify Developer Dashboard.
- Add http://localhost:8888/callback/ under Redirect URIs
- Select Web API under API/SDKs

Once created, you’ll find your client ID and secret—enter them in deeRip’s settings tab.

### Deezer
deeRip uses your personal Deezer session to access your library and metadata.
- Log in at deezer.com
- Open developer tools (Right-click → Inspect)
- Go to the Application tab
- Under Cookies for https://www.deezer.com, find the arl token


⚠️ This tool is intended for personal use only.
It does not bypass DRM or access paid content without authorization.
Please respect the terms of service of each platform.


Special thanks to open-source projects in the music ecosystem for their inspiration.

