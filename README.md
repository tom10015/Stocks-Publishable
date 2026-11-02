# Stocks Publishable — SEC-first research site

A separate, self-contained, **commercialization-conscious** static financial research website. Designed to be hosted on a commercial-friendly host while keeping the code on GitHub. No third-party JS, analytics, fonts, options market-data feeds, scraping, or licensed exchange quotes.

## What's included

- **SEC Company Explorer** — shares outstanding, share-count changes, dated filing history, revenue, net income, diluted EPS, operating cash flow, estimated free cash flow and net margin. All sourced from SEC XBRL disclosures; absent metrics are marked as unavailable.
- **Original Options Calculator** — cash-secured puts, covered calls, purchased calls and purchased puts. All inputs are entered by the user. No quotes or contract data are fetched or redistributed.
- **Data-source inventory** — explicit source and use disclosures.
- **SEC collector** — Python standard library only, expanded watchlist (up to 150 tickers), rate limiting, restricted outbound URLs and twice-weekly GitHub Actions workflow. Requires a real contact email.

## First use / deployment

1. Create a **new, empty GitHub repository** named `Stocks-Publishable` (not a fork of ShareWatch).
2. Unzip these files, preserving the `assets`, `data`, `scripts`, `config` and `.github/workflows` directories. Upload/commit them to the repo's default branch. Don't upload the ZIP as a single file.
3. In your new repo, open **Settings → Secrets and variables → Actions → Variables → New repository variable** and create `SEC_CONTACT_EMAIL` with **your real contact email**. SEC fair access calls for identifying automated requests.
4. Open **Actions → Refresh public SEC filings → Run workflow**. The scheduled workflow will then check the selected issuers twice a week (Monday and Thursday). This avoids unnecessary hosting deployments, since SEC filings are periodic. Source data updates are stored in `data/companies.json`.
5. For a website that might earn revenue, open [Netlify](https://app.netlify.com/) and choose **Add new project → Import an existing project → GitHub → Stocks-Publishable**. The repository includes a `netlify.toml`; no build framework is needed. Netlify's free tier has usage limits and terms that you should review before commercial launch.
6. To add or remove tickers, edit `config/tickers.json` (up to 150); rerun the SEC workflow. The starting data includes 35 SEC issuers. The configured watchlist contains 76, and additional entries populate only after successful SEC collection. The collector runs automatically when the watchlist or collection script changes, in addition to its scheduled and manual runs. The script only collects supported SEC issuers and will skip or preserve older available data for unsupported or temporarily failing issuers.

**GitHub Pages caution:** GitHub Pages is primarily project/showcase hosting and GitHub prohibits running a commercial SaaS business on it. Keep code on GitHub, but deploy a paid/ad-supported product to a hosting provider that expressly permits your intended business model.

## Local preview

Run `python -m http.server 8000` in this folder, then open `http://localhost:8000`. Opening `index.html` directly from the filesystem may block `fetch()` of JSON in some browsers.

## Licensing and accuracy

- SEC government-created content and public EDGAR filing content are generally reusable, with exceptions for third-party material. Reference: [SEC webmaster FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions).
- The collector only contacts `https://www.sec.gov` and `https://data.sec.gov`, follows fair-access limits, and identifies itself through `SEC_CONTACT_EMAIL`. Reference: [SEC fair access](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data).
- Financial facts may refer to different fiscal periods, issuer-specific tags, or different classes of outstanding shares. `revenue` especially should not be considered universal across banks, insurers and other specialized issuers. All source dates and links are shown. Verify them before making decisions.
- This **does not guarantee** commercial use of any future additions, embedded third-party materials, branding, hosting, or third-party issuer content. Review those rights before release. Consider legal review before selling a financial product.
- No current stock prices, P/E/P/S, bid/ask spreads, implied volatility, market cap, option-chain data, or live market prices are provided. Those require appropriately licensed sources. **The options page is not a live options feed**.
- SEC, the issuers and brokerage firms do not endorse this app. Not investment advice.

## Project license

The new project uses an all-rights-reserved notice for its original site design and project code (see `LICENSE`), rather than automatically granting competitors permission to resell a clone. This notice does not override the public nature of SEC government data, or third-party and hosting terms.

**Hosting credits:** Netlify’s current Free plan provides 300 monthly credits, and production deploys can use 15 credits each. Two updates per week typically mean about 8–10 monthly deployment events (plus any manual deploys and other usage). Monitor the limit in Netlify; the site may pause if exhausted.
## Why the explorer might have fewer companies than the configuration
The website displays only companies already saved in `data/companies.json`, not a guessed set of tickers. The starter snapshot is 35 SEC issuers, and `config/tickers.json` has 76 configured names. To populate the remaining names, configure the `SEC_CONTACT_EMAIL` Actions variable and run **Actions → Refresh public SEC filings → Run workflow**. Issuers without appropriate SEC XBRL disclosures may have fewer metrics, including no reported share-count history.
