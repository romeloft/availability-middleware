from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import requests
from bs4 import BeautifulSoup
import aiohttp
import asyncio

app = FastAPI()

# ----------------------
# MODELS
# ----------------------
class AvailabilityRequest(BaseModel):
    region: str
    checkin: str
    checkout: str
    adults: int
    villa_name: Optional[str] = None


# ----------------------
# HEADERS FOR CLOUDFLARE BYPASS
# ----------------------
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml,application/xml",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.sopranovillas.com/",
    "x-api-secret": "supersecretkey123"
}


# ----------------------
# LINK REACHABILITY CHECK
# ----------------------
async def check_link(session, url):
    try:
        async with session.get(url, timeout=10) as response:
            return url, response.status == 200
    except:
        return url, False


async def filter_broken_links(results):
    async with aiohttp.ClientSession() as session:
        tasks = [check_link(session, villa["url"]) for villa in results]
        checks = await asyncio.gather(*tasks)
        return [villa for villa, (url, ok) in zip(results, checks) if ok]


# ----------------------
# SCRAPING FUNCTION
# ----------------------
def scrape_villas(region, checkin, checkout, adults, villa_name=None):
    url = f"https://www.sopranovillas.com/wp-admin/admin-ajax.php?action=so_get_villa_results&region={region}&checkin={checkin}&checkout={checkout}&adults={adults}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 403:
        raise HTTPException(status_code=403, detail="Cloudflare blocked the request. Check headers and rules.")
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=f"Error fetching data from Sopranovillas")

    soup = BeautifulSoup(response.text, "html.parser")
    villas = []

    for villa_div in soup.find_all("div", class_="result-wrapper"):
        name = villa_div.get("data-property-name", "").strip()
        price = villa_div.get("data-price", "").strip()

        i
