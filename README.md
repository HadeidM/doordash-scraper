# DoorDash Scraper

A tool for automatically downloading and analyzing your full DoorDash order history. It includes a Python-based scraper to export your DoorDash orders (including items, stores, dates, and customizations) to CSV files, and ships with an interactive, visually-rich dashboard (HTML/JS) for data exploration and insight discovery. The project is designed for privacy (runs locally), convenience, and actionable insights about your takeout habits.


## Features

✨ **Scrapes complete order history** from DoorDash (items, stores, dates, customizations)  
📊 **Interactive dashboard** with charts and visualizations  
🔒 **Security hardened** with XSS prevention and null-safe code  
💾 **Smart caching** to resume interrupted scrapes  
🎨 **Beautiful UI** for exploring your order data

## Requirements

```bash
pip3 install requests
```

## Instructions

### 1. Obtain Your DoorDash Cookies

**Important:** Due to Cloudflare protection, you need to provide your full cookie string (not just sessionid).

1. Sign in to your account at https://www.doordash.com/consumer/login/
2. Open Chrome DevTools (F12 or Cmd+Option+I on Mac)
3. Go to the **Network** tab
4. Navigate to https://www.doordash.com/orders/
5. Look for a request to `graphql` (with `getConsumerOrdersWithDetails`)
6. Click on it, scroll to **Request Headers**, and find the `cookie:` header
7. Copy the **entire cookie string** (it will be very long)

**Example cookie string format:**
```
cf_clearance=xxxxx; dd_device_id=xxxxx; sessionid=xxxxx; ...
```

### 2. Run the Scraper

Run the scraper with your full cookie string. It will output two CSV files containing all your DoorDash orders.

```bash
python3 doordash_scraper.py "YOUR_FULL_COOKIE_STRING_HERE"
```

**With verbose logging:**
```bash
python3 doordash_scraper.py "YOUR_FULL_COOKIE_STRING_HERE" -v
```

**Example output:**
```bash
Fetching all order summaries in batches of 20
Fetched orders from offset 0
Fetched orders from offset 20
...
Got an empty batch, so we're done fetching order summaries!
Writing normal CSV doordash.csv
Writing pivoted CSV doordash-pivot.csv
```

> **Note:** The script generates JSON cache files (`doordash-orders-*.json`) for each API response. These allow resuming if something goes wrong. To do a fresh scrape, delete these cache files first.

### 3. View the Dashboard (Optional)

After scraping, you can visualize your order history with the interactive dashboard:

```bash
# Start a local web server
python3 -m http.server 8000

# Open in your browser
open http://localhost:8000/dashboard.html
```

The dashboard includes:
- 📊 **Stats cards**: Total orders, favorite store, date range
- 📈 **Orders over time**: Line chart showing ordering patterns  
- 🏆 **Top stores**: Bar chart of your most-visited restaurants
- 🍕 **Most ordered items**: What you order most frequently
- 🔍 **Search & filter**: Find specific orders instantly

## Output Format

### doordash.csv

Complete order history with one row per item ordered:

| Date | Store | Person | Item | Options |
| ---- | ----- | ------ | ---- | ------- | 
| 2025-11-05 | Panda Express | John Doe | Bigger Plate | Step 1: Super Greens, Step 1: Chow Mein, Step 2: Grilled Teriyaki Chicken |
| 2025-11-04 | Bonchon Korean Fried Chicken | Foo Bar | Wings | Wing Count: 8 PC Wings |
| 2025-11-03 | Nando's PERi-PERi | Perry Platypus | Two 1/4 Chicken Legs | PERi-ometer: Hot, Sides?: One Side |
