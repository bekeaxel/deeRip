import requests
from bs4 import BeautifulSoup
import re

resp = requests.get("https://soundcloud.com")
soup = BeautifulSoup(resp.text, "html.parser")

for script in soup.find_all("script", src=True):
    if "a-v2" in script["src"] and (src := script["src"]).endswith(".js"):
        js = requests.get(src).text
        match = re.search(r'client_id["=:]\s*"?([a-zA-Z0-9]{32})"?', js)
        if match:
            print(match.group(1))
