import requests
import urllib.parse
from websocket import create_connection

class Misskey:
    def __init__(self, accessToken):
        self.accessToken = accessToken
    
    def rest(self, method: str, options: dict = {}):
        options["i"] = self.accessToken
        return requests.post(urllib.parse.urljoin("https://api.misskey.xyz", method), json=options)
    
    def stream(self, method: str, options: dict = {}):
        options["i"] = self.accessToken
        method = method + "?" + urllib.parse.urlencode(options)
        return create_connection(urllib.parse.urljoin("wss://api.misskey.xyz", method))