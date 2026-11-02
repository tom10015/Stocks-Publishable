"""One-time seeded subset of existing SEC-filed facts; no market data."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
data = [
("AAPL","Apple Inc.","0000320193","2025-09-27","2024-09-29",416161000000,112010000000,7.46,111482000000,12715000000,107520000000,"2026-06-27",[("2025-01-17",15022073000,"10-Q"),("2025-07-18",14840390000,"10-Q"),("2025-10-17",14776353000,"10-K"),("2026-01-16",14681140000,"10-Q"),("2026-04-17",14687356000,"10-Q"),("2026-07-17",14594180000,"10-Q")]),
("NVDA","NVIDIA Corporation","0001045810","2026-01-25","2025-01-27",215938000000,120067000000,4.90,102718000000,6042000000,228984000000,"2026-07-26",[("2025-02-21",24400000000,"10-K"),("2025-08-22",24300000000,"10-Q"),("2025-11-14",24300000000,"10-Q"),("2026-02-20",24300000000,"10-K"),("2026-05-15",24200000000,"10-Q"),("2026-08-21",24100000000,"10-Q")]),
("AMZN","Amazon.com, Inc.","0001018724","2025-12-31","2025-01-01",716924000000,77670000000,7.17,139514000000,131819000000,613601000000,"2026-09-30",[("2025-04-23",10616352407,"10-Q"),("2025-10-22",10690216011,"10-Q"),("2026-01-28",10734920870,"10-K"),("2026-04-22",10757109436,"10-Q"),("2026-07-22",10786313572,"10-Q"),("2026-10-21",10813138306,"10-Q")]),
("SOFI","SoFi Technologies, Inc.","0001818874","2025-12-31","2025-01-01",619353000,481320000,0.39,-3742458000,242444000,11076227000,"2026-06-30",[("2025-01-31",1096540215,"10-K"),("2025-07-31",1197450100,"10-Q"),("2025-10-31",1205903044,"10-Q"),("2026-01-30",1275263850,"10-K"),("2026-04-30",1282741200,"10-Q"),("2026-07-31",1291570324,"10-Q")]),
("SOUN","SoundHound AI, Inc.","0001840856","2025-12-31","2025-01-01",168920000,-14006000,-0.28,-98222000,902000,490430000,"2026-06-30",[]),
("IREN","IREN Limited","0001878848","2026-06-30","2025-07-01",707007000,-702621000,-2.22,2100418000,2998006000,4185613000,"2026-06-30",[("2025-10-31",283465490,"10-Q"),("2026-01-30",332280383,"10-Q"),("2026-04-30",357378674,"10-Q")]),
]
companies=[]
for t,name,cik,end,start,rev,net,eps,ocf,cap,equ,eqdate,shares in data:
    url=f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    metrics={key:{"value":value,"period_start":start,"period_end":end,"source_url":url}
             for key,value in [("revenue",rev),("net_income",net),("diluted_eps",eps),("operating_cash_flow",ocf),("capex",cap)]}
    if t=="SOFI":
        metrics.pop("revenue",None)  # bank revenue requires bank-specific accounting tags
    metrics["equity"]={"value":equ,"period_start":None,"period_end":eqdate,"source_url":url}
    entries=[{"date":date,"shares":count,"form":form,"source_url":url,"concept":"dei:EntityCommonStockSharesOutstanding"}
             for date,count,form in shares]
    companies.append({"ticker":t,"name":name,"cik":cik,"source":"SEC EDGAR XBRL companyfacts", "source_url":url,"metrics":metrics,"shares_history":entries})
obj={"updated_at":"2026-11-02", "seed_note":"Initial SEC-derived starter snapshot from prior automated collection, not independently refreshed at build time. Run the GitHub Actions collector for current filings.","source":"SEC EDGAR public XBRL companyfacts (historical)","companies":companies}
(root/'data'/'companies.json').write_text(json.dumps(obj,indent=2)+'\n')
print(f'Generated {len(companies)} seeded SEC issuer profiles.')