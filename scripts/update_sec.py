#!/usr/bin/env python3
"""Fetch SEC-only companyfacts for the tracked issuers, with fair-access User-Agent.

The collector has a strict allowlist of SEC hosts. It never fetches market
quotes, options chains, editorial content, or external vendor financial data.
Usage: SEC_CONTACT_EMAIL=you@example.com python scripts/update_sec.py
"""
from __future__ import annotations
import datetime as dt
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "companies.json"
TICKERS_FILE = ROOT / "config" / "tickers.json"
ALLOWED_HOSTS = {"www.sec.gov", "data.sec.gov"}
FINANCIAL_TAGS = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax"],
    "net_income": ["NetIncomeLoss"],
    "diluted_eps": ["EarningsPerShareDiluted"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    "equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue"],
    "assets": ["Assets"],
    "liabilities": ["Liabilities"],
    "long_term_debt": ["LongTermDebtCurrent", "LongTermDebtNoncurrent", "LongTermDebt"],
    "dividends_paid": ["PaymentsOfDividendsCommonStock", "PaymentsOfDividends"],
    "repurchases": ["PaymentsForRepurchaseOfCommonStock"],
    "dividend_per_share": ["CommonStockDividendsPerShareDeclared"],
}

def get_json(url: str, agent: str):
    u = urlparse(url)
    if u.scheme != "https" or u.hostname not in ALLOWED_HOSTS:
        raise ValueError("Only SEC HTTPS hosts are allowed")
    req = Request(url, headers={"User-Agent": agent, "Accept-Encoding": "identity", "Accept": "application/json"})
    for attempt in range(3):
        try:
            with urlopen(req, timeout=35) as r:
                return json.load(r)
        except (HTTPError, URLError, TimeoutError) as e:
            if attempt == 2:
                raise RuntimeError(f"SEC request failed for {u.hostname}: {e}") from e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError("unreachable")

def iso_day(s):
    try:
        return dt.date.fromisoformat(str(s))
    except (ValueError, TypeError):
        return None

def annual(rec):
    if rec.get("form") not in {"10-K", "10-K/A", "20-F", "40-F"}:
        return False
    start, end = iso_day(rec.get("start")), iso_day(rec.get("end"))
    return bool(start and end and 330 <= (end - start).days <= 385 and end <= dt.date.today())

def latest_metric(facts, tags, unit="USD", annual_only=True):
    candidates=[]
    for priority,tag in enumerate(tags):
        units = facts.get("us-gaap", {}).get(tag, {}).get("units", {}).get(unit, [])
        for x in units:
            if not isinstance(x.get("val"), (int,float)):
                continue
            if annual_only and not annual(x):
                continue
            if not annual_only and not (x.get("form") in {"10-K","10-K/A","10-Q","10-Q/A","20-F","40-F"}
                                        and iso_day(x.get("end")) and iso_day(x.get("end")) <= dt.date.today()):
                continue
            candidates.append((x.get("end", ""), x.get("filed", ""), -priority, tag, x))
    if not candidates:
        return None
    # Prefer the most recent fiscal end, with latest filed amendment,
    # then the preferred concept if the reporting dates match.
    candidates.sort(key=lambda r:(r[0],r[1],r[2]))
    _,_,_,tag,x=candidates[-1]
    result={"value":x["val"],"period_start":x.get("start"),"period_end":x["end"],
            "filed":x.get("filed"),"taxonomy":"us-gaap","concept":tag}
    if annual_only:
        # Use one earlier same-concept annual fiscal period. Do not combine quarters.
        earlier=[r for _,_,_,tag2,r in candidates if tag2==tag
                 and r.get("end") and 300 <= (iso_day(x["end"])-iso_day(r["end"])).days <= 430]
        if earlier:
            earlier.sort(key=lambda r:(r["end"],r.get("filed","")))
            previous=earlier[-1]
            result["prior_annual_value"]=previous["val"]
            result["prior_annual_period_end"]=previous["end"]
    return result

