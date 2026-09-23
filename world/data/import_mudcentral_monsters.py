#!/usr/bin/env python3
"""Convert MudCentral MajorMUD monster scrape into a lossless ROP mob catalog."""
from __future__ import annotations
import json, re, sys
from collections import Counter
from pathlib import Path

DEFAULT_SOURCE = Path("/root/mudcentral_monsters_index.txt")
DEFAULT_OUTPUT = Path(__file__).with_name("mudcentral_monsters.json")
ROW_RE = re.compile(r"^\[ROW\s+\d+\]$")
DROP_RE = re.compile(r"^Drops?\s+", re.I)
PCT_RE = re.compile(r"^(.*?)(?:\s+(-?\d+(?:\.\d+)?)%)$")

def integer(text):
    text=text.strip().replace(",","")
    if not text: return None
    try: return int(text)
    except ValueError: return None

def number(text):
    text=text.strip().replace(",","")
    if not text: return None
    try: return int(text)
    except ValueError:
        try: return float(text)
        except ValueError: return None

def slugify(text):
    s=re.sub(r"\bNEW\b","",text,flags=re.I).strip().lower()
    s=re.sub(r"[^a-z0-9]+","_",s).strip("_")
    return s or "monster"

def split_ac(text):
    if not text: return (None,None)
    a,sep,b=text.partition("/")
    return (number(a), number(b) if sep else None)

def parse_drop_line(text):
    body=DROP_RE.sub("",text,1).strip()
    drops=[]
    for chunk in [x.strip() for x in body.split(",") if x.strip()]:
        m=PCT_RE.match(chunk)
        if m:
            drops.append({"item_name":m.group(1).strip(),"chance_percent":number(m.group(2)),"raw":chunk})
        else:
            drops.append({"item_name":chunk,"chance_percent":None,"raw":chunk})
    return drops

def extract_rows(text):
    structured=text.split("STRUCTURED TABLE DATA",1)[-1].split("FULL PAGE TEXT",1)[0]
    lines=structured.splitlines()
    out=[]
    i=0
    while i<len(lines):
        if ROW_RE.match(lines[i].strip()):
            i+=1
            vals=[]
            while i<len(lines) and not ROW_RE.match(lines[i].strip()):
                if lines[i].strip(): vals.append(lines[i].strip())
                i+=1
            out.append(" ".join(vals).strip())
        else:
            i+=1
    return out

def main():
    source=Path(sys.argv[1]) if len(sys.argv)>1 else DEFAULT_SOURCE
    output=Path(sys.argv[2]) if len(sys.argv)>2 else DEFAULT_OUTPUT
    rows=extract_rows(source.read_text(encoding="utf-8",errors="replace"))
    appearances=[]
    current=None
    for row in rows:
        if row.count("|")==7:
            if current: appearances.append(current)
            p=[x.strip() for x in row.split("|")]
            ac,dr=split_ac(p[3])
            current={
                "name":re.sub(r"\s+NEW\s*$","",p[0],flags=re.I).strip(),
                "source_name":p[0],
                "exp":integer(p[1]), "hp":integer(p[2]),
                "ac":ac, "damage_reduction":dr,
                "magic_resistance":integer(p[4]),
                "regen":integer(p[5]), "magical":integer(p[6]),
                "spell_immunity":integer(p[7]),
                "special":[],"drops":[],
                "source_stats_raw":row,
            }
        elif current and row and row!="Notes" and not row.startswith("Subscribe to"):
            if DROP_RE.match(row):
                current["drops"].extend(parse_drop_line(row))
            else:
                current["special"].append(row)
    if current: appearances.append(current)

    # Preserve genuinely distinct same-name variants. Merge exact-stat repeats and union details/drops.
    catalog={}
    sig_to_id={}
    counters=Counter()
    duplicate_appearances=0
    for rec in appearances:
        base=slugify(rec["name"])
        sig=(base,rec["exp"],rec["hp"],rec["ac"],rec["damage_reduction"],
             rec["magic_resistance"],rec["regen"],rec["magical"],rec["spell_immunity"])
        if sig in sig_to_id:
            duplicate_appearances+=1
            old=catalog[sig_to_id[sig]]
            for s in rec["special"]:
                if s not in old["special"]: old["special"].append(s)
            for d in rec["drops"]:
                if d not in old["drops"]: old["drops"].append(d)
            old["source_appearances"]+=1
            continue
        counters[base]+=1
        mid=base if counters[base]==1 else f"{base}__variant_{counters[base]}"
        rec["mob_id"]=mid
        rec["source_appearances"]=1
        catalog[mid]=rec
        sig_to_id[sig]=mid

    payload={
        "source":str(source),
        "source_url":"https://www.mudcentral.org/monsters/monsterall.html",
        "format_version":1,
        "source_rows":len(rows),
        "monster_appearances":len(appearances),
        "duplicate_appearances_merged":duplicate_appearances,
        "unique_monster_variants":len(catalog),
        "monsters":catalog,
    }
    output.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("MudCentral monster conversion complete")
    print("="*44)
    print(f"Monster appearances:          {len(appearances)}")
    print(f"Duplicate appearances merged: {duplicate_appearances}")
    print(f"Unique monster variants:      {len(catalog)}")
    print(f"Output: {output}")

if __name__=="__main__":
    main()
