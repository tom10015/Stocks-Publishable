#!/usr/bin/env python3
"""Collect BLS and US Treasury public economic indicators, without paid APIs.
BLS API v1: official, 2 public requests. Treasury Fiscal Data API: official JSON.
Never silently replace missing values with invented observations.
"""
import datetime as dt
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"economy.json"
HEAD={"User-Agent":"StocksPublishable educational-data-research/1.0","Accept":"application/json"}

def fetch(url):
    req=Request(url,headers=HEAD)
    for attempt in range(3):
        try:
            with urlopen(req,timeout=35) as response:
                return json.load(response)
        except Exception:
            if attempt==2:raise
            time.sleep(3*(attempt+1))

def bls(sid,name,desc,unit):
    url="https://api.bls.gov/publicAPI/v1/timeseries/data/"+sid
    obj=fetch(url)
    if obj.get("status")!="REQUEST_SUCCEEDED":raise ValueError("BLS did not confirm success: "+str(obj.get("message")))
    found=[v for v in obj.get("Results",{}).get("series",[]) if v.get("seriesID")==sid]
    if not found:raise ValueError("BLS series not found")
    rows=[]
    for x in found[0].get("data",[]):
        period=x.get("period","")
        if not period.startswith("M") or period=="M13":continue
        try:
            month=int(period[1:]);value=float(x["value"]);year=int(x["year"])
            if not 1<=month<=12:continue
        except (KeyError,ValueError,TypeError):continue
        rows.append({"date":f"{year}-{month:02d}","value":value})
    rows.sort(key=lambda x:x["date"])
    if not rows:raise ValueError("BLS series had no usable observations")
    return {"id":"cpi" if sid=="CUUR0000SA0" else "unemployment","name":name,
            "agency":"BLS","description":desc,"unit":unit,"source_url":url,
            "note":"BLS data may be revised. CPI is not an inflation percent rate; it is a published index.",
            "observations":rows[-36:]}

def treasury():
    base="https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny"
    url=base+"?"+urlencode({"fields":"record_date,tot_pub_debt_out_amt",
        "sort":"-record_date","page[size]":"110"})
    obj=fetch(url)
    rows=[]
    for x in obj.get("data",[]):
        try:
            val=float(str(x["tot_pub_debt_out_amt"]).replace(",",""))
            date=x["record_date"]
            if val<=0 or len(date)!=10:continue
        except (ValueError,TypeError,KeyError):continue
        rows.append({"date":date,"value":val})
    rows.sort(key=lambda x:x["date"])
    if not rows:raise ValueError("Treasury debt endpoint had no usable rows")
    return {"id":"debt","name":"Total U.S. Public Debt Outstanding","agency":"U.S. Treasury",
            "description":"Federal public debt outstanding (not Treasury security yield).",
            "unit":"USD","source_url":base,
            "note":"This is the total public debt outstanding, not market bond yields or the federal deficit.",
            "observations":rows[-90:]}

def main():
    old=json.loads(OUT.read_text()) if OUT.exists() else {}
    saved={x["id"]:x for x in old.get("series",[]) if x.get("id")}
    errors=[]
    for key,fn in [
        ("cpi",lambda:bls("CUUR0000SA0","CPI-U, U.S. City Average (All Items)",
                     "Not seasonally adjusted consumer price index for all urban consumers.","index")),
        ("unemployment",lambda:bls("LNS14000000","Civilian Unemployment Rate",
                     "Seasonally adjusted unemployment percentage of the civilian labor force.","percent")),
        ("debt",treasury)]:
        try:
            saved[key]=fn()
            print(key,"latest",saved[key]["observations"][-1]["date"])
        except Exception as e:
            errors.append(f"{key}: {e}")
            print("WARNING",key,e)
    if not any(saved.get(k,{}).get("observations") for k in ("cpi","unemployment","debt")):
        raise SystemExit("No official observations available; preserving prior data.")
    out={"updated_at":dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
         "source":"Official BLS Public Data API and U.S. Treasury Fiscal Data API",
         "sources":{"BLS":"https://www.bls.gov/developers/termsOfService.htm",
                    "Treasury":"https://fiscaldata.treasury.gov/"},
         "bls_required_disclaimer":"BLS.gov cannot vouch for the data or analyses derived from these data after the data have been retrieved from BLS.gov.",
         "errors":errors,
         "series":[saved[k] for k in ("cpi","unemployment","debt") if k in saved and saved[k].get("observations")]}
    OUT.write_text(json.dumps(out,indent=2)+"\n")

if __name__=="__main__":main()
