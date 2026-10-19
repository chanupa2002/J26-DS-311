"""Build a read-only D1 housing material crosswalk and feasibility audit."""
from pathlib import Path
from itertools import product
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "component1_audit" / "outputs" / "d1_housing_material_validation"
MASTER = ROOT / "Data" / "bright_csv" / "mod_a_household_identification.csv"
HOUSING = ROOT / "Data" / "processed" / "clean" / "mod_c_housing.csv"
QUESTIONNAIRE = "Data/BRIGHT_questionnaire_English.pdf, PDF pp.14-15 (printed pp.14-15)"
CENSUS = "Department of Census and Statistics, Census of Population and Housing 2024, Final Report (English), section 11.5 ‘Status of housing unit’, printed p.189, table captioned ‘Basis for classifying status of housing units as permanent, semi-permanent, and improvised’"

ITEMS = {
    "c1_04": ("C1_04", "principal wall material", {
        "1": ("Brick", "exact", "Bricks"), "2": ("Cement block", "exact", "Cement blocks"),
        "3": ("Stone/Cube stone", "exact", "Granite/cube stones"), "4": ("Cabook", "exact", "Cabook"),
        "5": ("Clay", "unresolved", ""), "6": ("Cadjan/Palmyrah", "approximate", "Coconut/palmyrah leaves or straw"),
        "7": ("Wood", "unmatched", ""), "8": ("Asbestos", "unmatched", ""),
        "9": ("Cloth (no walls)", "unmatched", ""), "10": ("Polythene", "unmatched", ""),
        "11": ("Metal sheet/Takaran", "approximate", "Planks or metal sheet/asbestos/zinc aluminium sheets"),
        "999": ("Other, specify", "unresolved", ""),
    }),
    "c1_05": ("C1_05", "principal flooring material", {
        "1": ("Cement", "exact", "Cement"), "2": ("Teraso/Tile/Granite", "exact", "Terrazzo/tile/granite"),
        "3": ("Mud", "exact", "Mud"), "4": ("Wood", "exact", "Wood"), "5": ("Sand", "exact", "Sand"),
        "6": ("Concrete", "exact", "Concrete"), "7": ("Metal", "unmatched", ""), "999": ("Other, specify", "unresolved", ""),
    }),
    "c1_06": ("C1_06", "principal roof material", {
        "1": ("Tile", "exact", "Tiles"), "2": ("Asbestos", "exact", "Asbestos"),
        "3": ("Concrete", "exact", "Concrete"), "4": ("Metal sheet", "approximate", "Zink Aluminium sheets/Metal sheet"),
        "5": ("Takaran", "approximate", "Zink Aluminium sheets/Metal sheet"),
        "6": ("Cadjan/Palmyrah/Straw", "exact", "Coconut/palmyrah leaves or straw"),
        "7": ("Polythene", "unmatched", ""), "999": ("Other, specify", "unresolved", ""),
    }),
}

