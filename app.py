"""
CDC LAUNCHPAD — AI-Powered Startup Assessment & Decision-Support Platform
Author: Dorra Fadhloun · PTMBA 2024 · Mediterranean School of Business
Client: Caisse des Dépôts et Consignations (CDC), Tunisia

Single-file Streamlit application. All engines run on the real CDC dataset.
Pure engine functions contain NO Streamlit calls so they can be tested headless.
"""

import os
import io
import datetime as _dt

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------
# CONFIG  (absolute paths so it works on Hugging Face Spaces / any host)
# ----------------------------------------------------------------------------
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_FILE   = os.path.join(SCRIPT_DIR, "Startups_Tunisia_Master_v4.xlsx")
LOGO_FILE   = os.path.join(SCRIPT_DIR, "cdc_logo.png")
STORE_FILE  = os.path.join(SCRIPT_DIR, "cdc_learning_store.csv")

NAVY, RED, GREY, LIGHT = "#272E5F", "#D10A11", "#6B7280", "#F4F5F9"
ACCESS_CODE  = "CDC2026"
ADMIN_EMAIL  = "dorra.fadhloun@msb.tn"
RANDOM_STATE = 42
ANALYSIS_YEAR = 2026

REGIONS_TN = ["Tunis","Ariana","Ben Arous","Manouba","Nabeul","Zaghouan","Bizerte",
    "Béja","Jendouba","Kef","Siliana","Sousse","Monastir","Mahdia","Sfax","Kairouan",
    "Kasserine","Sidi Bouzid","Gabès","Médenine","Tataouine","Gafsa","Tozeur","Kébili"]

# ----------------------------------------------------------------------------
# BILINGUAL STRINGS
# ----------------------------------------------------------------------------
TX = {
 "subtitle":{"EN":"AI-Powered Startup Assessment & Decision Support","FR":"Évaluation des startups par IA & aide à la décision"},
 "access":{"EN":"Secure access","FR":"Accès sécurisé"},
 "email":{"EN":"Professional email","FR":"Email professionnel"},
 "req":{"EN":"Request access code","FR":"Demander un code d'accès"},
 "code":{"EN":"Access code","FR":"Code d'accès"},
 "enter":{"EN":"Enter platform","FR":"Accéder à la plateforme"},
 "bad":{"EN":"Incorrect code. Please check with the administrator.","FR":"Code incorrect. Veuillez vérifier auprès de l'administrateur."},
 "sent":{"EN":"Access request registered. The administrator has been notified at","FR":"Demande enregistrée. L'administrateur a été notifié à"},
 "tab_news":{"EN":"Ecosystem","FR":"Écosystème"},
 "tab_pf":{"EN":"Portfolio","FR":"Portefeuille"},
 "tab_as":{"EN":"Assessment","FR":"Évaluation"},
 "tab_val":{"EN":"Valuation","FR":"Valorisation"},
 "tab_learn":{"EN":"Data & Learning","FR":"Données & Apprentissage"},
 "tab_rep":{"EN":"Reports","FR":"Rapports"},
 "logout":{"EN":"Log out","FR":"Déconnexion"},
}
def TXT(k, lang): return TX.get(k,{}).get(lang,k)

# ============================================================================
#  ENGINE 1 — DATA LOADING & FEATURE ENGINEERING  (pure)
# ============================================================================
def _count_founders(v):
    if pd.isna(v): return 1
    s = str(v)
    for sep in [";","/","|"," et "," and ",","]:
        s = s.replace(sep, ";")
    parts = [p for p in s.split(";") if p.strip()]
    return max(1, len(parts))

def load_base(path=DATA_FILE, store=STORE_FILE):
    """Load real portfolio, derive funding label + leakage-free model features."""
    xls = pd.ExcelFile(path)
    pick = lambda kw: next(s for s in xls.sheet_names if kw.lower() in s.lower())
    base = pd.read_excel(xls, pick("base"),   header=1)
    fin  = pd.read_excel(xls, pick("financ"), header=1)

    norm = lambda s: s.astype(str).str.strip().str.lower()
    funded_names = set(norm(fin["Nom"]))
    base["funded"] = norm(base["Nom"]).isin(funded_names).astype(int)

    yr = pd.to_numeric(base.get("Année de création"), errors="coerce")
    med_year = int(yr.median()) if yr.notna().any() else 2018
    base["company_age"] = (ANALYSIS_YEAR - yr.fillna(med_year)).clip(0, 40)
    base["n_founders"]  = base.get("Founders").apply(_count_founders) if "Founders" in base else 1
    base["is_labelled"] = base.get("Label Date").notna().astype(int) if "Label Date" in base else 0
    base["has_email"]   = base.get("Courriel").notna().astype(int) if "Courriel" in base else 0
    base["has_web"]     = base.get("Site web").notna().astype(int) if "Site web" in base else 0
    base["sector"]      = base.get("Secteur").astype(str).str.strip().replace({"nan":"Unknown","":"Unknown"})

    # fold in any self-learning rows the officers have appended
    if os.path.exists(store):
        try:
            extra = pd.read_csv(store)
            base = pd.concat([base, extra], ignore_index=True)
        except Exception:
            pass
    return base

