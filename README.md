# Stocks Publishable — SEC-first research site

A separate, commercialization-conscious financial research website. Built with SEC EDGAR public data and original software, without Yahoo Finance, Stooq, Nasdaq, Alpaca, or third-party market-quote feeds.

## Included features
- SEC Company Explorer: shares outstanding, historical changes, annual financial metrics with dates and source links.
- Original Options Calculator: cash-secured puts, covered calls, purchased calls, purchased puts; quotes entered manually.
- Data-source transparency and licensing caveats.
- GitHub Actions SEC collector with a contact-email requirement; no API secrets in the browser.

## Setup
1. In GitHub repository **Settings → Secrets and variables → Actions → Variables**, create `SEC_CONTACT_EMAIL` with a real contact email for SEC fair access.
2. Run **Actions → Refresh public SEC filings → Run workflow**.
3. For a commercial site, consider Netlify or another host that allows commercial usage. Do not assume GitHub Pages is suitable for commercial SaaS.
4. Manage tracked issuers in `config/tickers.json`, then refresh the SEC data.

## Usage and important limitations
The app uses SEC public-filing data and original calculations. SEC filings may include third-party copyrighted material; avoid republishing such material. EDGAR has fair-access requirements. Verify each reported metric and fiscal period against its source. No real-time prices, options chains, P/E from vendor quotes, bid/ask, or unlicensed market information are included. The options analyzer is for **manually entered numbers**, not brokerage or investment advice.

Commercial plans still require review of hosting, legal requirements, and any future provider data contracts.

SEC sources: https://www.sec.gov/about/developer-resources and https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data.
