#!/usr/bin/env python3
"""Collect the official source extracts for the 22 November 2026 release."""
from __future__ import annotations

import json
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent / "sources-2026-11-22"
ROOT.mkdir(exist_ok=True)
HEADERS = {"User-Agent": "Mariia Nyaas Financial & Risk Intelligence research; public-source reproduction"}


def get(url: str, timeout: int = 120) -> bytes:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def ssb(table: str, selections: dict[str, list[str]]) -> None:
    meta = get(f"https://data.ssb.no/api/v0/en/table/{table}", 90)
    (ROOT / f"ssb_{table}_meta.json").write_bytes(meta)
    query = {
        "query": [
            {
                "code": code,
                "selection": {
                    "filter": "all" if values == ["all"] else "item",
                    "values": ["*"] if values == ["all"] else values,
                },
            }
            for code, values in selections.items()
        ],
        "response": {"format": "json-stat2"},
    }
    body = json.dumps(query).encode()
    request = urllib.request.Request(
        f"https://data.ssb.no/api/v0/en/table/{table}",
        data=body,
        headers={**HEADERS, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as opened:
        response = opened.read()
    (ROOT / f"ssb_{table}_query.json").write_text(json.dumps(query, indent=2))
    (ROOT / f"ssb_{table}_response.json").write_bytes(response)


ssb("08727", {"RenteUtgift": ["15-20", "20-30", "30-40", "40+"], "Hushaldstype": ["50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "60", "61", "62", "63", "64", "65"], "ContentsCode": ["Hushald"], "Tid": ["all"]})
ssb("12128", {"OkonomiskRomslig": ["05", "16", "08", "09"], "Inntekstgruppe": ["000", "41", "42", "43", "44"], "ContentsCode": ["Personer"], "Tid": ["all"]})
ssb("10721", {"Sektor": ["C_OFF", "6100", "6500"], "Art": ["A51", "B41"], "ContentsCode": ["Belop"], "Tid": ["all"]})
ssb("09542", {"Region": ["Ialt"], "ContentsCode": ["Inntekter", "Utgifter", "Loyvingar"], "Tid": ["all"]})
ssb("09539", {"Region": ["Ialt"], "MuseBesok": ["01", "02", "03"], "ContentsCode": ["Besok"], "Tid": ["all"]})

countries = ["NO", "DK", "SE", "FI", "DE", "FR", "NL", "BE", "IE", "PL"]
for dataset in ["isoc_e_dii", "isoc_eb_ain2"]:
    for country in countries:
        url = f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}?lang=en&geo={country}"
        (ROOT / f"eurostat_{dataset}_{country}.json").write_bytes(get(url))

for name, url in {
    "norges_policy_rate.csv": "https://data.norges-bank.no/api/data/IR/B.KPRA?format=csv&startPeriod=2000-01-01&locale=en",
    "norges_eurnok_monthly.csv": "https://data.norges-bank.no/api/data/EXR/M.EUR.NOK.SP?format=csv&startPeriod=2000-01&locale=en",
}.items():
    (ROOT / name).write_bytes(get(url))

print(ROOT)