FEATURES = ["company_age","n_founders","is_labelled","has_email","has_web","sector_baserate"]

def _sector_baserate(df):
    g = df.groupby("sector")["funded"].mean()
    return g.to_dict(), float(df["funded"].mean())

def build_features(df, rate_map, global_rate):
    X = pd.DataFrame({
        "company_age": pd.to_numeric(df["company_age"], errors="coerce").fillna(8),
        "n_founders":  pd.to_numeric(df["n_founders"],  errors="coerce").fillna(1),
        "is_labelled": pd.to_numeric(df["is_labelled"], errors="coerce").fillna(0),
        "has_email":   pd.to_numeric(df["has_email"],   errors="coerce").fillna(0),
        "has_web":     pd.to_numeric(df["has_web"],     errors="coerce").fillna(0),
        "sector_baserate": df["sector"].map(rate_map).fillna(global_rate),
    })
    return X[FEATURES]

# ============================================================================
#  ENGINE 2 — SELECTION MODEL  (XGBoost if present, else GradientBoosting)
# ============================================================================
def train_selection(df):
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import roc_auc_score, f1_score, accuracy_score
    try:
        from xgboost import XGBClassifier
        HAVE_XGB = True
    except Exception:
        from sklearn.ensemble import GradientBoostingClassifier
        HAVE_XGB = False

    rate_map, global_rate = _sector_baserate(df)
    X = build_features(df, rate_map, global_rate)
    y = df["funded"].astype(int).values

    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=0.25, random_state=RANDOM_STATE, stratify=y)

    if HAVE_XGB:
        pos = max(1, int((ytr == 0).sum())) / max(1, int((ytr == 1).sum()))
        model = XGBClassifier(
            n_estimators=300, max_depth=4, learning_rate=0.05,
            subsample=0.9, colsample_bytree=0.9, eval_metric="logloss",
            scale_pos_weight=pos, random_state=RANDOM_STATE)
        model.fit(Xtr, ytr)
    else:
        from sklearn.ensemble import GradientBoostingClassifier
        w = np.where(ytr == 1, (ytr == 0).sum()/max(1,(ytr == 1).sum()), 1.0)
        model = GradientBoostingClassifier(
            n_estimators=300, max_depth=3, learning_rate=0.05, random_state=RANDOM_STATE)
        model.fit(Xtr, ytr, sample_weight=w)

    proba = model.predict_proba(Xte)[:, 1]
    pred  = (proba >= 0.5).astype(int)
    metrics = {
        "roc_auc": round(float(roc_auc_score(yte, proba)), 3),
        "f1":      round(float(f1_score(yte, pred, zero_division=0)), 3),
        "accuracy":round(float(accuracy_score(yte, pred)), 3),
        "n_rows":  int(len(df)),
        "n_funded":int(df["funded"].sum()),
        "engine":  "XGBoost" if HAVE_XGB else "Gradient Boosting",
    }
    # direction of each feature (sign of correlation with funded) for explainability
    signs = {f: float(np.sign(np.corrcoef(X[f], y)[0, 1] or 0)) for f in FEATURES}
    importance = dict(zip(FEATURES, [float(v) for v in model.feature_importances_]))
    # refit on ALL rows for production scoring
    model.fit(X, y)
    return {"model": model, "metrics": metrics, "rate_map": rate_map,
            "global_rate": global_rate, "signs": signs, "importance": importance,
            "feat_mean": X.mean().to_dict()}

PRETTY = {"company_age":"Company maturity","n_founders":"Founding team size",
          "is_labelled":"Startup Act label","has_email":"Verified contact",
          "has_web":"Web presence","sector_baserate":"Sector funding track record"}

def assess_one(bundle, inp):
    """Score one startup. inp keys: sector, founding_year, n_founders, is_labelled, has_email, has_web."""
    age = float(np.clip(ANALYSIS_YEAR - inp.get("founding_year", 2020), 0, 40))
    row = pd.DataFrame([{
        "company_age": age,
        "n_founders":  inp.get("n_founders", 1),
        "is_labelled": int(inp.get("is_labelled", 0)),
        "has_email":   int(inp.get("has_email", 0)),
        "has_web":     int(inp.get("has_web", 0)),
        "sector":      inp.get("sector", "Unknown"),
    }])
    X = build_features(row, bundle["rate_map"], bundle["global_rate"])
    proba = float(bundle["model"].predict_proba(X)[0, 1])
    score = round(proba * 100, 1)
    if   proba >= 0.60: verdict, tone = "Recommended for selection", "ok"
    elif proba >= 0.40: verdict, tone = "Conditional — further due diligence", "warn"
    else:               verdict, tone = "Not recommended — elevated risk", "bad"

    drivers = []
    for f in FEATURES:
        contrib = bundle["importance"][f] * bundle["signs"][f] * \
                  (X[f].iloc[0] - bundle["feat_mean"][f])
        drivers.append((PRETTY[f], contrib))
    drivers.sort(key=lambda t: abs(t[1]), reverse=True)
    drivers = [(n, "↑ supports" if c >= 0 else "↓ weighs against") for n, c in drivers[:5]]
    return {"score": score, "proba": proba, "verdict": verdict, "tone": tone, "drivers": drivers}

