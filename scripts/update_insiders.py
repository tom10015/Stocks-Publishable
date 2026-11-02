"""Read official SEC quarterly Insider Transactions Data Set Form 3/4/5 ZIPs.
The issuer-submissions index often does NOT contain insiders' Form 4 filings.
Join SEC ISSUER/SUBMISSION/REPORTINGOWNER/NONDERIV_TRANS tables by accession.
Only report verified non-derivative P/S codes. Unavailable ZIP means no change.
"""
import argparse,csv,datetime as dt,io,json,re,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"data"/"insiders.json"
COMPANIES=ROOT/"data"/"companies.json"
HEAD={"User-Agent":"StocksPublishable researcher "+__import__("os").environ.get("SEC_CONTACT_EMAIL",""),"Accept":"application/zip"}
TODAY=dt.datetime.now(dt.timezone.utc)
def norm(row):
 return {re.sub(r"[^A-Z0-9]","",k.upper()):v for k,v in row.items() if k}
def fld(row,*names):
 for n in names:
  val=row.get(re.sub(r"[^A-Z0-9]","",n.upper()))
  if val is not None:return str(val).strip()
 return ""
def table(z,base):
 name=next((n for n in z.namelist() if n.upper().split("/")[-1].startswith(base.upper()+".") and n.lower().endswith((".tsv",".txt",".csv"))),None)
 if not name:return []
 with z.open(name) as raw:
  wrapper=io.TextIOWrapper(raw,encoding="utf-8-sig",errors="replace",newline="")
  preview=wrapper.readline()
  wrapper.seek(0)
  delim="\t" if "\t" in preview else "|"
  return [norm(row) for row in csv.DictReader(wrapper,delimiter=delim)]
def find_table(z,name):
 return table(z,name)
def download(year,quarter):
 filename=f"{year}q{quarter}_form345.zip"
 candidates=[
  "https://www.sec.gov/files/datastandardsinnovation/data/insider-transactions-data-sets/"+filename,
  "https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/"+filename]
 errors=[]
 for url in candidates:
  try:
   req=urllib.request.Request(url,headers=HEAD)
   with urllib.request.urlopen(req,timeout=45) as response:raw=response.read(50_000_000)
   if not zipfile.is_zipfile(io.BytesIO(raw)):raise ValueError("Not ZIP")
   return zipfile.ZipFile(io.BytesIO(raw)),url
  except Exception as e:errors.append(str(e)[:90])
 raise RuntimeError("SEC quarterly dataset unavailable: "+"; ".join(errors))
def date_value(s):
 s=str(s or "").strip()
 for fmt in ("%Y-%m-%d","%d-%b-%Y","%d-%B-%Y","%m/%d/%Y","%Y%m%d"):
  try:return dt.datetime.strptime(s,fmt).date().isoformat()
  except ValueError:pass
 return None
