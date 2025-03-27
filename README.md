# deeRip

Deerip is a converter/downloader for Spotify and Deezer. It was built using python and Textual (shoutout) and runs straight in your terminal! Run the commands below to get started. 


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
deeRip uses Spotify and Deezer api meaning that you need to supply your own api keys. 

### Spotify
For Spotify this is done by creating an app via https://developer.spotify.com/dashboard. 
Make sure to enter http://localhost:8888/callback/ under **Redirect URIs** and to select **Web API** under **Which API/SDKs are you planning to use?**

After creating the app you can find the public and private keys which you will need to enter in the deeRip settings tab.

### Deezer
Deezer uses an ARL which you can find by logging in to deezer website. 
- Open developer tools by right-clicking and pressing inspect
- Go to Application
- Under Cookies/https://www.deezer.com look for arl

Now you are all set! Happy listening!



Huge thanks to deemix for all the inspiration.