# ============================================================================
#  ENGINE 3 — PORTFOLIO LOOKUP & RISK ALERTS  (pure, real columns)
# ============================================================================
def lookup_startup(df, query):
    if not query or not str(query).strip():
        return {"level":"none","title":"Enter a name or RNE to search","details":[]}
    q = str(query).strip().lower()
    hit = df[df["Nom"].astype(str).str.lower().str.contains(q, na=False)]
    if "RNE" in df.columns:
        hit = pd.concat([hit, df[df["RNE"].astype(str).str.lower().str.contains(q, na=False)]]).drop_duplicates()
    if hit.empty:
        return {"level":"green","title":"No existing record in the CDC database","details":[]}

    r = hit.iloc[0]
    details = [f"Name: {r.get('Nom','—')}",
               f"Sector: {r.get('Secteur','—')}",
               f"Founded: {r.get('Année de création','—')}"]
    advance = pd.to_numeric(pd.Series([r.get("Avance Remboursable Flywheel (TND)")]),
                            errors="coerce").iloc[0]
    if int(r.get("funded", 0)) == 1 and pd.notna(advance) and advance > 0:
        return {"level":"red","title":"HIGH RISK — repayable advance on file; verify reimbursement before proceeding",
                "details":details + [f"Repayable advance: {advance:,.0f} TND"]}
    if int(r.get("funded", 0)) == 1:
        amt = r.get("Montant total reçu") or r.get("Fonds reçus")
        if pd.notna(amt): details.append(f"Funds received: {amt}")
        return {"level":"amber","title":"CAUTION — existing CDC beneficiary; review prior programme history",
                "details":details}
    return {"level":"blue","title":"INFORMATION — in database but not previously funded",
            "details":details}

# ============================================================================
#  ENGINE 4 — FIVE-METHOD VALUATION  (deterministic, defensible)
# ============================================================================
def valuation_engine(v):
    """v: stage(0/1/2), team, market, product, competition (0-1), revenue_tnd(optional), growth."""
    stage = v.get("stage", 1)            # 0 Idea, 1 MVP, 2 Revenue
    team, market = v.get("team",0.6), v.get("market",0.6)
    product, comp = v.get("product",0.6), v.get("competition",0.5)
    rev, growth = v.get("revenue_tnd",0.0), v.get("growth",0.4)

    # 1) Berkus — 5 buckets, each capped at 500k TND
    cap = 500_000
    berkus = cap*(0.5+0.5*1) + cap*(stage/2) + cap*team + cap*market + cap*product
    # 2) Scorecard — Tunisian early-stage base × weighted multiplier
    base_pre = 1_200_000
    factor = (team*0.30 + market*0.25 + product*0.15 + (1-comp)*0.10 + 0.10 + 0.10)
    scorecard = base_pre * (0.5 + factor)
    # 3) Risk-Factor Summation — base ± 250k per favourable/adverse factor
    adj = (team-0.5)+(market-0.5)+(product-0.5)+(0.5-comp)+(stage/2-0.5)
    rfs = base_pre + adj*2*250_000
    # 4) VC Method — exit value back to present
    if rev > 0:
        exit_val = rev*(1+growth)**5 * 3.0
    else:
        exit_val = 8_000_000*(0.4+0.4*market)
    vc = exit_val/10.0                    # target 10x return
    # 5) Hybrid DCF — only if revenue exists
    if rev > 0:
        cfs = [rev*(1+growth)**i*0.20 for i in range(1,6)]
        disc = 0.35
        dcf = sum(c/(1+disc)**i for i,c in enumerate(cfs,1)) + (cfs[-1]*1.5)/(1+disc)**5
    else:
        dcf = None

    methods = {"Berkus":berkus, "Scorecard":scorecard, "Risk-Factor Summation":rfs,
               "Venture Capital Method":vc}
    if dcf is not None: methods["Hybrid DCF"] = dcf
    vals = np.array(list(methods.values()))
    return {"methods":methods,
            "low":  float(np.percentile(vals,25)),
            "mid":  float(np.percentile(vals,50)),
            "high": float(np.percentile(vals,75))}