def parse(z,watch_by_cik):
 # SEC's published eight-table schema has NO ISSUER table.
 # ISSUERCIK, DOCUMENT_TYPE and FILING_DATE all reside in SUBMISSION.
 submission=find_table(z,"SUBMISSION")
 if not submission:raise ValueError("SEC dataset missing SUBMISSION table")
 byacc={}
 filings={}
 for row in submission:
  cik=fld(row,"ISSUERCIK").lstrip("0")
  ticker=watch_by_cik.get(cik)
  if not ticker:continue
  acc=fld(row,"ACCESSION_NUMBER","ACCESSIONNUMBER")
  form=fld(row,"DOCUMENT_TYPE","DOCUMENTTYPE")
  date=date_value(fld(row,"FILING_DATE","FILINGDATE"))
  if not acc or form not in ("4","4/A") or not date:continue
  accession=re.sub("[^0-9]","",acc)
  if len(accession)!=18:continue
  filing={"ticker":ticker,"form":form,"filed":date,"accession":acc,
   "source_url":"https://www.sec.gov/Archives/edgar/data/"+str(int(cik))+"/"+accession+"/",
   "classification":"SEC Form 4: no verified P/S transaction",
   "verified_transactions":[]}
  byacc[acc]=ticker
  filings[acc]=filing
 print("SEC quarterly submission matches",len(filings),flush=True)
 if not filings:return {}
 owners={}
 for row in find_table(z,"REPORTINGOWNER"):
  acc=fld(row,"ACCESSION_NUMBER")
  if acc not in filings:continue
  name=fld(row,"RPTOWNERNAME")
  if name:owners.setdefault(acc,[]).append(name[:150])
 results={}
 for row in find_table(z,"NONDERIV_TRANS"):
  acc=fld(row,"ACCESSION_NUMBER")
  if acc not in filings:continue
  code=fld(row,"TRANS_CODE")
  if code not in ("P","S"):continue
  qty=fld(row,"TRANS_SHARES")
  try:shares=float(qty.replace(",",""))
  except (ValueError,TypeError):continue
  if not 0<shares<1e12:continue
  date=date_value(fld(row,"TRANS_DATE"))
  if not date:continue
  rawprice=fld(row,"TRANS_PRICEPERSHARE")
  try:price=float(rawprice.replace(",",""))
  except (ValueError,TypeError):price=None
  sec=fld(row,"SECURITY_TITLE")
  f=filings[acc]
  f["verified_transactions"].append({
   "code":code,"classification":"Reported purchase (P)" if code=="P" else "Reported sale (S)",
   "date":date,"shares":shares,"price":price if price is not None and price>=0 else None,
   "owner":", ".join(dict.fromkeys(owners.get(acc,[])))[:180] or "SEC reporting owner",
   "security":sec[:90],
   "note":"SEC reported non-derivative Form 4 P/S; execution venue/motivation not independently verified."})
 for f in filings.values():
  if not f["verified_transactions"]:continue
  f["classification"]="Verified SEC non-derivative P/S"
  results.setdefault(f["ticker"],[]).append(f)
 return results

def main():
    import os
    email=os.environ.get("SEC_CONTACT_EMAIL","").strip()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",email):
        raise SystemExit("Set SEC_CONTACT_EMAIL to a genuine contact email before downloading SEC insider datasets.")
    HEAD["User-Agent"]="StocksPublishable researcher "+email
    names=json.loads(COMPANIES.read_text()).get("companies",[])
    by_cik={str(int(c["cik"])):c["ticker"] for c in names if c.get("cik") and c.get("ticker")}
    old=json.loads(DEST.read_text()) if DEST.exists() else {}
    result=old.get("tickers",{})
    q=(TODAY.month-1)//3+1
    periods=[]
    for offset in range(3):
        year=TODAY.year;quarter=q-offset
        while quarter<1:
            year-=1;quarter+=4
        periods.append((year,quarter))
    fetched=0
    for year,quarter in periods:
        try:
            archive,url=download(year,quarter)
            with archive:
                matched=parse(archive,by_cik)
            for ticker,filings in matched.items():
                existing=result.get(ticker,{}).get("transactions",[])
                additions=[]
                for f in filings:
                    for t in f["verified_transactions"]:
                        additions.append({"type":t["code"],"date":t["date"],"filed":f["filed"],
                            "shares":t["shares"],"price":t["price"],"owner":t["owner"],
                            "security":t["security"],"source_url":f["source_url"]})
                unique={}
                for t in existing+additions:
                    key=(t.get("source_url"),t.get("date"),t.get("type"),t.get("owner"),t.get("shares"),t.get("price"))
                    unique[key]=t
                result[ticker]={"period":f"{year} Q{quarter}","source_url":url,
                                "transactions":sorted(unique.values(),key=lambda r:r.get("date",""),reverse=True)[:75]}
            fetched+=1
            print(f"Downloaded SEC {year} Q{quarter}")
        except Exception as e:
            print("WARNING: quarterly SEC insider ZIP unavailable:",year,quarter,str(e)[:150])
    if not fetched:raise SystemExit("SEC insider datasets unavailable; existing data retained.")
    out={"updated_at":TODAY.isoformat(timespec="seconds"),"source":"SEC Form 4 non-derivative P/S transactions",
         "source_url":"https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets",
         "notes":"Quarterly delayed SEC data; unverified transactions and non-P/S codes excluded. Not a live feed.",
         "tickers":result}
    DEST.write_text(json.dumps(out,ensure_ascii=False,separators=(",",":"))+"\n")
if __name__=="__main__":main()
