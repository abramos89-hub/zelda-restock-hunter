# Zelda Restock Hunter — Android cloud version

This is a conservative **restock alert monitor**, not an auto-purchaser. It checks public product pages only where robots.txt permits, parses Product/Offer JSON-LD, and alerts only when exact product identity, retailer seller, in-stock availability and price are confirmed.

## Settings
- Exact item: Nintendo Switch 2 — The Legend of Zelda — 40th Anniversary Edition
- Maximum item price: USD $519.99 before tax/shipping
- Nintendo and Best Buy enabled with verified product URLs
- Amazon, Target and Walmart disabled until exact listings are confirmed
- GitHub Actions schedule: every 5 minutes (GitHub's minimum scheduled interval)

It intentionally does not bypass CAPTCHAs, queues, access controls or rate limits, and does not add to cart or place orders. Retailer pages may not expose structured data; in that case it fails closed and sends no stock alert.

## Setup from Android

### 1. Create Telegram bot
1. In Telegram, open @BotFather.
2. Send `/newbot`, choose a display name and a username ending in `bot`.
3. Save the token privately. Treat it like a password; never paste it in this chat or source code.
4. Open your new bot's link and press **Start**.

### 2. Get your chat ID
Open @userinfobot in Telegram and press Start. It returns your numeric Telegram user ID; use that for your private chat ID.

### 3. Create GitHub repository
1. Open https://github.com in Chrome and sign in/create a free account.
2. Create a **Public** repository named `zelda-restock-hunter`.
3. Do not add a README or .gitignore during creation.
Public standard GitHub-hosted Actions runners are free. The source code and product links will be public, but secrets must be stored only as GitHub Actions secrets.

### 4. Upload project files
Extract the ZIP on Android with Files by Google or your file manager.
Upload these four files to the repository root: `monitor.py`, `config.json`, `requirements.txt`, `README.md`.
Then create the workflow:
1. Choose **Add file → Create new file**.
2. Name it `.github/workflows/monitor.yml`.
3. Paste the full contents of the included workflow file.
4. Commit to the default branch (`main`).

### 5. Add secrets
Repository **Settings → Secrets and variables → Actions → New repository secret**.
Create:
- `TELEGRAM_BOT_TOKEN` = token from BotFather
- `TELEGRAM_CHAT_ID` = numeric ID from @userinfobot
Never put these in config.json.

### 6. Test
Open **Actions → Zelda Restock Hunter → Run workflow**. Inspect the run logs. Telegram alerts are sent only for a real structured-data match; no fake stock test is generated.

## More retailers
Edit config.json only after you verify the exact console listing and retailer seller. Add the exact URL, allowed seller term and set `enabled` to true. Do not enable a retailer if its terms or robots.txt disallow automated access. If blocked with 401/403/429 or a challenge, disable it and use its official stock alert instead.

## Meaning of an alert
The alert requires structured product data confirming:
- title contains Zelda, 40th Anniversary and Switch 2
- seller matches the retailer
- availability is InStock
- item price is at or below $519.99

Always verify the live page, item, seller, pickup/shipping, taxes and final total. Inventory can change before checkout. No purchase is made.