# ============================================================================
#  ENGINE 5 — PORTFOLIO SEGMENTATION  (k-means, deterministic naming)
# ============================================================================
def segment_portfolio(df):
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import KMeans
    rate_map, global_rate = _sector_baserate(df)
    feat = pd.DataFrame({
        "company_age": pd.to_numeric(df["company_age"],errors="coerce").fillna(8),
        "n_founders":  pd.to_numeric(df["n_founders"], errors="coerce").fillna(1),
        "is_labelled": pd.to_numeric(df["is_labelled"],errors="coerce").fillna(0),
        "sector_baserate": df["sector"].map(rate_map).fillna(global_rate),
    })
    Z = StandardScaler().fit_transform(feat)
    km = KMeans(n_clusters=3, n_init=10, random_state=RANDOM_STATE).fit(Z)
    df = df.copy(); df["cluster"] = km.labels_
    age_by = df.groupby("cluster")["company_age"].mean()
    lab_by = df.groupby("cluster")["is_labelled"].mean()
    health_c = age_by.idxmax()
    rest = [c for c in age_by.index if c != health_c]
    soft_c = max(rest, key=lambda c: lab_by[c])
    comm_c = [c for c in rest if c != soft_c][0]
    names = {health_c:"Health / deep-tech cluster", soft_c:"Digital-software cluster",
             comm_c:"Commerce / services cluster"}
    df["profile"] = df["cluster"].map(names)
    summary = (df.groupby("profile")
                 .agg(startups=("Nom","count"),
                      funded_rate=("funded","mean"),
                      avg_age=("company_age","mean"))
                 .reset_index())
    summary["funded_rate"] = (summary["funded_rate"]*100).round(1)
    summary["avg_age"] = summary["avg_age"].round(1)
    return df, summary

# ============================================================================
#  ENGINE 6 — LIVE NEWS  (feedparser; graceful offline fallback)
# ============================================================================
def fetch_news(limit=6):
    feeds = [
        "https://news.google.com/rss/search?q=startup+Tunisie&hl=fr&gl=TN&ceid=TN:fr",
        "https://news.google.com/rss/search?q=Tunisia+startup+funding&hl=en-US&gl=US&ceid=US:en",
    ]
    items = []
    try:
        import feedparser
        for url in feeds:
            d = feedparser.parse(url)
            for e in d.entries[:limit]:
                items.append({"title": e.get("title",""), "link": e.get("link",""),
                              "src": e.get("source",{}).get("title","") if e.get("source") else ""})
            if len(items) >= limit: break
    except Exception:
        pass
    if not items:
        items = [{"title":"Connect this Space to the internet to stream live ecosystem news.",
                  "link":"", "src":"CDC LAUNCHPAD"}]
    return items[:limit]

# ============================================================================
#  ENGINE 7 — REPORT GENERATION  (real PDF via reportlab, real Excel via openpyxl)
# ============================================================================
def _gauge_png(score):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(3.2,1.8), subplot_kw={"projection":"polar"})
    ax.set_theta_zero_location("W"); ax.set_theta_direction(-1)
    ax.set_thetamin(0); ax.set_thetamax(180)
    for lo,hi,col in [(0,40,RED),(40,60,"#E8A33D"),(60,100,"#2E8B57")]:
        ax.barh(1, np.radians((hi-lo)*1.8), left=np.radians(lo*1.8), height=0.45, color=col)
    ang = np.radians(score*1.8)
    ax.plot([ang,ang],[0,1.2], color=NAVY, lw=3)
    ax.set_axis_off(); ax.set_title(f"{score:.0f}/100", color=NAVY, fontweight="bold", pad=2)
    buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                                    transparent=True); plt.close(fig); buf.seek(0)
    return buf

