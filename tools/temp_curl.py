import urllib.request
from urllib.error import HTTPError

try:
    with urllib.request.urlopen("http://127.0.0.1:6001/login") as response:
        print(response.read().decode())
except HTTPError as e:
    print(f"Error {e.code}:\n{e.read().decode()}")
except Exception as e:
    print(f"Failed: {e}")
