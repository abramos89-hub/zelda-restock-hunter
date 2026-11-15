import json, os, re, sys, time
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parent
CFG=json.loads((ROOT/"config.json").read_text(encoding="utf-8"))
STATE=ROOT/"state.json"
TOKEN=os.environ.get("TELEGRAM_BOT_TOKEN","")
CHAT=os.environ.get("TELEGRAM_CHAT_ID","")
MAX=float(CFG.get("max_item_price_usd",519.99))
TIMEOUT=int(CFG.get("request_timeout_seconds",20))
UA=CFG.get("user_agent","ZeldaRestockHunter/1.0")
BLOCK=("captcha","verify you are human","unusual traffic","access denied","robot or human","automated requests","temporarily blocked")

def load_state():
    try: return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception: return {}
def save_state(s): STATE.write_text(json.dumps(s,indent=2),encoding="utf-8")
def send(msg):
    r=requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
      json={"chat_id":CHAT,"text":msg},timeout=TIMEOUT)
    r.raise_for_status()
    if not r.json().get("ok"): raise RuntimeError("Telegram API rejected the message")

def robots_ok(url):
    p=urlparse(url); robots=f"{p.scheme}://{p.netloc}/robots.txt"
    try:
        r=requests.get(robots,headers={"User-Agent":UA},timeout=TIMEOUT)
        if r.status_code in (401,403,429) or r.status_code>=500: return False
        if r.status_code==404: return True
        rp=RobotFileParser(); rp.parse(r.text.splitlines())
        return rp.can_fetch(UA,url)
    except requests.RequestException: return False

def walk(x):
    if isinstance(x,dict):
        yield x
        for v in x.values(): yield from walk(v)
    elif isinstance(x,list):
        for v in x: yield from walk(v)

def products(html):
    soup=BeautifulSoup(html,"html.parser"); out=[]
    for tag in soup.find_all("script",attrs={"type":re.compile(r"ld\+json",re.I)}):
        raw=tag.string or tag.get_text()
        try: data=json.loads(raw)
        except Exception: continue
        for n in walk(data):
            typ=n.get("@type",[])
            if isinstance(typ,str): typ=[typ]
            if any(str(t).lower()=="product" for t in typ): out.append(n)
    return out

def offers(x):
    if isinstance(x,list):
        for a in x: yield from offers(a)
    elif isinstance(x,dict):
        if "offers" in x and "price" not in x: yield from offers(x["offers"])
        else: yield x

def inspect(retailer,html):
    low=html.lower()
    if any(x in low for x in BLOCK): return {"status":"CHALLENGE_OR_BLOCK"}
    matches=[]
    for p in products(html):
        name=str(p.get("name","")).lower()
        if "zelda" in name and "40th anniversary" in name and "switch 2" in name:
            matches.append(p)
    if not matches: return {"status":"UNCONFIRMED"}
    for p in matches:
        for o in offers(p.get("offers",{})):
            seller=o.get("seller",{})
            seller=str(seller.get("name","") if isinstance(seller,dict) else seller).lower()
            if not any(t in seller for t in retailer.get("allowed_seller_terms",[])): continue
            raw=o.get("price")
            if raw is None and isinstance(o.get("priceSpecification"),dict):
                raw=o["priceSpecification"].get("price")
            try: price=float(str(raw).replace(",",""))
            except (TypeError,ValueError): continue
            avail=str(o.get("availability","")).lower()
            if price>MAX: return {"status":"OVER_BUDGET","price":price}
            if "instock" in avail or avail.endswith("/instock"):
                return {"status":"MATCH","price":price,"seller":seller}
    return {"status":"NO_VERIFIED_MATCH"}

def check(r):
    url=r.get("url","").strip()
    if not url: return {"status":"NOT_CONFIGURED"}
    if not robots_ok(url): return {"status":"SKIPPED_ROBOTS_OR_POLICY"}
    try:
        resp=requests.get(url,headers={"User-Agent":UA,"Accept":"text/html","Accept-Language":"en-US,en;q=0.9"},timeout=TIMEOUT)
        if resp.status_code in (401,403,429): return {"status":f"BLOCKED_{resp.status_code}"}
        resp.raise_for_status()
        return inspect(r,resp.text)
    except requests.RequestException as e:
        print(f"Request error: {e}")
        return {"status":"REQUEST_ERROR"}

def main():
    if not TOKEN or not CHAT:
        print("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID secrets."); sys.exit(2)
    state=load_state()
    enabled=[r for r in CFG["retailers"] if r.get("enabled")]
    print(f"Checking {len(enabled)} enabled retailers; item price cap ${MAX:.2f}")
    for r in enabled:
        name=r["name"]; result=check(r); status=result["status"]
        print(name, status)
        if status=="MATCH" and state.get(name,{}).get("status")!="MATCH":
            send("🗡️ Zelda Restock Hunter: POSSIBLE MATCH\n"
                 f"Retailer: {name}\nPrice: ${result['price']:.2f}\n"
                 f"Seller: {result['seller']}\nMaximum item price: ${MAX:.2f}\n"
                 f"Open and verify stock, delivery/pickup, seller and final total:\n{r['url']}\n\n"
                 "No order was placed; complete checkout yourself.")
        if status in ("CHALLENGE_OR_BLOCK","BLOCKED_401","BLOCKED_403","BLOCKED_429","SKIPPED_ROBOTS_OR_POLICY"):
            print(f"Disable {name} unless you confirm a permitted access method.")
        state[name]={"status":status,"checked_at":int(time.time())}
    save_state(state)

if __name__=="__main__": main()