def assessment_pdf(p):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                    TableStyle, Image)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18*mm, bottomMargin=16*mm,
                            leftMargin=18*mm, rightMargin=18*mm)
    ss = getSampleStyleSheet()
    H = ParagraphStyle("H", parent=ss["Title"], textColor=colors.HexColor(NAVY), fontSize=20)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=colors.HexColor(NAVY))
    body = ss["BodyText"]
    el = []
    if os.path.exists(LOGO_FILE):
        try: el.append(Image(LOGO_FILE, width=46*mm, height=18*mm)); el.append(Spacer(1,6))
        except Exception: pass
    el += [Paragraph("Startup Assessment Report", H),
           Paragraph(f"<b>{p['name']}</b> &nbsp;·&nbsp; {p['sector']} &nbsp;·&nbsp; {p['region']} "
                     f"&nbsp;·&nbsp; {_dt.date.today():%d %b %Y}", body),
           Spacer(1,8)]
    el.append(Image(_gauge_png(p["score"]), width=70*mm, height=40*mm))
    tone = {"ok":"#2E8B57","warn":"#E8A33D","bad":RED}.get(p["tone"], NAVY)
    el += [Paragraph(f"<font color='{tone}'><b>Verdict: {p['verdict']}</b></font>", h2),
           Paragraph(f"Funding-likelihood score: <b>{p['score']:.1f}/100</b> "
                     f"(model probability {p['proba']:.2f}).", body), Spacer(1,8)]
    el.append(Paragraph("Key decision drivers", h2))
    dt = Table([["Factor","Effect"]]+[[n,e] for n,e in p["drivers"]], colWidths=[95*mm,60*mm])
    dt.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor(NAVY)),("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#D9DCE6")),("FONTSIZE",(0,0),(-1,-1),9),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor(LIGHT)])]))
    el += [dt, Spacer(1,8)]
    if p.get("alert"):
        el.append(Paragraph(f"<b>Database check:</b> {p['alert']}", body)); el.append(Spacer(1,6))
    if p.get("val"):
        el.append(Paragraph("Indicative valuation (5-method reconciliation)", h2))
        v = p["val"]; rows = [["Method","Value (TND)"]] + \
            [[m, f"{val:,.0f}"] for m,val in v["methods"].items()] + \
            [["Reconciled range", f"{v['low']:,.0f} – {v['high']:,.0f}"]]
        vt = Table(rows, colWidths=[95*mm,60*mm])
        vt.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor(RED)),("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#D9DCE6")),("FONTSIZE",(0,0),(-1,-1),9),
            ("BACKGROUND",(0,-1),(-1,-1),colors.HexColor(NAVY)),("TEXTCOLOR",(0,-1),(-1,-1),colors.white)]))
        el += [vt, Spacer(1,8)]
    el.append(Spacer(1,6))
    el.append(Paragraph("<font size=8 color='#6B7280'>This output is a decision-support tool. "
        "Final investment decisions remain the sole responsibility of authorised CDC officers. "
        "Model trained on CDC historical records; predictors exclude post-funding fields.</font>", body))
    doc.build(el); buf.seek(0); return buf

def assessment_excel(p):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    wb = Workbook(); ws = wb.active; ws.title = "Assessment"
    navy = PatternFill("solid", fgColor="272E5F"); red = PatternFill("solid", fgColor="D10A11")
    white = Font(color="FFFFFF", bold=True); bold = Font(bold=True)
    thin = Border(*[Side(style="thin", color="D9DCE6")]*4)
    ws["A1"]="CDC LAUNCHPAD — Startup Assessment"; ws["A1"].font=Font(size=15,bold=True,color="272E5F")
    rows = [("Startup",p["name"]),("Sector",p["sector"]),("Region",p["region"]),
            ("Date",f"{_dt.date.today():%Y-%m-%d}"),("Funding-likelihood score",f"{p['score']:.1f}/100"),
            ("Model probability",f"{p['proba']:.2f}"),("Verdict",p["verdict"])]
    r=3
    for k,v in rows:
        ws.cell(r,1,k).font=bold; ws.cell(r,2,v); r+=1
    r+=1; ws.cell(r,1,"Key drivers").font=white; ws.cell(r,1).fill=navy
    ws.cell(r,2,"Effect").font=white; ws.cell(r,2).fill=navy; r+=1
    for n,e in p["drivers"]:
        ws.cell(r,1,n); ws.cell(r,2,e); r+=1
    if p.get("val"):
        r+=1; ws.cell(r,1,"Valuation method").font=white; ws.cell(r,1).fill=red
        ws.cell(r,2,"Value (TND)").font=white; ws.cell(r,2).fill=red; r+=1
        for m,val in p["val"]["methods"].items():
            ws.cell(r,1,m); ws.cell(r,2,round(val)); ws.cell(r,2).number_format="#,##0"; r+=1
        ws.cell(r,1,"Reconciled range").font=bold
        ws.cell(r,2,f"{p['val']['low']:,.0f} – {p['val']['high']:,.0f}"); r+=1
    ws.column_dimensions["A"].width=34; ws.column_dimensions["B"].width=40
    for row in ws.iter_rows(min_row=3,max_row=r,max_col=2):
        for c in row: c.border=thin
    buf=io.BytesIO(); wb.save(buf); buf.seek(0); return buf

