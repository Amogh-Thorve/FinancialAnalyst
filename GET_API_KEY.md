# Get Your Free Alpha Vantage API Key

## The Problem

The demo API key (`demo`) has very strict limits:
- **5 requests per minute**
- **25 requests per day**

You've hit the rate limit, which is why META lookup failed.

## The Solution - Get Your FREE API Key (Takes 30 seconds)

### Step 1: Visit Alpha Vantage
Go to: **https://www.alphavantage.co/support/#api-key**

### Step 2: Enter Your Email
- Enter your email address
- Click "GET FREE API KEY"
- You'll receive your key instantly (no email verification needed!)

### Step 3: Update Your .env File
Open `.env` and replace:
```
ALPHA_VANTAGE_API_KEY=demo
```

With:
```
ALPHA_VANTAGE_API_KEY=YOUR_ACTUAL_KEY_HERE
```

### Step 4: Restart Your Agent
Just run `python main.py` again and it will work!

## Free Tier Limits

With your free key, you get:
- ✅ **25 requests per day** (plenty for testing)
- ✅ **5 requests per minute**
- ✅ **Unlimited time** (never expires)
- ✅ **No credit card required**

## Alternative: Use a Different Stock

If you don't want to get an API key right now, try asking about **IBM** instead - the demo key seems to work better with IBM:

```
"What is the current stock price of IBM?"
```

---

**Quick Link:** https://www.alphavantage.co/support/#api-key