def extract_shares(facts):
    # Prefer DEI entity-wide disclosure; avoid mixing class-specific counts.
    dei = facts.get("dei", {}).get("EntityCommonStockSharesOutstanding", {}).get("units", {}).get("shares", [])
    if not dei:
        return []
    by_date = {}
    for x in dei:
        d=iso_day(x.get("end"))
        if not d or d>dt.date.today() or not isinstance(x.get("val"), (int,float)) or x["val"] <= 0:
            continue
        if x.get("form") not in {"10-K","10-Q","10-K/A","10-Q/A","20-F","40-F"}:
            continue
        entry={"date": x["end"], "shares":x["val"], "form":x.get("form"),"filed":x.get("filed"),
               "concept":"dei:EntityCommonStockSharesOutstanding"}
        old=by_date.get(x["end"])
        if not old or (entry["filed"] or "") > (old["filed"] or ""):
            by_date[x["end"]]=entry
    return [by_date[d] for d in sorted(by_date)[-12:]]

def collect(ticker, cik, name, agent):
    url=f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
    doc=get_json(url,agent)
    facts=doc.get("facts",{})
    metrics={}
    for key,tags in FINANCIAL_TAGS.items():
        # Banking revenue needs bank-specific concepts; a general GAAP revenue tag
        # can represent only a small part of a bank's operating revenue.
        if ticker in {"SOFI"} and key=="revenue":
            continue
        value=latest_metric(facts,tags, unit="USD/shares" if key in {"diluted_eps","dividend_per_share"} else "USD",annual_only=key not in {"equity","cash","assets","liabilities","long_term_debt"})
        if value:
            value["source_url"]=url
            metrics[key]=value
    shares=extract_shares(facts)
    for x in shares:
        x["source_url"]=url
    return {"ticker":ticker,"name":doc.get("entityName") or name,"cik":str(cik).zfill(10),
            "metrics":metrics,"shares_history":shares,"source":"SEC EDGAR XBRL companyfacts", "source_url":url,
            "checked_at":dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()}

def run():
    email=os.environ.get("SEC_CONTACT_EMAIL", "").strip()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",email):
        raise SystemExit("SEC_CONTACT_EMAIL must be a real contact email. Set the GitHub Actions repository variable or environment variable.")
    agent=f"StocksPublishable/1.0 research {email}"
    tickers=json.loads(TICKERS_FILE.read_text())
    if not isinstance(tickers,list) or len(tickers)>150 or not all(isinstance(t,str) and re.fullmatch(r"[A-Z0-9.\-]{1,12}",t) for t in tickers):
        raise SystemExit("config/tickers.json must be a list of up to 150 supported ticker symbols")
    old={}
    if DATA_FILE.exists():
        previous=json.loads(DATA_FILE.read_text())
        old={x["ticker"]:x for x in previous.get("companies",[]) if x.get("ticker")}
    lookup=get_json("https://www.sec.gov/files/company_tickers.json",agent)
    by_ticker={v["ticker"].upper():(v["cik_str"],v.get("title",v["ticker"])) for v in lookup.values()}
    records=[]; failures=[]; refreshed=0
    for ticker in dict.fromkeys(tickers):
        if ticker not in by_ticker:
            failures.append(f"{ticker}: no SEC CIK mapping")
            if ticker in old: records.append(old[ticker])
            continue
        cik,name=by_ticker[ticker]
        try:
            time.sleep(.45)
            records.append(collect(ticker,int(cik),name,agent))
            refreshed+=1
            print(f"{ticker}: SEC fundamentals retrieved")
        except Exception as e:
            failures.append(f"{ticker}: {e}")
            if ticker in old: records.append(old[ticker])
    if not refreshed:
        raise SystemExit("No SEC records were retrieved; preserving previous data. " + "; ".join(failures))
    obj={"updated_at":dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
         "source":"SEC EDGAR XBRL companyfacts (free public disclosures)",
         "notes":"Historical SEC issuer filings, not exchange quotes. Source licensing must be reviewed separately from site hosting.",
         "requested_count":len(list(dict.fromkeys(tickers))),
         "refreshed_count":refreshed,
         "failed_count":len(failures),
         "companies":records}
    DATA_FILE.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n")
    print(f"Wrote {len(records)} issuers; warnings: {len(failures)}")
    for msg in failures:print("WARNING:",msg)

if __name__=="__main__":
    run()