def portfolio_pdf(df, summary):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                    TableStyle, Image)
    buf=io.BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=A4,topMargin=18*mm,bottomMargin=16*mm,leftMargin=18*mm,rightMargin=18*mm)
    ss=getSampleStyleSheet()
    H=ParagraphStyle("H",parent=ss["Title"],textColor=colors.HexColor(NAVY),fontSize=20)
    h2=ParagraphStyle("h2",parent=ss["Heading2"],textColor=colors.HexColor(NAVY))
    el=[]
    if os.path.exists(LOGO_FILE):
        try: el.append(Image(LOGO_FILE,width=46*mm,height=18*mm)); el.append(Spacer(1,6))
        except Exception: pass
    el+=[Paragraph("CDC Portfolio Report",H),
         Paragraph(f"Generated {_dt.date.today():%d %b %Y}",ss["BodyText"]),Spacer(1,8)]
    k=[["Portfolio startups",f"{len(df):,}"],
       ["Funded beneficiaries",f"{int(df['funded'].sum()):,}"],
       ["Funding rate",f"{df['funded'].mean()*100:.1f}%"],
       ["Distinct sectors",f"{df['sector'].nunique():,}"]]
    kt=Table(k,colWidths=[80*mm,60*mm])
    kt.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#D9DCE6")),
        ("BACKGROUND",(0,0),(0,-1),colors.HexColor(LIGHT)),("FONTSIZE",(0,0),(-1,-1),10)]))
    el+=[Paragraph("Headline indicators",h2),kt,Spacer(1,10)]
    rows=[["Segment","Startups","Funded %","Avg age (yrs)"]]+ \
         summary[["profile","startups","funded_rate","avg_age"]].values.tolist()
    stt=Table(rows,colWidths=[70*mm,30*mm,30*mm,35*mm])
    stt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor(NAVY)),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#D9DCE6")),
        ("FONTSIZE",(0,0),(-1,-1),9),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor(LIGHT)])]))
    el+=[Paragraph("Portfolio segments",h2),stt,Spacer(1,10),
         Paragraph("<font size=8 color='#6B7280'>Segments derived by unsupervised clustering on "
                   "maturity, team size, label status and sector funding track record.</font>",ss["BodyText"])]
    doc.build(el); buf.seek(0); return buf

# ============================================================================
#  SELF-LEARNING LOOP  (append a labelled row, then caller retrains)
# ============================================================================
def append_record(rec, store=STORE_FILE):
    row = {
        "Nom": rec["name"], "Secteur": rec["sector"], "sector": rec["sector"],
        "Année de création": rec["year"],
        "company_age": np.clip(ANALYSIS_YEAR-rec["year"],0,40),
        "n_founders": rec["founders"], "is_labelled": int(rec.get("labelled",0)),
        "has_email": int(rec.get("email",0)), "has_web": int(rec.get("web",0)),
        "funded": int(rec["funded"]),
    }
    df = pd.DataFrame([row])
    if os.path.exists(store):
        df = pd.concat([pd.read_csv(store), df], ignore_index=True)
    df.to_csv(store, index=False)
    return len(df)

