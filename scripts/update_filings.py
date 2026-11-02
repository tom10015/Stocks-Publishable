#!/usr/bin/env python3
"""Collect dated company submissions from SEC EDGAR; not a live alert service.
Only https://data.sec.gov/submissions and official SEC archive links are used.
"""
import datetime as dt
import json, os, re, time
from pathlib import Path
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"/"companies.json"
OUT=ROOT/"data"/"filings.json"
KEEP_FORMS={"8-K","8-K/A","10-Q","10-Q/A","10-K","10-K/A","20-F","20-F/A","6-K","6-K/A","13D","13D/A","13G","13G/A"}

def get_json(url,agent):
    if not url.startswith("https://data.sec.gov/submissions/CIK"):raise ValueError("Unexpected SEC URL")
    req=Request(url,headers={"User-Agent":agent,"Accept":"application/json"})
    for retry in range(3):
        try:
            with urlopen(req,timeout=30) as rsp:return json.load(rsp)
        except Exception:
            if retry==2:raise
            time.sleep(3*(retry+1))

def main():
    email=os.environ.get("SEC_CONTACT_EMAIL","").strip()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",email):
        raise SystemExit("Set a real SEC_CONTACT_EMAIL GitHub Actions variable before collecting SEC submissions")
    agent="StocksPublishable researcher "+email
    companies=json.loads(DATA.read_text()).get("companies",[])
    old=json.loads(OUT.read_text()) if OUT.exists() else {}
    cache=old.get("tickers",{})
    failures=[];success=0
    for c in companies:
        ticker=c.get("ticker");cik=str(c.get("cik",""))
        if not ticker or not re.fullmatch(r"\d{10}",cik):continue
        url=f"https://data.sec.gov/submissions/CIK{cik}.json"
        try:
            obj=get_json(url,agent)
            recent=obj.get("filings",{}).get("recent",{})
            records=[]
            forms=recent.get("form",[])
            for i,form in enumerate(forms):
                if form not in KEEP_FORMS:continue
                acc=recent.get("accessionNumber",[])[i]
                filed=recent.get("filingDate",[])[i]
                doc=recent.get("primaryDocument",[])[i]
                if not re.fullmatch(r"\d{10}-\d{2}-\d{6}",acc):continue
                if not re.fullmatch(r"\d{4}-\d\d-\d\d",filed):continue
                if not re.fullmatch(r"[A-Za-z0-9._-]{1,160}",doc):continue
                source=f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-','')}/{doc}"
                desc={"8-K":"Current report","10-Q":"Quarterly financial report","10-K":"Annual financial report","20-F":"Foreign issuer annual report","6-K":"Foreign issuer report","13D":"Beneficial ownership disclosure","13G":"Beneficial ownership disclosure"}.get(form.split("/")[0],"SEC company filing")
                records.append({"form":form,"filed":filed,"description":desc,"accession":acc,"source_url":source})
                if len(records)>=40:break
            cache[ticker]=records
            success+=1
            print(ticker,len(records),"SEC filings")
        except Exception as e:
            failures.append(ticker+": "+str(e))
            print("WARNING",ticker,e)
        time.sleep(.4)
    if not success:
        raise SystemExit("No SEC submissions could be refreshed; existing file left unchanged.")
    result={"updated_at":dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "source":"SEC EDGAR public issuer submissions API",
            "source_url":"https://www.sec.gov/search-filings/edgar-application-programming-interfaces",
            "note":"Periodic collection; not push or email notifications. Data and filing dates come from SEC submissions, with amendments possible.",
            "refreshed_issuers":success,"failures":failures[:15],
            "tickers":cache}
    OUT.write_text(json.dumps(result,indent=2)+"\n")
if __name__=="__main__":main()