# Census material families used by each combination rule, as literally listed in §11.5.
RULES = [
    ("Permanent", {"brick", "block", "stone", "cabook", "pressed soil brick"}, {"tile", "asbestos", "concrete", "zinc/aluminium sheet", "metal sheet"}, {"cement", "terrazzo", "tile/granite", "wood finished", "titanium", "concrete"}, "Permanent row 1"),
    ("Permanent", {"mud/warichchi"}, {"tile", "asbestos", "zinc/aluminium sheet", "metal sheet"}, {"cement", "concrete"}, "Permanent row 2"),
    ("Semi-permanent", {"brick", "block", "stone", "cabook", "pressed soil brick"}, {"tile", "asbestos", "concrete", "zinc/aluminium sheet", "metal sheet"}, {"mud", "wood", "sand"}, "Semi-permanent row 1"),
    ("Semi-permanent", {"brick", "block", "stone", "cabook", "pressed soil brick"}, {"coconut/palmyrah leaves", "straw", "other"}, {"cement", "concrete", "mud", "wood", "sand"}, "Semi-permanent row 2"),
    ("Semi-permanent", {"mud/warichchi"}, {"tile", "asbestos", "zinc/aluminium sheet", "metal sheet"}, {"mud", "wood", "sand"}, "Semi-permanent row 3"),
    ("Semi-permanent", {"mud/warichchi"}, {"coconut/palmyrah leaves", "straw", "other"}, {"cement", "concrete", "mud", "wood"}, "Semi-permanent row 4"),
    ("Semi-permanent", {"planks or metal sheet/asbestos/zinc aluminium sheets"}, {"tile", "asbestos", "zinc/aluminium sheet", "metal sheet", "other"}, {"cement", "concrete", "mud", "wood", "sand"}, "Semi-permanent row 5"),
    ("Semi-permanent", {"planks or metal sheet/asbestos/zinc aluminium sheets"}, {"coconut/palmyrah leaves", "straw"}, {"cement", "concrete"}, "Semi-permanent row 6"),
    ("Improvised", {"coconut/palmyrah leaves", "straw"}, None, None, "Improvised row 1"),
    ("Improvised", {"planks or metal sheet/asbestos/zinc aluminium sheets"}, {"coconut/palmyrah leaves", "straw"}, {"mud", "wood", "sand"}, "Improvised row 2"),
]

