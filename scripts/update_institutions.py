#!/usr/bin/env python3
"""Read an official SEC quarterly Form 13F dataset and match issuer names strictly.
Caution: 13F is delayed and incomplete; no CUSIP is copied or redisplayed.
Download is substantial (~100 MB compressed). Run monthly, not for page requests.
"""
import csv,datetime as dt,html,io,json,os,re,time,zipfile
from pathlib import Path
from urllib.parse import urljoin,urlparse
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"institutions.json"
COMPANIES=ROOT/"data"/"companies.json"
LANDING="https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets"
FALLBACK="https://www.sec.gov/files/datastandardsinnovation/data/form-13f-data-sets/01jun2026-31aug2026_form13f.zip"
def normal(s):return re.sub(r"[^A-Z0-9]","",str(s or "").upper())
def fields(row):return {normal(k):str(v or "").strip() for k,v in row.items() if k}
def field(row,*keys):
    for k in keys:
        v=row.get(normal(k))
        if v:return v
    return ""
def source_url(cik,accession,otherwise):
    acc=re.sub(r"[^0-9]","",str(accession or ""))
    if cik and acc and len(acc)==18 and str(cik).isdigit():
        return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/"
    return otherwise
def table(z,key):
    name=next((n for n in z.namelist() if n.split("/")[-1].upper().startswith(key.upper()+".")
            and n.lower().endswith((".tsv",".txt",".csv"))),None)
    if not name:raise ValueError("Dataset missing "+key+" table")
    with z.open(name) as f:
        txt=io.TextIOWrapper(f,encoding="utf-8-sig",errors="replace",newline="")
        header=txt.readline()
        txt.seek(0)
        reader=csv.DictReader(txt,delimiter="\t" if "\t" in header else "|")
        for row in reader:yield fields(row)
def get(url,agent,limit):
    if urlparse(url).hostname!="www.sec.gov" or not url.startswith("https://"):
        raise ValueError("Only secure SEC download URLs are permitted")
    req=Request(url,headers={"User-Agent":agent,"Accept":"text/html,application/zip"})
    with urlopen(req,timeout=100) as response:
        data=response.read(limit+1)
    if len(data)>limit:raise ValueError("SEC response exceeded download limit")
    return data
def latest_archive(agent):
    page=get(LANDING,agent,2_500_000).decode("utf-8",errors="replace")
    links=re.findall(r'href=["\']([^"\']+_form13f\.zip)["\']',page,re.I)
    for link in links:
        url=urljoin(LANDING,html.unescape(link))
        if urlparse(url).hostname=="www.sec.gov":return url
    return FALLBACK
def parse_number(s):
    try:return float(str(s).replace(",",""))
    except (ValueError,TypeError):return None
def main():
    email=os.environ.get("SEC_CONTACT_EMAIL","").strip()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",email):
        raise SystemExit("Set SEC_CONTACT_EMAIL before downloading 13F filings.")
    agent="StocksPublishable research "+email
    companies=json.loads(COMPANIES.read_text()).get("companies",[])
    lookup={}
    ambiguous=set()
    for c in companies:
        name=normal(c.get("name"))
        if len(name)<6:continue
        if name in lookup:ambiguous.add(name)
        lookup[name]=c["ticker"]
    for name in ambiguous:lookup.pop(name,None)
    src=latest_archive(agent)
    previous=json.loads(OUT.read_text()) if OUT.exists() else {}
    if previous.get("dataset_url")==src and previous.get("matched_rows",0)>0:
        print("Already imported latest official SEC 13F dataset; skipping large download.")
        return
    data=get(src,agent,180_000_000)
    if not zipfile.is_zipfile(io.BytesIO(data)):raise SystemExit("Latest SEC 13F download is not a ZIP; no update.")
    byacc={}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for row in table(z,"SUBMISSION"):
            acc=field(row,"ACCESSION_NUMBER")
            if not acc:continue
            byacc[acc]={"cik":field(row,"CIK","FILINGMANAGER_CIK","FILERCIK"),
                "period":field(row,"PERIODOFREPORT","REPORTCALENDARORQUARTER","PERIOD_OF_REPORT"),
                "form":field(row,"SUBMISSIONTYPE","SUBMISSION_TYPE","DOCUMENTTYPE")}
        print("13F submission keys:",len(byacc),flush=True)
        managers={}
        try:
            for row in table(z,"COVERPAGE"):
                acc=field(row,"ACCESSION_NUMBER")
                if not acc:continue
                managers[acc]={"manager":field(row,"FILINGMANAGER_NAME","FILING_MANAGER_NAME","FILINGMANAGERNAME") or "SEC reporting manager",
                    "period":field(row,"REPORTCALENDARORQUARTER","REPORT_CALENDAR_OR_QUARTER")}
        except ValueError as e:
            print("WARNING",e)
        selected={}
        count=0
        for row in table(z,"INFOTABLE"):
            name=normal(field(row,"NAMEOFISSUER","NAME_OF_ISSUER"))
            ticker=lookup.get(name)
            if not ticker:continue
            call=field(row,"PUTCALL","PUT_CALL")
            if call:continue
            typ=field(row,"SSHPRNAMTTYPE","SSHPRNAMTTYPE","SHRS_OR_PRN_AMT_TYPE")
            if typ and typ.upper() not in ("SH","SHS"):continue
            acc=field(row,"ACCESSION_NUMBER")
            meta=byacc.get(acc,{})
            cover=managers.get(acc,{})
            shares=parse_number(field(row,"SSHPRNAMT","SHRSORPRNAMT","SHRS_OR_PRN_AMT"))
            if shares is None or shares<=0:continue
            value=parse_number(field(row,"VALUE","VALUE_USD_EST"))
            source=source_url(meta.get("cik"),acc,src)
            record={"manager":cover.get("manager") or "SEC reporting manager",
                "period":cover.get("period") or meta.get("period") or "Quarter not supplied",
                "shares":shares,"value_usd":value if value is not None and value>=0 else None,
                "security_class":field(row,"TITLEOFCLASS","TITLE_OF_CLASS")[:80],
                "source_url":source}
            selected.setdefault(ticker,[]).append(record)
            count+=1
        print("Matched issuer-name rows:",count,flush=True)
    if not count:
        raise SystemExit("No strict issuer-name matches in SEC 13F dataset; retaining prior data.")
    result={}
    for ticker,rows in selected.items():
        rows.sort(key=lambda v:v.get("shares",0),reverse=True)
        result[ticker]={"positions":rows[:45]}
    output={"updated_at":dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source":"SEC Form 13F official quarterly structured dataset",
        "source_url":LANDING,"dataset_url":src,"matched_rows":count,
        "match_method":"Exact normalization of the reported issuer name against SEC company names; ambiguous names excluded. Not a licensed CUSIP-to-ticker match.",
        "note":"13F filings are delayed, exclude many investments, and may contain amendments. Values/units are as filed; review full SEC reports. No percentage ownership inferred.",
        "tickers":result}
    OUT.write_text(json.dumps(output,separators=(",",":"))+"\n")
if __name__=="__main__":main()

# Validation/deployment trigger: official-source collector only.
