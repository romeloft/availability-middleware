from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import Optional
import requests
from bs4 import BeautifulSoup
import aiohttp
import asyncio

app = FastAPI()

class AvailabilityRequest(BaseModel):
    region: str
    checkin: str
    checkout: str
    adults: int
    villa_name: Optional[str] = None

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml,application/xml",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.sopranovillas.com/"
}

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

def scrape_villas(region, checkin, checkout, adults, villa_name=None):
    url = f"https://www.sopranovillas.com/wp-admin/admin-ajax.php?action=so_get_villa_results&region={region}&checkin={checkin}&checkout={checkout}&adults={adults}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Error fetching Sopranovillas data")

    soup = BeautifulSoup(response.text, "html.parser")
    villas = []
    for villa_div in soup.find_all("div", class_="result-wrapper"):
        name = villa_div.get("data-property-name", "").strip()
        price = villa_div.get("data-price", "").strip()
        if villa_name and villa_name.lower() not in name.lower():
            continue

        link_tag = villa_div.find("a", href=True)
        url = link_tag["href"] if link_tag else ""
        url = url.replace("\\", "").replace("\"", "")

        villas.append({
            "name": name,
            "price": price,
            "url": url
        })

    return villas

@app.get("/")
def home():
    return {"status": "Middleware running"}

@app.post("/check_availability")
async def check_availability(request: AvailabilityRequest, x_api_secret: str = Header(None)):
    if x_api_secret != "supersecretkey123":
        raise HTTPException(status_code=401, detail="Unauthorized")
    villas = scrape_villas(request.region, request.checkin, request.checkout, request.adults, request.villa_name)
    villas = await filter_broken_links(villas)
    return {"success": True, "count": len(villas), "results": villas}

@app.get("/check_availability")
async def check_availability_get(region: str, checkin: str, checkout: str, adults: int, villa_name: Optional[str] = None):
    villas = scrape_villas(region, checkin, checkout, adults, villa_name)
    villas = await filter_broken_links(villas)
    return {"success": True, "count": len(villas), "results": villas}
