from fastapi import FastAPI
from pydantic import BaseModel
import requests

app = FastAPI()

SOPRANO_API_URL = "https://soprano-villas-api-production.up.railway.app/get_price"
API_SECRET = "supersecretkey123"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*;q=0.8",
    "Referer": "https://www.sopranovillas.com/"
}

class CrispPayload(BaseModel):
    region: str = None
    checkin: str = None
    checkout: str = None
    adults: int = None
    villa_name: str = None

@app.get("/")
def home():
    return {"message": "Middleware is running!"}

@app.post("/check_availability")
async def check_availability(payload: CrispPayload):
    try:
        params = {
            "region": payload.region,
            "checkin": payload.checkin,
            "checkout": payload.checkout,
            "adults": payload.adults
        }

        # Call Sopranovillas API
        res = requests.get(SOPRANO_API_URL, params=params, headers={"x-api-secret": API_SECRET, **HEADERS}, timeout=20)
        data = res.json()

        if not data.get("success"):
            return {"text": "⚠️ Error checking availability, please try again."}

        villas = data.get("results", [])
        if not villas:
            return {"text": "❌ No villas available for the requested dates."}

        # If villa_name specified, filter by name
        if payload.villa_name:
            matched_villa = next((v for v in villas if payload.villa_name.lower() in v["name"].lower()), None)
            if matched_villa:
                if check_link_reachability(matched_villa["url"]):
                    return {"text": format_single_villa(matched_villa)}
                else:
                    return {"text": f"⚠️ The villa '{payload.villa_name}' exists but the link is unreachable. Please contact us."}
            else:
                return {"text": f"❌ Villa '{payload.villa_name}' is not available. Here are alternatives:\n" + format_villas_list(villas)}

        # Otherwise, return top 3 available villas
        return {"text": format_villas_list(villas)}

    except Exception as e:
        return {"text": f"⚠️ Error: {str(e)}"}

def check_link_reachability(url: str) -> bool:
    try:
        r = requests.get(url, headers=HEADERS, timeout=8)
        return r.status_code == 200
    except:
        return False

def format_single_villa(villa: dict) -> str:
    return (f"✅ **{villa['name']}** is available!\n"
            f"Price: {villa['price']}\n"
            f"Bedrooms: {villa['bedrooms']} | Bathrooms: {villa['bathrooms']}\n"
            f"[Book Now]({villa['url']})")

def format_villas_list(villas: list) -> str:
    reply = "🏡 **Available Villas:**\n"
    count = 0
    for villa in villas:
        if count >= 3:
            break
        if check_link_reachability(villa["url"]):
            reply += f"- {villa['name']} ({villa['price']}) → {villa['url']}\n"
            count += 1
    if count == 0:
        return "⚠️ No valid villa links are reachable at the moment."
    return reply
