import sys
import requests
import datetime
import json

def get_date_as_string(n: int) -> str:
    today = datetime.datetime.now()
    date = today - datetime.timedelta(days=n)
    return f"{date.year}-{date.month:02d}-{date.day:02d}"

def get_first_date_as_string() -> str:
    first_day = datetime.datetime(datetime.datetime.now().year, 1, 1)
    return f"{first_day.year}-{first_day.month:02d}-{first_day.day:02d}"

def get_token(techem_email: str, techem_password: str) -> str:
    url = "https://techemadmin.dk/analytics/graphql"

    token_body = {
        "query": """
            mutation nucleolusLogin($credentials: CredentialsInput!) {
                loginWithEmailAndPassword(credentials: $credentials) {
                    ok {
                        token
                    }
                }
            }
        """,
        "variables": {
            "credentials": {
                "username": techem_email,
                "password": techem_password,
                "targetResource": "tenant"
            }
        }
    }
    
    token_headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://beboer.techemadmin.dk/",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
    }

    try:
        response = requests.post(
            url,
            headers=token_headers,
            json=token_body,
            timeout=10.0
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Safer access with error checking
        if "data" not in data:
            return ""
        
        login_data = data.get("data", {}).get("loginWithEmailAndPassword", {})
        ok_data = login_data.get("ok")
        
        if ok_data is None:
            return ""
        
        token = ok_data.get("token", "")
        return token
    
    except (requests.exceptions.RequestException, KeyError, ValueError):
        return ""

def get_data(techem_email: str, techem_password: str, object_id: str, yearly: bool, days_offset: int) -> str:
    token = get_token(techem_email, techem_password)

    if not token:
        return ""

    if yearly:
        start_time = get_first_date_as_string()
        end_time = get_date_as_string(days_offset)
        compare_period = "previous-year"
    else:
        start_time = get_date_as_string(days_offset + 7)
        end_time = get_date_as_string(days_offset)
        compare_period = "previous-period"

    url = "https://techemadmin.dk/analytics/graphql"

    body = {
        "query": """
            query TenantTable($table: TenantTableInput!) {
                tenantTable(table: $table) {
                    rows {
                        values
                        comparisonValues
                    }
                }
            }
        """,
        "variables": {
            "table": {
                "aggregationLevel": "UNIT",
                "objectId": object_id,
                "periodBegin": f"{start_time}T00:00:00",
                "periodEnd": f"{end_time}T00:00:00",
                "compareWith": compare_period
            }
        },
        "operationName": "TenantTable"
    }

    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Origin": "https://beboer.techemadmin.dk",
        "Referer": "https://beboer.techemadmin.dk/",
        "Authorization": f"JWT {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=body,
            timeout=10.0
        )
        response.raise_for_status()

        data = response.json()
        
        # Safer access with error checking
        if "data" not in data:
            return ""
        
        tenant_table = data.get("data", {}).get("tenantTable", {})
        rows = tenant_table.get("rows", [])
        
        if not rows or len(rows) == 0:
            return ""
        
        return json.dumps(rows[0])
    
    except (requests.exceptions.RequestException, KeyError, ValueError, IndexError):
        return ""

def main() -> None:
    if len(sys.argv) < 5:
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    object_id = sys.argv[3]
    yearly = sys.argv[4] == "True"

    offset = 1

    result = get_data(email, password, object_id, yearly, offset)

    if result:
        print(result)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()