"""Techem API client."""
import logging
import requests
import datetime
import json
from .const import COUNTRIES

_LOGGER = logging.getLogger(__name__)

class TechemAPI:
    """Techem API client."""

    def __init__(self, email: str, password: str, object_id: str, country: str):
        """Initialize the API client."""
        self.email = email
        self.password = password
        self.object_id = object_id
        self.country_config = COUNTRIES[country]
        self.url = self.country_config["url"]
        self.referer = self.country_config["referer"]

    def get_token(self) -> str:
        """Get authentication token."""
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
            _LOGGER.debug("Attempting login to %s", self.url)
            response = requests.post(self.url, headers=headers, json=token_body, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            _LOGGER.debug("Response data: %s", data)
            
            login_data = data.get("data", {}).get("loginWithEmailAndPassword", {})
            ok_data = login_data.get("ok")
            
            if ok_data:
                token = ok_data.get("token", "")
                if token:
                    _LOGGER.info("Successfully authenticated")
                    return token
            
            _LOGGER.error("Authentication failed - no token in response")
        except Exception as err:
            _LOGGER.error("Failed to get token: %s", err)
        
        return ""

    def get_data(self, yearly: bool, days_offset: int = 1) -> dict | None:
        """Get consumption data."""
        token = self.get_token()
        if not token:
            _LOGGER.error("Cannot get data without token")
            return None

        today = datetime.datetime.now()
        
        if yearly:
            start = datetime.datetime(today.year, 1, 1)
            end = today - datetime.timedelta(days=days_offset)
            compare = "previous-year"
        else:
            start = today - datetime.timedelta(days=days_offset + 7)
            end = today - datetime.timedelta(days=days_offset)
            compare = "previous-period"

        body = {
            "query": """
                query TenantTable($table: TenantTableInput!) {
                    tenantTable(table: $table) {
                        rows { values comparisonValues }
                    }
                }
            """,
            "variables": {
                "table": {
                    "aggregationLevel": "UNIT",
                    "objectId": self.object_id,
                    "periodBegin": start.strftime("%Y-%m-%dT00:00:00"),
                    "periodEnd": end.strftime("%Y-%m-%dT00:00:00"),
                    "compareWith": compare
                }
            },
            "operationName": "TenantTable"
        }

        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/json",
            "Authorization": f"JWT {token}",
            "Origin": self.referer.rstrip('/'),
            "Referer": self.referer,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
        }

        try:
            response = requests.post(self.url, headers=headers, json=body, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            rows = data.get("data", {}).get("tenantTable", {}).get("rows", [])
            if rows:
                _LOGGER.debug("Successfully retrieved data")
                return rows[0]
        except Exception as err:
            _LOGGER.error("Failed to get data: %s", err)
        
        return None

    def get_kpi_data(self, days_back: int = 30) -> dict | None:
        """Get KPI data including room and meter breakdown."""
        token = self.get_token()
        if not token:
            _LOGGER.error("Cannot get KPI data without token")
            return None

        today = datetime.datetime.now()
        start = today - datetime.timedelta(days=days_back)
        end = today - datetime.timedelta(days=1)  # Yesterday

        body = {
            "query": """
                query UnitQuantityKPIs($input: UnitQuantityKPIsInput!) {
                    unitQuantityKpis(input: $input) {
                        total
                        previousPeriod
                        previousYear
                        propertyComparison
                        rooms {
                            label
                            value
                        }
                        meters {
                            object {
                                id
                                group {
                                    id
                                    quantity
                                    meter {
                                        id
                                        number
                                        roomName
                                    }
                                }
                            }
                            value
                        }
                    }
                }
            """,
            "variables": {
                "input": {
                    "objectId": self.object_id,
                    "quantity": "hca",
                    "periodBegin": start.strftime("%Y-%m-%d"),
                    "periodEnd": end.strftime("%Y-%m-%d")
                }
            },
            "operationName": "UnitQuantityKPIs"
        }

        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/json",
            "Authorization": f"JWT {token}",
            "Origin": self.referer.rstrip('/'),
            "Referer": self.referer,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
        }

        try:
            response = requests.post(self.url, headers=headers, json=body, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            kpi_data = data.get("data", {}).get("unitQuantityKpis")
            if kpi_data:
                _LOGGER.debug("Successfully retrieved KPI data")
                return kpi_data
        except Exception as err:
            _LOGGER.error("Failed to get KPI data: %s", err)
        
        return None