import sys
sys.path.insert(0, '/config/custom_components/techem')

# Copy COUNTRIES directly
COUNTRIES = {
    "dk": {
        "name": "Denmark",
        "url": "https://techemadmin.dk/analytics/graphql",
        "referer": "https://beboer.techemadmin.dk/"
    },
    "no": {
        "name": "Norway", 
        "url": "https://techemadmin.no/analytics/graphql",
        "referer": "https://beboer.techemadmin.no/"
    }
}

import logging 
import requests
import datetime

logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

class TechemAPI:
    def __init__(self, email: str, password: str, object_id: str, country: str):
        self.email = email
        self.password = password
        self.object_id = object_id
        self.country_config = COUNTRIES[country]
        self.url = self.country_config["url"]
        self.referer = self.country_config["referer"]

    def get_token(self) -> str:
        token_body = {
            "query": """
                mutation nucleolusLogin($credentials: CredentialsInput!) {
                    loginWithEmailAndPassword(credentials: $credentials) {
                        ok { token }
                    }
                }
            """,
            "variables": {
                "credentials": {
                    "username": self.email,
                    "password": self.password,
                    "targetResource": "tenant"
                }
            }
        }
        
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/json",
            "Referer": self.referer,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
        }

        try:
            print(f"Attempting login to {self.url}")
            response = requests.post(self.url, headers=headers, json=token_body, timeout=10)
            print(f"Status code: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            
            login_data = data.get("data", {}).get("loginWithEmailAndPassword", {})
            ok_data = login_data.get("ok")
            
            if ok_data:
                return ok_data.get("token", "")
        except Exception as err:
            print(f"Error: {err}")
        
        return ""

# Test
api = TechemAPI(
    'simonbachdall@gmail.com',
    'JoQ2$WtquP!VzVSYD3fc4kRlPs!1Zpqx?LBj#Fps',
    'cF9fMTYwNC51X18xMjc0MzQ',
    'dk'
)

print("\nTesting get_token...")
token = api.get_token()
if token:
    print(f"✓ Token: {token[:20]}...")
else:
    print("✗ Failed to get token")