def main():
    master = pd.read_csv(MASTER, dtype={"hhcode": "string"})
    h = pd.read_csv(HOUSING, dtype={"hhcode": "string", "c1_04": "string", "c1_05": "string", "c1_06": "string"})
    assert master.hhcode.notna().all() and master.hhcode.is_unique
    assert h.hhcode.notna().all() and h.hhcode.is_unique
    assert set(h.hhcode).issubset(set(master.hhcode))
    df = master[["hhcode"]].merge(h[["hhcode", *ITEMS]], on="hhcode", how="left", validate="one_to_one", indicator=True)
    assert len(df) == len(master) and df.hhcode.equals(master.hhcode)
    assert (df._merge == "both").all()
    df.drop(columns="_merge", inplace=True)
    total = len(master)
    cross, coded = [], {}
    for col, (var, label, codes) in ITEMS.items():
        vals = df[col].fillna("[MISSING]")
        denom = int(vals.ne("[MISSING]").sum())
        coded[col] = {}
        for code in sorted(vals.unique(), key=lambda x: (x == "[MISSING]", int(x) if x.isdigit() else 99999)):
            count = int(vals.eq(code).sum())
            if code == "[MISSING]":
                orig, status, census_cat = "[Missing]", "unresolved", ""
                explanation = "Missing response; retained as missing, not a material category."
            elif code in codes:
                orig, status, census_cat = codes[code]
                explanation = ("Terminology/category directly aligns with the Census rule." if status == "exact" else
                    "Wording is broader or not equivalent enough for a deterministic classification." if status in {"approximate", "unresolved"} else
                    "BRIGHT material is absent from the Census §11.5 combinations.")
            else:
                orig, status, census_cat = f"Unlisted code {code}", "unresolved", ""
                explanation = "Observed code is not listed among questionnaire options; preserve pending source clarification."
            othercol = col + "_other"
            examples = sorted({str(x).strip() for x in h.loc[h[col].eq(code), othercol].dropna() if str(x).strip()}) if code == "999" and othercol in h else []
            if code == "999": explanation += " Free-text other responses remain separate; no text is assigned to a Census category." 
            row = {"bright_variable":var,"response_code":code,"original_questionnaire_label":orig,"observed_household_count":count,"percent_all_master_households":100*count/total,"percent_nonmissing_item_responses":(100*count/denom if code!="[MISSING]" and denom else ""),"census_category_or_material_family":census_cat,"mapping_status":status,"census_reference":CENSUS,"explanation":explanation,"other_text_value_count_distinct":len(examples) if code=="999" else ""}
            cross.append(row)
            coded[col][code] = (status, census_cat)

    pd.DataFrame(cross).to_csv(OUT/"housing_material_crosswalk.csv",index=False)
    # Combined rules only attempted where each item is nonmissing and exact mapping is supported.
    comb={}
    for _,r in df.iterrows():
        keys=tuple(v if pd.notna(v) else "[MISSING]" for v in (r.c1_04,r.c1_06,r.c1_05))
        sig=tuple(coded[c].get(v,("unresolved","")) for c,v in zip(("c1_04","c1_06","c1_05"),keys))
        if any(v=="[MISSING]" for v in keys): reason="Missing one or more material responses"
        elif any(s[0]=="approximate" for s in sig): reason="Depends on one or more approximate material equivalences"
        elif any(s[0]!="exact" for s in sig): reason="One or more materials unmatched or unresolved"
        else:
            # Category family normalization based only on exact labels
            wall,roof,floor=(x[1] for x in sig)
            wf={"Brick":"brick","Cement block":"block","Stone/Cube stone":"stone","Cabook":"cabook","Teraso/Tile/Granite":"tile/granite"}
            # Only literal exact BRIGHT labels map to a family listed in the rules.
            wfam=wf.get(wall,wall.lower())
            rfam=roof.lower(); ffam=floor.lower()
            hits=[]
            for status,ws,rs,fs,name in RULES:
                if wfam in ws and (rs is None or rfam in rs) and (fs is None or ffam in fs): hits.append((status,name))
            if len(hits)==1: reason="Verified rule: "+hits[0][1]
            elif len(hits)>1: reason="Multiple Census rules match; status unresolved pending rule precedence"
            else: reason="No published combination rule matches this exact material combination"
        key=(*keys,reason)
        comb[key]=comb.get(key,0)+1
    feasibility=[]
    for key,n in sorted(comb.items(),key=lambda z:(-z[1],z[0])):
        a,b,c,reason=key
        feasibility.append({"wall_response_code":a,"roof_response_code":b,"floor_response_code":c,"feasibility_status":("classifiable by verified rule" if reason.startswith("Verified rule:") else "not classifiable"),"rule_or_limitation":reason,"household_count":n,"percent_all_master_households":100*n/total,"census_reference":CENSUS})
    pd.DataFrame(feasibility).to_csv(OUT/"housing_combination_feasibility.csv",index=False)

    freqs=[]
    for col,(var,label,codes) in ITEMS.items():
        vals=df[col].fillna("[MISSING]"); valid=int(vals.ne("[MISSING]").sum())
        for code,n in vals.value_counts(dropna=False).items():
            freqs.append({"representation":var,"category_code":code,"category_label": codes.get(code,("[Missing]","",""))[0] if code!="[MISSING]" else "[Missing]","household_count":int(n),"denominator_nonmissing_responses":valid,"denominator_all_households":total,"percent_nonmissing_responses":100*n/valid if code!="[MISSING]" and valid else "","percent_all_households":100*n/total})
    for row in feasibility:
        freqs.append({"representation":"combined_status_feasibility","category_code":row["feasibility_status"],"category_label":row["rule_or_limitation"],"household_count":row["household_count"],"denominator_nonmissing_responses":"all three observed: see feasibility file","denominator_all_households":total,"percent_nonmissing_responses":"","percent_all_households":row["percent_all_master_households"]})
    pd.DataFrame(freqs).to_csv(OUT/"housing_material_frequency_report.csv",index=False)
    # Report summary counts without microdata.
    classifiable=sum(x["household_count"] for x in feasibility if x["feasibility_status"]=="classifiable by verified rule")
    all3=int(df[list(ITEMS)].notna().all(axis=1).sum())
    report=f'''# D1 housing material classification validation audit\n\n**Status:** read-only validation for researcher review. No deprivation coding, score, or model feature is implemented.\n\n## Inputs inspected\n\n- Questionnaire: `{QUESTIONNAIRE}`. It identifies C1_04 as walls, C1_05 as flooring, and C1_06 as roof; the cleaned field order agrees.\n- Household master: `Data/bright_csv/mod_a_household_identification.csv`, key `hhcode` ({total:,} rows).\n- Cleaned module: `Data/processed/clean/mod_c_housing.csv`; columns `hhcode`, `c1_04`, `c1_04_other`, `c1_05`, `c1_05_other`, `c1_06`, `c1_06_other`.\n- Census reference: [{CENSUS}](https://www.statistics.gov.lk/Resource/en/Population/CPH_2024/CPH2024_Final_Eng.pdf).\n\n## Verified Census source rules\n\nSection 11.5, printed page 189, Table “Basis for classifying status of housing units as permanent, semi-permanent, and improvised” gives ten rows: two permanent combinations, six semi-permanent combinations, and two improvised combinations. They are transcribed in the script's `RULES` list and evaluated without inferring equivalence. Permanent row 1 is durable listed walls + durable listed roof + listed finished floor; permanent row 2 is mud/warichchi walls + tile/asbestos/zinc aluminium/metal sheet roof + cement/concrete floor. Semi-permanent rows separately enumerate durable walls with durable roof and mud/wood/sand floor; durable walls with leaf/straw/other roof and the listed floors; analogous mud-wall combinations; and plank/metal-sheet wall combinations. Improvised is leaf/palmyrah/straw walls with any roof and floor, or plank/metal-sheet/asbestos/zinc-aluminium walls with leaf/straw roof and mud/wood/sand floor. The source does not supply a generic hierarchy or fallback for combinations outside these rows.\n\n## Item crosswalk findings\n\nThe CSV contains every observed code including missing, frequency and denominator. Exact matches are only assigned where the BRIGHT label directly matches a Census material. Approximate mappings (wall Cadjan/Palmyrah; wall Metal sheet/Takaran; roof Metal sheet and Takaran) are retained as approximate and excluded from deterministic combined classifications. BRIGHT Clay is unresolved against the Census wording Mud/warichchi. BRIGHT wall Wood/Asbestos/Cloth/Polythene, floor Metal, and roof Polythene are unmatched to the rule's material families. “Other” code 999 and its free-text entries stay unresolved. Missing is separately recorded, never treated as a material.\n\n## Combination feasibility and descriptive comparison\n\nThere are {all3:,} households with all three material responses present. Of these, {classifiable:,} ({classifiable/total*100:.2f}% of the master) match exactly one published combination row using only exact item mappings; see the feasibility CSV for every observed triad and limitation. No classification has been written back to source data. Frequencies in the frequency report show item-response denominators and all-master denominators explicitly.\n\n## Checks executed\n\n- Household key `hhcode`: unique and nonmissing in master and housing module.\n- Module keys are a subset of the household master; one-to-one `hhcode` merge validated.\n- Join preserved master row count and key order ({total:,}); all master records matched the housing module.\n- Item missingness, observed category coverage and response counts were calculated from cleaned module. Original BRIGHT responses were only read.\n- No household identifiers or row-level records are included in outputs.\n\n## Limitations and decisions for researcher\n\n- Local files did not include the Census report; official online DCS final report was used.\n- Census labels/categories are not fully equivalent to several BRIGHT options. Census material “Wood (finished)” is narrower than BRIGHT “Wood”; floor BRIGHT Teraso/Tile/Granite groups items across Census subcategories, which matters for rules specifying finished wood/titanium/concrete. Accordingly, status counts are conservative and may understate feasibility.\n- The report's extracted text presents no explicit precedence rule for any overlap or status for unlisted combinations. No gap filling or assumed hierarchy was used.\n- “Other” text was counted for distinct nonblank strings only, not reproduced, to avoid sharing respondent-provided text. Individual other text was not mapped.\n- These artifacts validate the crosswalk only. Researcher approval is still needed before deprivation coding, indicator inclusion, fuzzy membership, weights, or model implementation.\n'''
    (OUT/"housing_classification_audit.md").write_text(report,encoding="utf-8")
    print(f"Wrote validation artifacts. Households={total}; all three observed={all3}; classifiable by exact verified row={classifiable}.")

if __name__ == "__main__":
    OUT.mkdir(parents=True,exist_ok=True)
    main()
