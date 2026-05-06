"""
Quick diagnostic: test fetch_job_details on a known Lever URL.
Run: python3 test_fetch.py
"""
import os, requests
from dotenv import load_dotenv

load_dotenv()

KEY = os.getenv("TINYFISH_API_KEY")
TEST_URL = "https://jobs.lever.co/teramind/7ef9a4f0-ed78-42bf-afca-61266c7b1043"

print(f"API Key loaded: {'YES' if KEY else 'NO'}")
print(f"Testing fetch for: {TEST_URL}\n")

response = requests.post(
    "https://api.fetch.tinyfish.ai",
    headers={"X-API-Key": KEY, "Content-Type": "application/json"},
    json={"urls": [TEST_URL]},
    timeout=20,
)

print(f"Status code: {response.status_code}")
print(f"Response headers: {dict(response.headers)}\n")

try:
    data = response.json()
    print(f"Response type: {type(data)}")
    if isinstance(data, list):
        print(f"List length: {len(data)}")
        if data:
            print(f"First item keys: {list(data[0].keys()) if isinstance(data[0], dict) else type(data[0])}")
            for k, v in (data[0].items() if isinstance(data[0], dict) else []):
                val_preview = str(v)[:200] if v else "(empty)"
                print(f"  {k!r}: {val_preview}")
    else:
        print(f"Response: {str(data)[:500]}")
except Exception as e:
    print(f"JSON parse failed: {e}")
    print(f"Raw body: {response.text[:500]}")