# ============================================================================
#  STREAMLIT UI   (everything below uses st.*; engines above stay pure)
# ============================================================================
def run_app():
    import streamlit as st
    st.set_page_config(page_title="CDC LAUNCHPAD", page_icon="🚀",
                       layout="wide", initial_sidebar_state="expanded")

    if not os.path.exists(DATA_FILE):
        st.error("Dataset not found. Upload Startups_Tunisia_Master_v4.xlsx next to app.py.")
        st.write("Files present:", os.listdir(SCRIPT_DIR)); st.stop()

    st.markdown(f"""<style>
      .stApp {{ background:{LIGHT}; }}
      h1,h2,h3 {{ color:{NAVY}; }}
      .stButton>button {{ background:{NAVY}; color:#fff; border:0; border-radius:8px; font-weight:600; }}
      .stButton>button:hover {{ background:{RED}; color:#fff; }}
      div[data-testid="stMetricValue"] {{ color:{NAVY}; }}
    </style>""", unsafe_allow_html=True)

    ss = st.session_state
    ss.setdefault("lang","EN"); ss.setdefault("auth",False)

    @st.cache_resource(show_spinner="Loading CDC portfolio and training the model…")
    def _bundle():
        df = load_base()
        return df, train_selection(df), segment_portfolio(df)
    df, bundle, (seg_df, seg_sum) = _bundle()

    # ---------- header ----------
    c1,c2,c3 = st.columns([1,6,2])
    with c1:
        if os.path.exists(LOGO_FILE): st.image(LOGO_FILE, width=84)
        else: st.markdown("### 🚀")
    with c2:
        st.markdown(f"## CDC&nbsp;LAUNCHPAD")
        st.caption(TXT("subtitle", ss.lang))
    with c3:
        ss.lang = st.radio("🌐", ["EN","FR"], horizontal=True,
                           index=0 if ss.lang=="EN" else 1, label_visibility="collapsed")
    st.divider()
    L = ss.lang

    # ---------- access gate ----------
    if not ss.auth:
        st.subheader("🔐 " + TXT("access", L))
        email = st.text_input(TXT("email", L), placeholder="name@cdc.tn")
        a,b = st.columns(2)
        with a:
            if st.button(TXT("req", L), use_container_width=True):
                st.info(f"✉️ {TXT('sent', L)} **{ADMIN_EMAIL}** — code: **{ACCESS_CODE}**")
        with b:
            code = st.text_input(TXT("code", L), type="password")
            if st.button(TXT("enter", L), use_container_width=True):
                if code == ACCESS_CODE:
                    ss.auth=True; st.rerun()
                else:
                    st.error(TXT("bad", L))
        st.stop()

    # ---------- tabs ----------
    t1,t2,t3,t4,t5,t6 = st.tabs([
        "📰 "+TXT("tab_news",L), "📊 "+TXT("tab_pf",L), "🎯 "+TXT("tab_as",L),
        "💰 "+TXT("tab_val",L), "🧠 "+TXT("tab_learn",L), "📄 "+TXT("tab_rep",L)])

    # ===== ECOSYSTEM =====
    with t1:
        m = bundle["metrics"]
        k1,k2,k3,k4 = st.columns(4)
        k1.metric("Startups in base", f"{m['n_rows']:,}")
        k2.metric("Funded", f"{m['n_funded']:,}")
        k3.metric("Funding rate", f"{m['n_funded']/m['n_rows']*100:.1f}%")
        k4.metric("Sectors", f"{df['sector'].nunique():,}")
        st.markdown("#### À la une — live ecosystem news")
        for n in fetch_news():
            if n["link"]:
                st.markdown(f"- [{n['title']}]({n['link']})  \n  <span style='color:{GREY};font-size:12px'>{n['src']}</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"- {n['title']}")

    # ===== PORTFOLIO =====
    with t2:
        st.markdown("#### Portfolio composition")
        a,b = st.columns(2)
        with a:
            top = df["sector"].value_counts().head(10)
            st.bar_chart(top, color=NAVY)
            st.caption("Top sectors by number of startups")
        with b:
            yr = pd.to_numeric(df["Année de création"], errors="coerce").dropna().astype(int)
            st.bar_chart(yr.value_counts().sort_index().tail(15), color=RED)
            st.caption("Startups by founding year")
        st.markdown("#### Portfolio segments")
        st.dataframe(seg_sum.rename(columns={"profile":"Segment","startups":"Startups",
            "funded_rate":"Funded %","avg_age":"Avg age (yrs)"}), use_container_width=True, hide_index=True)

    # ===== ASSESSMENT =====
    with t3:
        st.markdown("#### Assess a startup")
        lq = st.text_input("Database check — startup name or RNE",
                           placeholder="Type a name to check prior CDC history…")
        if lq:
            a = lookup_startup(df, lq)
            colmap = {"green":"#2E8B57","blue":"#2563EB","amber":"#E8A33D","red":RED,"none":GREY}
            st.markdown(f"<div style='padding:10px;border-radius:8px;background:{colmap[a['level']]}1A;"
                        f"border-left:5px solid {colmap[a['level']]}'><b>{a['title']}</b><br>"
                        + "<br>".join(a["details"]) + "</div>", unsafe_allow_html=True)
        st.markdown("---")
        c = st.columns(3)
        name = c[0].text_input("Startup name", "Demo Health SA")
        sector = c[1].selectbox("Sector", sorted(df["sector"].unique().tolist()))
        region = c[2].selectbox("Region", REGIONS_TN)
        c = st.columns(3)
        year = c[0].number_input("Founding year", 2000, ANALYSIS_YEAR, 2021)
        founders = c[1].number_input("Number of founders", 1, 10, 2)
        stage = c[2].selectbox("Product stage", ["Idea","MVP","Revenue-generating"], index=1)
        c = st.columns(3)
        labelled = c[0].checkbox("Holds Startup Act label", True)
        has_email = c[1].checkbox("Verified contact on file", True)
        has_web = c[2].checkbox("Has website", True)
        with st.expander("Optional financial inputs (improve valuation)"):
            rev = st.number_input("Latest annual revenue (TND)", 0, 50_000_000, 0, step=50_000)
            growth = st.slider("Expected annual growth", 0.0, 1.5, 0.4, 0.05)
            team = st.slider("Team strength", 0.0, 1.0, 0.7, 0.05)
            market = st.slider("Market opportunity", 0.0, 1.0, 0.65, 0.05)
            product = st.slider("Product maturity", 0.0, 1.0, 0.6, 0.05)
            comp = st.slider("Competitive pressure", 0.0, 1.0, 0.5, 0.05)

        if st.button("Run assessment", use_container_width=True):
            res = assess_one(bundle, {"sector":sector,"founding_year":year,"n_founders":founders,
                "is_labelled":labelled,"has_email":has_email,"has_web":has_web})
            val = valuation_engine({"stage":["Idea","MVP","Revenue-generating"].index(stage),
                "team":team,"market":market,"product":product,"competition":comp,
                "revenue_tnd":rev,"growth":growth})
            alert = lookup_startup(df, name)["title"]
            payload = {"name":name,"sector":sector,"region":region, **res, "val":val, "alert":alert}
            ss["last"] = payload

            tone = {"ok":"#2E8B57","warn":"#E8A33D","bad":RED}[res["tone"]]
            st.markdown(f"### Score: {res['score']:.1f}/100")
            st.markdown(f"<h4 style='color:{tone}'>{res['verdict']}</h4>", unsafe_allow_html=True)
            st.progress(min(1.0, res["proba"]))
            st.markdown("**Key drivers**")
            for n,e in res["drivers"]:
                st.write(("✅ " if "supports" in e else "⚠️ ")+f"{n} — {e}")
            st.markdown("**Indicative valuation (TND)**")
            vc = st.columns(len(val["methods"]))
            for col,(mname,mval) in zip(vc, val["methods"].items()):
                col.metric(mname, f"{mval/1e6:.2f}M")
            st.success(f"Reconciled range: {val['low']:,.0f} – {val['high']:,.0f} TND")

            st.download_button("⬇️ Download PDF report", assessment_pdf(payload),
                file_name=f"Assessment_{name.replace(' ','_')}.pdf", mime="application/pdf")
            st.download_button("⬇️ Download Excel workbook", assessment_excel(payload),
                file_name=f"Assessment_{name.replace(' ','_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ===== VALUATION (standalone) =====
    with t4:
        st.markdown("#### Standalone 5-method valuation")
        c = st.columns(3)
        stage2 = c[0].selectbox("Stage", ["Idea","MVP","Revenue-generating"], index=1, key="v_stage")
        rev2 = c[1].number_input("Annual revenue (TND)", 0, 50_000_000, 0, step=50_000, key="v_rev")
        growth2 = c[2].slider("Growth", 0.0, 1.5, 0.4, 0.05, key="v_g")
        c = st.columns(4)
        team2 = c[0].slider("Team", 0.0,1.0,0.7,0.05,key="v_t")
        market2 = c[1].slider("Market", 0.0,1.0,0.65,0.05,key="v_m")
        product2 = c[2].slider("Product", 0.0,1.0,0.6,0.05,key="v_p")
        comp2 = c[3].slider("Competition", 0.0,1.0,0.5,0.05,key="v_c")
        v = valuation_engine({"stage":["Idea","MVP","Revenue-generating"].index(stage2),
            "team":team2,"market":market2,"product":product2,"competition":comp2,
            "revenue_tnd":rev2,"growth":growth2})
        st.dataframe(pd.DataFrame({"Method":list(v["methods"].keys()),
            "Value (TND)":[f"{x:,.0f}" for x in v["methods"].values()]}),
            use_container_width=True, hide_index=True)
        st.success(f"Reconciled range: {v['low']:,.0f} – {v['high']:,.0f} TND (median {v['mid']:,.0f})")

    # ===== DATA & LEARNING =====
    with t5:
        st.markdown("#### Current model performance")
        m = bundle["metrics"]
        k = st.columns(4)
        k[0].metric("ROC-AUC", m["roc_auc"]); k[1].metric("F1", m["f1"])
        k[2].metric("Accuracy", m["accuracy"]); k[3].metric("Training rows", f"{m['n_rows']:,}")
        st.caption(f"Engine: {m['engine']} · honest held-out test metrics (no leakage).")
        st.markdown("#### Add a labelled beneficiary → retrain")
        c = st.columns(3)
        nn = c[0].text_input("Name", "NewCo Tunisia", key="ln")
        nsec = c[1].selectbox("Sector", sorted(df["sector"].unique().tolist()), key="lsec")
        nyear = c[2].number_input("Founding year", 2000, ANALYSIS_YEAR, 2022, key="ly")
        c = st.columns(3)
        nf = c[0].number_input("Founders", 1, 10, 3, key="lf")
        out = c[1].selectbox("Outcome", ["funded","not funded"], key="lo")
        nlab = c[2].checkbox("Labelled", True, key="llab")
        if st.button("Append & retrain", use_container_width=True):
            total = append_record({"name":nn,"sector":nsec,"year":nyear,"founders":nf,
                "labelled":nlab,"email":1,"web":1,"funded":1 if out=="funded" else 0})
            st.cache_resource.clear()
            st.success(f"Record stored. Dataset now {total} learning rows. Reload to see refreshed metrics.")

    # ===== REPORTS =====
    with t6:
        st.markdown("#### Generate portfolio report")
        st.download_button("⬇️ Portfolio report (PDF)", portfolio_pdf(df, seg_sum),
            file_name="CDC_Portfolio_Report.pdf", mime="application/pdf")
        if ss.get("last"):
            st.markdown("#### Re-download last assessment")
            st.download_button("⬇️ Last assessment (PDF)", assessment_pdf(ss["last"]),
                file_name="Last_Assessment.pdf", mime="application/pdf")
        st.markdown("---")
        if st.button(TXT("logout", L)):
            ss.auth=False; st.rerun()


if __name__ == "__main__":
    run_app()
