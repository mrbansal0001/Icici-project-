import requests

url = "https://saras.cbse.gov.in/saras/AffiliatedList/ListOfSchdirReport"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
try:
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {response.status_code}")
    print(response.text[:200])
except Exception as e:
    print(e)
