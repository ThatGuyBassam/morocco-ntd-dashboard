"""
app.py — Morocco NTD Dashboard
===============================
Interactive epidemiological map of Neglected Tropical Diseases
across Morocco's 12 administrative regions (post-2015 reform).

Run:
    streamlit run app.py

Requirements:
    pip install streamlit pandas folium streamlit-folium

Also required in this folder (copy from pyGeno_Scouter):
    pygeno_query.py
    clinvar.py
"""

import os, json, sys, copy, subprocess
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

sys.path.insert(0, os.path.dirname(__file__))
from data.ntd_data import (
    DISEASES, POPULATION, REGION_NAMES, REGION_NAMES_FR,
    PHYSICIAN_DENSITY, NATIONAL_POPULATION, T
)

# ─── CONFIG ──────────────────────────────────────────────────────────────────

GEOJSON_PATH  = os.path.join(os.path.dirname(__file__), "data", "Morocco-Regions.geojson")
PYGENO_PYTHON = r"C:\Users\GAMER\miniconda3\envs\pygeno_env\python.exe"
PYGENO_SCRIPT = os.path.join(os.path.dirname(__file__), "pygeno_query.py")
GENOME_BUILD  = "GRCh38.78"

# ClinVar — import if available (requires clinvar.py copied from pyGeno_Scouter)
try:
    from clinvar import fetch_clinvar_variants, clinvar_url
    CLINVAR_AVAILABLE = True
except ImportError:
    CLINVAR_AVAILABLE = False

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Morocco NTD Dashboard",
    page_icon="🗺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── SESSION STATE ────────────────────────────────────────────────────────────

if "lang"               not in st.session_state: st.session_state.lang               = "en"
if "selected_disease"   not in st.session_state: st.session_state.selected_disease   = "cutaneous_leish"
if "selected_region"    not in st.session_state: st.session_state.selected_region    = None
if "selected_gene"      not in st.session_state: st.session_state.selected_gene      = None
if "show_gene_explorer" not in st.session_state: st.session_state.show_gene_explorer = False

def t(key): return T[st.session_state.lang][key]
def rname(idx): return REGION_NAMES_FR[idx] if st.session_state.lang == "fr" else REGION_NAMES[idx]

# ─── CSS ─────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
*,*::before,*::after{box-sizing:border-box;}
html,body,.stApp{background-color:#0d0f14!important;color:#c8cfe0!important;font-family:'IBM Plex Sans',sans-serif!important;}
.block-container{padding:2rem 2.5rem!important;max-width:1280px!important;}
#MainMenu,footer,.stDeployButton{display:none!important;}
[data-testid="stSidebar"]{background-color:#0a0c10!important;border-right:1px solid #1e2230!important;}
[data-testid="stSidebar"] *{color:#8090a8!important;font-family:'IBM Plex Sans',sans-serif!important;font-size:13px!important;}
[data-testid="stSidebar"] h2{color:#c8cfe0!important;font-size:15px!important;font-weight:600!important;}
[data-testid="stSidebar"] .stSuccess{background:#0f1f10!important;border:1px solid #1e3a20!important;color:#4a9e5c!important;border-radius:6px!important;font-size:12px!important;}
h1{font-family:'IBM Plex Mono',monospace!important;font-size:24px!important;font-weight:600!important;color:#e8eeff!important;letter-spacing:-0.01em!important;}
[data-testid="stTabs"] [data-baseweb="tab-list"]{background:transparent!important;border-bottom:1px solid #1e2438!important;gap:0!important;}
[data-testid="stTabs"] [data-baseweb="tab"]{background:transparent!important;color:#5060a0!important;font-family:'IBM Plex Sans',sans-serif!important;font-size:13px!important;font-weight:500!important;padding:8px 16px!important;border-bottom:2px solid transparent!important;}
[data-testid="stTabs"] [aria-selected="true"]{color:#8090e0!important;border-bottom-color:#4a6cf7!important;}
[data-testid="stTabs"] [data-baseweb="tab-panel"]{background:transparent!important;padding:16px 0!important;}
[data-testid="stMetric"]{background:#131720!important;border:1px solid #1e2438!important;border-radius:8px!important;padding:12px 16px!important;}
[data-testid="stMetricLabel"]{color:#506080!important;font-family:'IBM Plex Mono',monospace!important;font-size:10px!important;text-transform:uppercase!important;letter-spacing:0.06em!important;}
[data-testid="stMetricValue"]{color:#c8cfe0!important;font-family:'IBM Plex Mono',monospace!important;font-size:20px!important;font-weight:600!important;}
[data-testid="stButton"] button{background:#1a1f30!important;border:1px solid #2a3050!important;border-radius:8px!important;color:#8090b8!important;font-family:'IBM Plex Sans',sans-serif!important;width:100%!important;text-align:left!important;padding:10px 14px!important;transition:background 0.15s!important;}
[data-testid="stButton"] button:hover{background:#1e2540!important;border-color:#4a6cf7!important;}
[data-testid="stExpander"]{background:#111420!important;border:1px solid #1e2438!important;border-radius:10px!important;margin:4px 0!important;}
[data-testid="stExpander"] summary{background:#111420!important;color:#c8cfe0!important;font-family:'IBM Plex Sans',sans-serif!important;font-size:13px!important;padding:12px 16px!important;}
[data-testid="stExpander"] > div > div{background:#0e1118!important;padding:14px 16px!important;}
[data-testid="stDataFrame"]{border:1px solid #1e2438!important;border-radius:8px!important;}
.section-label{font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:600;letter-spacing:0.12em;color:#3a4868;text-transform:uppercase;margin:14px 0 6px 0;}
.stat-card{background:#111420;border:1px solid #1e2438;border-radius:10px;padding:14px 16px;margin:5px 0;}
.stat-val{font-family:'IBM Plex Mono',monospace;font-size:22px;font-weight:600;color:#c8cfe0;}
.stat-lbl{font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:0.1em;color:#3a4868;text-transform:uppercase;margin-bottom:4px;}
.stat-sub{font-size:11px;color:#506080;margin-top:4px;}
.trend-up{color:#c06060;}
.trend-down{color:#4a9e6a;}
.gene-chip{display:inline-block;background:#141c38;color:#7090e8;border:1px solid #2a3870;border-radius:20px;padding:3px 10px;margin:2px;font-size:11px;font-weight:600;font-family:'IBM Plex Mono',monospace;cursor:pointer;}
.gene-chip-active{display:inline-block;background:#1e2a5a;color:#a0c0ff;border:2px solid #4a6cf7;border-radius:20px;padding:3px 10px;margin:2px;font-size:11px;font-weight:600;font-family:'IBM Plex Mono',monospace;}
.scouter-btn{display:block;background:#0e1525;border:1px solid #4a6cf7;border-radius:8px;padding:12px 16px;color:#4a6cf7;font-size:13px;font-weight:600;text-decoration:none;text-align:center;margin-top:10px;transition:background 0.15s;}
.scouter-btn:hover{background:#141c38;color:#7090e8;}
.source-box{background:#0a0c10;border:1px solid #1e2230;border-radius:8px;padding:10px 14px;font-size:11px;color:#3a4868;font-family:'IBM Plex Mono',monospace;margin-top:8px;line-height:1.7;}
.warning-box{background:#1a1408;border:1px solid #3a2800;border-radius:8px;padding:10px 14px;font-size:11px;color:#8a6020;margin-top:6px;line-height:1.6;}
.confirmed-box{background:#0a1408;border:1px solid #1e3a18;border-radius:8px;padding:10px 14px;font-size:11px;color:#4a9e5a;margin-top:6px;}
.region-detail{background:#0e1220;border:1px solid #2a3870;border-left:3px solid #4a6cf7;border-radius:0 10px 10px 0;padding:18px 20px;margin-top:10px;}
.region-row{display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid #1a1e2e;font-size:12px;color:#8090a8;}
.region-row .rname{color:#a0b0c8;}
.region-row .rval{font-family:'IBM Plex Mono',monospace;color:#7090e8;}
.divider{border:none;border-top:1px solid #1a1e2e;margin:12px 0;}
.genomic-pos{display:inline-block;font-family:'IBM Plex Mono',monospace;font-size:12px;color:#c08040;background:#1a1408;border:1px solid #2a2010;border-radius:6px;padding:5px 12px;margin:6px 0;}
.clinvar-row{background:#0e1118;border:1px solid #1e2438;border-radius:8px;padding:10px 14px;margin:5px 0;font-size:12px;color:#a0b0d0;}
.badge-pathogenic{display:inline-block;background:#1a0f0f;color:#c06060;border:1px solid #3a1818;border-radius:4px;padding:1px 7px;font-size:10px;font-family:'IBM Plex Mono',monospace;}
.badge-likely{display:inline-block;background:#1a150f;color:#c09060;border:1px solid #3a2818;border-radius:4px;padding:1px 7px;font-size:10px;font-family:'IBM Plex Mono',monospace;}
</style>
""", unsafe_allow_html=True)

# ─── MAP HELPERS ─────────────────────────────────────────────────────────────

@st.cache_data
def load_geojson():
    with open(GEOJSON_PATH, encoding="utf-8") as f:
        return json.load(f)


def value_to_hex(val, vmin, vmax):
    """Map a value to YlOrRd hex color."""
    if val == 0 or vmax == vmin:
        return "#1a1e2e"
    ratio = min(1.0, max(0.0, (val - vmin) / (vmax - vmin)))
    stops = [
        (0.00, (255, 255, 204)),
        (0.25, (254, 217, 118)),
        (0.50, (253, 141,  60)),
        (0.75, (240,  59,  32)),
        (1.00, (189,   0,  38)),
    ]
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t0 <= ratio <= t1:
            f = (ratio - t0) / (t1 - t0)
            r = int(c0[0] + f * (c1[0] - c0[0]))
            g = int(c0[1] + f * (c1[1] - c0[1]))
            b = int(c0[2] + f * (c1[2] - c0[2]))
            return f"#{r:02x}{g:02x}{b:02x}"
    return "#bd0026"


def density_to_hex(val):
    """RdYlGn for physician density."""
    thresh = PHYSICIAN_DENSITY["who_threshold"]
    if val >= thresh:
        ratio = min(1.0, (val - thresh) / (3.5 - thresh))
        r = int(44  + ratio * (0  - 44))
        g = int(160 + ratio * (104 - 160))
        b = int(44  + ratio * (55  - 44))
    else:
        ratio = 1.0 - (val / thresh)
        r = int(215 + ratio * (40  - 215))
        g = int(48  + ratio * (26  - 48))
        b = int(31  + ratio * (44  - 31))
    return f"#{max(0,min(255,r)):02x}{max(0,min(255,g)):02x}{max(0,min(255,b)):02x}"


def point_in_polygon(lat, lon, ring):
    """Ray-casting point-in-polygon test."""
    x, y = lon, lat
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def find_region_by_click(lat, lon, geojson):
    """Return region Indice for a clicked lat/lon."""
    for feat in geojson["features"]:
        idx  = feat["properties"]["Indice"]
        geom = feat["geometry"]
        try:
            if geom["type"] == "Polygon":
                if point_in_polygon(lat, lon, geom["coordinates"][0]):
                    return idx
            elif geom["type"] == "MultiPolygon":
                for poly in geom["coordinates"]:
                    if point_in_polygon(lat, lon, poly[0]):
                        return idx
        except Exception:
            continue
    return None


def centroid(feat):
    """Approximate centroid of a GeoJSON feature."""
    geom = feat["geometry"]
    try:
        if geom["type"] == "Polygon":
            pts = geom["coordinates"][0]
        else:
            pts = max(geom["coordinates"], key=lambda p: len(p[0]))[0]
        lats = [p[1] for p in pts]
        lons = [p[0] for p in pts]
        return (min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2
    except Exception:
        return None, None


def build_map(geojson, values_by_indice, tooltip_label, year):
    """Single GeoJson layer — handles color, hover, click."""
    vmin = min((v for v in values_by_indice.values() if v > 0), default=0)
    vmax = max(values_by_indice.values(), default=1)

    geo = copy.deepcopy(geojson)
    for feat in geo["features"]:
        idx  = feat["properties"]["Indice"]
        val  = values_by_indice.get(idx, 0)
        feat["properties"]["_val"]  = val
        feat["properties"]["_name"] = REGION_NAMES.get(idx, "")
        feat["properties"]["_pop"]  = f"{POPULATION.get(idx, 0):,}"
        feat["properties"]["_hex"]  = value_to_hex(val, vmin, vmax)

    m = folium.Map(
        location=[29.5, -7.5],
        zoom_start=5,
        tiles="CartoDB dark_matter",
        prefer_canvas=True,
    )

    folium.GeoJson(
        geo,
        style_function=lambda feat: {
            "fillColor":   feat["properties"]["_hex"],
            "fillOpacity": 0.82,
            "color":       "#c8cfe0",
            "weight":      1.2,
        },
        highlight_function=lambda feat: {
            "fillColor":   "#4a6cf7",
            "fillOpacity": 0.55,
            "color":       "#ffffff",
            "weight":      2.5,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["_name", "_val", "_pop"],
            aliases=["Region", f"{tooltip_label} / 100k ({year})", "Population (2024)"],
            style=(
                "background-color:#0e1220;color:#c8cfe0;"
                "font-family:IBM Plex Mono,monospace;font-size:12px;"
                "border:1px solid #4a6cf7;border-radius:6px;padding:10px 14px;"
            ),
            sticky=True,
        ),
    ).add_to(m)

    # Region labels
    for feat in geo["features"]:
        val  = feat["properties"]["_val"]
        name = feat["properties"]["_name"]
        clat, clon = centroid(feat)
        if clat is None:
            continue
        short = name.split("-")[0].strip()
        folium.Marker(
            location=[clat, clon],
            icon=folium.DivIcon(
                html=(
                    f'<div style="font-family:IBM Plex Mono,monospace;font-size:8px;'
                    f'color:#e8eeff;font-weight:600;text-align:center;white-space:nowrap;'
                    f'pointer-events:none;'
                    f'text-shadow:0 0 3px #000,0 0 3px #000,0 0 3px #000;">'
                    f'{short}<br>'
                    f'<span style="color:#f0c060;font-size:10px;font-weight:700;">'
                    f'{val:.1f}</span></div>'
                ),
                icon_size=(110, 30),
                icon_anchor=(55, 15),
            )
        ).add_to(m)

    return m


def build_physician_map(geojson):
    """Physician density map — single GeoJson layer."""
    density   = PHYSICIAN_DENSITY["per_1000"]
    thresh    = PHYSICIAN_DENSITY["who_threshold"]
    confirmed = PHYSICIAN_DENSITY["confirmed_regions"]

    geo = copy.deepcopy(geojson)
    for feat in geo["features"]:
        idx = feat["properties"]["Indice"]
        d   = density.get(idx, 0)
        feat["properties"]["_name"]    = REGION_NAMES.get(idx, "")
        feat["properties"]["_density"] = d
        feat["properties"]["_status"]  = "Above WHO threshold" if d >= thresh else "Below WHO threshold"
        feat["properties"]["_conf"]    = "✓ confirmed" if idx in confirmed else "~ estimated"
        feat["properties"]["_hex"]     = density_to_hex(d)

    m = folium.Map(
        location=[29.5, -7.5],
        zoom_start=5,
        tiles="CartoDB dark_matter",
        prefer_canvas=True,
    )

    folium.GeoJson(
        geo,
        style_function=lambda feat: {
            "fillColor":   feat["properties"]["_hex"],
            "fillOpacity": 0.82,
            "color":       "#c8cfe0",
            "weight":      1.2,
        },
        highlight_function=lambda feat: {
            "fillColor":   "#4a6cf7",
            "fillOpacity": 0.5,
            "color":       "#ffffff",
            "weight":      2.5,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["_name", "_density", "_status", "_conf"],
            aliases=["Region", "Doctors / 1,000", "WHO status", "Data quality"],
            style=(
                "background-color:#0e1220;color:#c8cfe0;"
                "font-family:IBM Plex Mono,monospace;font-size:12px;"
                "border:1px solid #4a6cf7;border-radius:6px;padding:10px 14px;"
            ),
            sticky=True,
        ),
    ).add_to(m)

    for feat in geo["features"]:
        d    = feat["properties"]["_density"]
        name = feat["properties"]["_name"]
        clat, clon = centroid(feat)
        if clat is None:
            continue
        color = "#4a9e6a" if d >= thresh else "#c06060"
        short = name.split("-")[0].strip()
        folium.Marker(
            location=[clat, clon],
            icon=folium.DivIcon(
                html=(
                    f'<div style="font-family:IBM Plex Mono,monospace;font-size:8px;'
                    f'color:#e8eeff;font-weight:600;text-align:center;white-space:nowrap;'
                    f'pointer-events:none;'
                    f'text-shadow:0 0 3px #000,0 0 3px #000;">'
                    f'{short}<br>'
                    f'<span style="color:{color};font-size:10px;font-weight:700;">'
                    f'{d}</span></div>'
                ),
                icon_size=(110, 30),
                icon_anchor=(55, 15),
            )
        ).add_to(m)

    return m


# ─── GENERAL HELPERS ─────────────────────────────────────────────────────────

def incidence_per_100k(cases: dict) -> dict:
    return {
        idx: round((cases.get(idx, 0) / POPULATION[idx]) * 100_000, 2)
        for idx in POPULATION
    }


def render_trend(trend: dict) -> str:
    years = sorted(k for k, v in trend.items() if v is not None)
    if len(years) < 2:
        return ""
    vals  = [trend[y] for y in years]
    delta = vals[-1] - vals[-2]
    pct   = round(abs(delta / vals[-2]) * 100, 1) if vals[-2] else 0
    arrow = "▲" if delta > 0 else "▼"
    cls   = "trend-up" if delta > 0 else "trend-down"
    chain = " → ".join(f"{v:,}" for v in vals)
    return (
        f'<span class="{cls}">{arrow} {pct}% vs {years[-2]}</span>'
        f'<br><span style="color:#3a4868;font-size:11px;">{chain}</span>'
    )


def top_regions(values: dict, n=5):
    return sorted(
        [(rname(i), v) for i, v in values.items()],
        key=lambda x: x[1], reverse=True
    )[:n]


def protein_blocks(seq, block=10, per_line=6):
    if not seq:
        return ""
    lines = []
    for ls in range(0, len(seq), block * per_line):
        chunk  = seq[ls:ls + block * per_line]
        blocks = [chunk[i:i+block] for i in range(0, len(chunk), block)]
        lines.append(f"{ls+1:>5}  " + "  ".join(blocks))
    return "\n".join(lines)


# ─── PYGENO HELPERS ──────────────────────────────────────────────────────────

def pygeno_available():
    return os.path.exists(PYGENO_PYTHON) and os.path.exists(PYGENO_SCRIPT)


@st.cache_data(ttl=3600, show_spinner=False)
def run_pygeno(gene_name: str) -> dict:
    if not pygeno_available():
        return {"error": "not_configured"}
    try:
        result = subprocess.run(
            [PYGENO_PYTHON, PYGENO_SCRIPT, gene_name, GENOME_BUILD],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            return {"error": result.stderr.strip()}
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {"error": "Query timed out (>60s). Is the genome imported?"}
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=3600, show_spinner=False)
def get_clinvar(gene_name: str) -> list:
    if not CLINVAR_AVAILABLE:
        return []
    return fetch_clinvar_variants(gene_name)


def render_gene_explorer(genes: list, disease_label: str):
    """Render pyGeno + ClinVar results for a list of genes."""
    if not pygeno_available():
        st.markdown(
            '<div class="warning-box">⚙ pyGeno not configured — '
            'set PYGENO_PYTHON in app.py to enable genomic queries.</div>',
            unsafe_allow_html=True
        )
        return

    st.markdown(
        f'<div class="section-label">Susceptibility genes — {disease_label}</div>',
        unsafe_allow_html=True
    )

    # Gene selector
    selected = st.radio(
        "Select gene",
        genes,
        horizontal=True,
        label_visibility="collapsed",
        key="gene_radio",
    )
    if selected != st.session_state.selected_gene:
        st.session_state.selected_gene = selected

    gene = st.session_state.selected_gene or genes[0]

    col_pygeno, col_clinvar = st.columns([1, 1], gap="medium")

    with col_pygeno:
        st.markdown(
            '<div class="section-label">Genomic coordinates — pyGeno</div>',
            unsafe_allow_html=True
        )
        with st.spinner(f"Querying pyGeno — {gene}..."):
            data = run_pygeno(gene)

        if "error" in data:
            st.error(f"pyGeno: {data['error']}")
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Chr", data["chromosome"])
            c2.metric("Length", f"{data['length_bp']:,} bp")
            c3.metric("Transcripts", data["n_transcripts"])
            c4.metric("Coding", data["n_coding_transcripts"])

            strand = "Forward (+)" if data["strand"] == 1 else "Reverse (−)"
            st.markdown(
                f'<div class="genomic-pos">chr{data["chromosome"]}:'
                f'{data["start"]:,}–{data["end"]:,} · {strand} · {data["ensembl_id"]}</div>',
                unsafe_allow_html=True
            )

            for iso in data.get("isoforms", []):
                with st.expander(
                    f'{iso["transcript_id"]} — {iso["protein_length"]} aa · {iso["coding_exons"]} exons'
                ):
                    if iso["exons"]:
                        df = pd.DataFrame(iso["exons"])
                        df.columns = ["Start", "End", "CDS (bp)", "5' CDS"]
                        df.index = [f"Exon {i+1}" for i in range(len(df))]
                        df["Start"] = df["Start"].apply(lambda x: f"{x:,}")
                        df["End"]   = df["End"].apply(lambda x: f"{x:,}")
                        st.dataframe(df, use_container_width=True)
                    if iso.get("protein_seq_60"):
                        st.code(
                            protein_blocks(iso["protein_seq_60"]) +
                            (f"\n... [{iso['protein_length'] - 60} more aa]"
                             if iso["protein_length"] > 60 else ""),
                            language=None
                        )

    with col_clinvar:
        st.markdown(
            '<div class="section-label">Pathogenic variants — ClinVar</div>',
            unsafe_allow_html=True
        )
        if not CLINVAR_AVAILABLE:
            st.markdown(
                '<div class="warning-box">clinvar.py not found — '
                'copy it from pyGeno_Scouter into this folder.</div>',
                unsafe_allow_html=True
            )
        else:
            with st.spinner(f"Fetching ClinVar — {gene}..."):
                variants = get_clinvar(gene)

            if not variants:
                st.markdown(
                    '<div class="source-box">No pathogenic or likely pathogenic '
                    'variants found in ClinVar for this gene.</div>',
                    unsafe_allow_html=True
                )
            else:
                st.caption(
                    f"{len(variants)} pathogenic / likely pathogenic variant(s) · ClinVar NCBI"
                )
                for v in variants:
                    sig = v["significance"].lower()
                    badge = (
                        '<span class="badge-likely">Likely Pathogenic</span>'
                        if "likely" in sig
                        else '<span class="badge-pathogenic">Pathogenic</span>'
                    )
                    url = clinvar_url(v["variation_id"])
                    st.markdown(
                        f'<div class="clinvar-row">'
                        f'<div style="font-family:IBM Plex Mono,monospace;font-size:11px;'
                        f'color:#7090e8;margin-bottom:4px;">{v["title"]}</div>'
                        f'{badge}'
                        f'<div style="font-size:11px;color:#506080;margin-top:4px;">'
                        f'Condition: {v["condition"]}</div>'
                        f'<a href="{url}" target="_blank" '
                        f'style="font-size:10px;color:#4a6cf7;text-decoration:none;">'
                        f'View on ClinVar →</a>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

                # CSV export
                df_export = pd.DataFrame([{
                    "Gene": gene,
                    "Variant": v["title"],
                    "Significance": v["significance"],
                    "Condition": v["condition"],
                    "ClinVar URL": clinvar_url(v["variation_id"]),
                } for v in variants])
                st.download_button(
                    label="⬇ Export variants (.csv)",
                    data=df_export.to_csv(index=False).encode("utf-8"),
                    file_name=f"clinvar_{gene}.csv",
                    mime="text/csv",
                )


# ─── LOAD ────────────────────────────────────────────────────────────────────

geojson = load_geojson()

# ─── SIDEBAR ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🗺 Morocco NTD")
    st.divider()

    st.markdown("#### Language / Langue")
    col_en, col_fr = st.columns(2)
    with col_en:
        if st.button("🇬🇧 EN", use_container_width=True):
            st.session_state.lang = "en"
            st.rerun()
    with col_fr:
        if st.button("🇫🇷 FR", use_container_width=True):
            st.session_state.lang = "fr"
            st.rerun()

    st.divider()
    st.markdown(f"#### {t('data_sources')}")
    st.success("Annuaire Statistique 2025 — HCP")
    st.success("RGPH 2024 — HCP")
    st.success("Santé en Chiffres 2023 — MSPS")
    st.success("WHO EMRO / MSPS 2024")

    st.divider()
    st.markdown(f"#### {t('diseases_covered')}")
    for key, d in DISEASES.items():
        lbl  = d["label_fr"] if st.session_state.lang == "fr" else d["label"]
        conf = d["data"]["confidence"]
        st.caption(f'{d["icon"]} {lbl} {"✓" if conf == "CONFIRMED" else "~"}')
    st.caption(f"🏥 {t('healthcare_tab')}")
    st.caption(f"🧬 Gene Explorer")

    st.divider()
    st.caption(f'{t("national_pop")}: {NATIONAL_POPULATION:,}')
    st.caption("12 régions (réforme 2015)")
    st.caption(f'{t("last_updated")}: mars 2026')
    st.divider()
    pyg_status = "✓ configured" if pygeno_available() else "⚠ not configured"
    cv_status  = "✓ available" if CLINVAR_AVAILABLE else "⚠ clinvar.py missing"
    st.caption(f"pyGeno: {pyg_status}")
    st.caption(f"ClinVar: {cv_status}")

# ─── HEADER ──────────────────────────────────────────────────────────────────

st.markdown(f"# 🗺 {t('title')}")
st.markdown(
    f'<p style="color:#506080;font-size:14px;margin-top:-8px;margin-bottom:20px;">'
    f'{t("subtitle")} · Annuaire Statistique 2025 / RGPH 2024</p>',
    unsafe_allow_html=True
)

# ─── TABS ────────────────────────────────────────────────────────────────────

main_tab, infra_tab, gene_tab = st.tabs([
    "🦟  NTD Map",
    f"🏥  {t('healthcare_tab')}",
    "🧬  Gene Explorer",
])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — NTD MAP
# ════════════════════════════════════════════════════════════════════════════

with main_tab:

    col_map, col_selector = st.columns([3, 1], gap="medium")

    # ── Right column: disease selector + stats ────────────────────────────────
    with col_selector:
        st.markdown(
            f'<div class="section-label">{t("select_disease")}</div>',
            unsafe_allow_html=True
        )

        for dkey, disease in DISEASES.items():
            lbl  = disease["label_fr"] if st.session_state.lang == "fr" else disease["label"]
            nat  = disease["national"]
            unit = disease["unit_fr"] if st.session_state.lang == "fr" else disease["unit"]
            is_active = st.session_state.selected_disease == dkey
            # Active indicator rendered above button via markdown
            if is_active:
                st.markdown(
                    f'<div style="background:#0e1525;border:1px solid #4a6cf7;'
                    f'border-radius:8px;padding:10px 14px;margin:3px 0;'
                    f'font-family:IBM Plex Sans,sans-serif;font-size:13px;'
                    f'color:#a0c0ff;font-weight:600;">'
                    f'▶ {disease["icon"]}  {lbl}  ·  {nat:,} {unit}</div>',
                    unsafe_allow_html=True
                )
            else:
                if st.button(
                    f'{disease["icon"]}  {lbl}  ·  {nat:,} {unit}',
                    key=f"btn_{dkey}",
                    use_container_width=True,
                ):
                    st.session_state.selected_disease   = dkey
                    st.session_state.selected_region    = None
                    st.session_state.show_gene_explorer = False
                    st.rerun()

        st.markdown('<hr class="divider">', unsafe_allow_html=True)

        disease  = DISEASES[st.session_state.selected_disease]
        data     = disease["data"]
        vkey     = disease["value_key"]
        raw      = data[vkey]
        incid    = incidence_per_100k(raw)
        conf     = data["confidence"]
        lbl      = disease["label_fr"] if st.session_state.lang == "fr" else disease["label"]
        unit     = disease["unit_fr"] if st.session_state.lang == "fr" else disease["unit"]

        st.markdown(
            f'<div class="stat-card">'
            f'<div class="stat-lbl">{t("national_total")} — {disease["year"]}</div>'
            f'<div class="stat-val">{disease["national"]:,}</div>'
            f'<div class="stat-sub">{unit}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

        trend_html = render_trend(data["trend"])
        if trend_html:
            st.markdown(
                f'<div class="stat-card">'
                f'<div class="stat-lbl">{t("trend")}</div>'
                f'<div style="font-size:12px;color:#8090a8;line-height:2;">{trend_html}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

        st.markdown(
            f'<div class="section-label">{t("top_regions")}</div>',
            unsafe_allow_html=True
        )
        rows = "".join(
            f'<div class="region-row"><span class="rname">{n}</span>'
            f'<span class="rval">{v:.1f}</span></div>'
            for n, v in top_regions(incid)
        )
        st.markdown(
            f'<div style="background:#111420;border:1px solid #1e2438;'
            f'border-radius:8px;padding:10px 14px;">{rows}'
            f'<div style="font-size:10px;color:#3a4868;margin-top:6px;'
            f'font-family:IBM Plex Mono,monospace;">{t("per_100k")}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

        if conf == "CONFIRMED":
            st.markdown(
                f'<div class="confirmed-box">✓ {t("confirmed")}<br>'
                f'<span style="color:#2a6838;">{data["source"]}</span></div>',
                unsafe_allow_html=True
            )
        elif conf == "NO_REGIONAL_DATA":
            st.markdown(
                f'<div class="warning-box">⚠ Regional breakdown not published in any '
                f'official source. Map disabled — national total only.<br>'
                f'<span style="color:#6a4010;">{data["source"]}</span></div>',
                unsafe_allow_html=True
            )
        elif conf == "PROPORTIONAL":
            st.markdown(
                f'<div class="warning-box">~ Regional figures proportionally derived '
                f'from DELM 10-year cumulative data (2013–2023). Not annual confirmed figures.<br>'
                f'<span style="color:#6a4010;">{data["source"]}</span></div>',
                unsafe_allow_html=True
            )
        elif conf == "PARTIAL":
            st.markdown(
                f'<div class="warning-box">~ One region confirmed (Casablanca: 55). '
                f'Remaining 567 cases distributed proportionally.<br>'
                f'<span style="color:#6a4010;">{data["source"]}</span></div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div class="warning-box">{t("warning_estimated")}</div>',
                unsafe_allow_html=True
            )

        # Genes panel
        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-label">🧬 Susceptibility genes</div>',
            unsafe_allow_html=True
        )
        genes     = disease["pygeno_genes"]
        gene_note = disease["pygeno_note_fr"] if st.session_state.lang == "fr" else disease["pygeno_note"]
        chips     = " ".join(f'<span class="gene-chip">{g}</span>' for g in genes)
        st.markdown(
            f'<div style="background:#0e1118;border:1px solid #1e2438;border-radius:8px;'
            f'padding:12px 14px;margin-bottom:8px;">'
            f'{chips}'
            f'<div style="font-size:11px;color:#506080;margin-top:8px;line-height:1.6;">'
            f'{gene_note}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        if st.button("🧬 Explore in Gene Explorer →", key="goto_gene", use_container_width=True):
            st.session_state.selected_gene      = genes[0]
            st.session_state.show_gene_explorer = not st.session_state.show_gene_explorer
            st.rerun()

    # ── Left column: map + detail panel ──────────────────────────────────────
    with col_map:
        if conf == "NO_REGIONAL_DATA":
            st.markdown(
                f'<div class="section-label">{lbl} — {disease["year"]}</div>',
                unsafe_allow_html=True
            )
            st.markdown(
                f'<div style="background:#111420;border:1px solid #1e2438;border-radius:10px;'
                f'padding:40px 24px;text-align:center;margin-bottom:12px;">'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:11px;'
                f'color:#3a4868;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:12px;">'
                f'Regional breakdown not available</div>'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:48px;'
                f'font-weight:600;color:#c8cfe0;">{disease["national"]}</div>'
                f'<div style="font-size:13px;color:#506080;margin-top:6px;">'
                f'confirmed national cases — {disease["year"]}</div>'
                f'<div style="font-size:11px;color:#3a4868;margin-top:16px;'
                f'max-width:400px;margin-left:auto;margin-right:auto;line-height:1.6;">'
                f'{data["note"]}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div class="section-label">{lbl} — {t("cases_per_100k")} — {disease["year"]}</div>',
                unsafe_allow_html=True
            )
            st.caption(t("select_region"))

            m = build_map(geojson, incid, lbl, disease["year"])
            map_data = st_folium(
                m,
                width=None,
                height=500,
                returned_objects=["last_object_clicked"],
                key=f"map_{st.session_state.selected_disease}_{st.session_state.lang}",
            )

            # Detect region click via point-in-polygon
            clicked = map_data.get("last_object_clicked") if map_data else None
            if clicked and isinstance(clicked, dict):
                lat = clicked.get("lat")
                lng = clicked.get("lng")
                if lat and lng:
                    idx = find_region_by_click(lat, lng, geojson)
                    if idx and idx != st.session_state.selected_region:
                        st.session_state.selected_region = idx
                        st.rerun()

        # ── Detail panel — directly below map ────────────────────────────────
        if st.session_state.selected_region:
            idx      = st.session_state.selected_region
            reg_name = rname(idx)
            pop      = POPULATION.get(idx, 0)

            st.markdown(
                f'<div class="region-detail">'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:15px;'
                f'font-weight:600;color:#e8eeff;margin-bottom:2px;">{reg_name}</div>'
                f'<div style="font-size:12px;color:#3a4868;margin-bottom:12px;">'
                f'{t("population")}: {pop:,}</div>',
                unsafe_allow_html=True
            )

            # All diseases for this region
            st.markdown(
                f'<div class="section-label">{t("all_diseases")}</div>',
                unsafe_allow_html=True
            )
            dcols = st.columns(len(DISEASES))
            for dcol, (dkey, d) in zip(dcols, DISEASES.items()):
                with dcol:
                    rv   = d["data"][d["value_key"]].get(idx, 0)
                    iv   = round((rv / pop) * 100_000, 1) if pop else 0
                    dlbl = d["label_fr"] if st.session_state.lang == "fr" else d["label"]
                    dunit= d["unit_fr"] if st.session_state.lang == "fr" else d["unit"]
                    cc   = d["data"]["confidence"]
                    cc_color = "#4a9e5a" if cc == "CONFIRMED" else "#8a6020"
                    st.markdown(
                        f'<div class="stat-card" style="text-align:center;padding:10px;">'
                        f'<div style="font-size:16px;">{d["icon"]}</div>'
                        f'<div class="stat-lbl" style="margin-top:3px;font-size:9px;">{dlbl}</div>'
                        f'<div class="stat-val" style="font-size:18px;">{rv:,}</div>'
                        f'<div class="stat-sub">{iv:.1f} {t("per_100k")}</div>'
                        f'<div style="font-size:9px;color:{cc_color};margin-top:2px;'
                        f'font-family:IBM Plex Mono,monospace;">{cc}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

            # Physician density
            st.markdown('<hr class="divider">', unsafe_allow_html=True)
            dens  = PHYSICIAN_DENSITY["per_1000"].get(idx)
            confs = PHYSICIAN_DENSITY["confirmed_regions"]
            thresh = PHYSICIAN_DENSITY["who_threshold"]
            if dens:
                sc   = "#4a9e6a" if dens >= thresh else "#c06060"
                stxt = t("above_threshold") if dens >= thresh else t("below_threshold")
                cnote= "✓ confirmed" if idx in confs else "~ estimated"
                st.markdown(
                    f'<div class="stat-card" style="display:inline-block;min-width:200px;">'
                    f'<div class="stat-lbl">{t("physician_density")}</div>'
                    f'<div class="stat-val">{dens}</div>'
                    f'<div class="stat-sub" style="color:{sc};">{stxt}</div>'
                    f'<div style="font-size:10px;color:#3a4868;margin-top:2px;'
                    f'font-family:IBM Plex Mono,monospace;">{t("who_threshold")} · {cnote}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

            st.markdown('</div>', unsafe_allow_html=True)

        else:
            st.markdown(
                f'<div class="source-box" style="margin-top:10px;">'
                f'↑ {t("select_region")} · '
                f'Source: Annuaire Statistique du Maroc 2025 (HCP), '
                f'RGPH 2024 (HCP), Santé en Chiffres 2023 (MSPS)'
                f'</div>',
                unsafe_allow_html=True
            )

    # ── Inline Gene Explorer — shown when button clicked ─────────────────────
    if st.session_state.show_gene_explorer:
        active_d     = DISEASES[st.session_state.selected_disease]
        active_label = active_d["label_fr"] if st.session_state.lang == "fr" else active_d["label"]
        active_genes = active_d["pygeno_genes"]
        active_note  = active_d["pygeno_note_fr"] if st.session_state.lang == "fr" else active_d["pygeno_note"]

        st.markdown(
            f'<div style="background:#0a0c14;border:1px solid #4a6cf7;'
            f'border-top:3px solid #4a6cf7;border-radius:0 0 10px 10px;'
            f'padding:20px 24px;margin-top:4px;">'
            f'<div style="font-family:IBM Plex Mono,monospace;font-size:13px;'
            f'font-weight:600;color:#4a6cf7;margin-bottom:4px;">🧬 Gene Explorer</div>'
            f'<div style="font-size:12px;color:#3a4868;margin-bottom:12px;">{active_label} — {active_note}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        render_gene_explorer(active_genes, active_label)

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — HEALTHCARE INFRASTRUCTURE
# ════════════════════════════════════════════════════════════════════════════

with infra_tab:
    density  = PHYSICIAN_DENSITY["per_1000"]
    thresh   = PHYSICIAN_DENSITY["who_threshold"]
    nat_avg  = PHYSICIAN_DENSITY["national_avg"]
    confs    = PHYSICIAN_DENSITY["confirmed_regions"]

    col_m2, col_s2 = st.columns([3, 1], gap="medium")

    with col_m2:
        st.markdown(
            f'<div class="section-label">{t("physician_density")} — 2024</div>',
            unsafe_allow_html=True
        )
        m2 = build_physician_map(geojson)
        st_folium(m2, width=None, height=500, returned_objects=[], key="map_infra")
        st.markdown(
            f'<div class="source-box">'
            f'Source: {PHYSICIAN_DENSITY["source"]}<br>'
            f'{PHYSICIAN_DENSITY["note"]}'
            f'</div>',
            unsafe_allow_html=True
        )

    with col_s2:
        st.markdown(
            f'<div class="stat-card">'
            f'<div class="stat-lbl">{t("national_avg")}</div>'
            f'<div class="stat-val">{nat_avg}</div>'
            f'<div class="stat-sub">/ 1,000 inhabitants</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            f'<div class="stat-card">'
            f'<div class="stat-lbl">{t("who_threshold")}</div>'
            f'<div class="stat-val">{thresh}</div>'
            f'<div class="stat-sub trend-up">Morocco below threshold</div>'
            f'</div>',
            unsafe_allow_html=True
        )

        above = [(REGION_NAMES[i], v, i in confs) for i, v in density.items() if v >= thresh]
        below = [(REGION_NAMES[i], v, i in confs) for i, v in density.items() if v < thresh]

        st.markdown(
            f'<div class="section-label">{t("above_threshold")} ({len(above)}/12)</div>',
            unsafe_allow_html=True
        )
        rows_a = "".join(
            f'<div class="region-row"><span class="rname">{n}{"" if c else " ~"}</span>'
            f'<span style="color:#4a9e6a;font-family:IBM Plex Mono,monospace;font-size:12px;">{v}</span></div>'
            for n, v, c in sorted(above, key=lambda x: x[1], reverse=True)
        )
        st.markdown(
            f'<div style="background:#111420;border:1px solid #1e2438;border-radius:8px;padding:10px 14px;">'
            f'{rows_a}</div>', unsafe_allow_html=True
        )

        st.markdown(
            f'<div class="section-label">{t("below_threshold")} ({len(below)}/12)</div>',
            unsafe_allow_html=True
        )
        rows_b = "".join(
            f'<div class="region-row"><span class="rname">{n}{"" if c else " ~"}</span>'
            f'<span style="color:#c06060;font-family:IBM Plex Mono,monospace;font-size:12px;">{v}</span></div>'
            for n, v, c in sorted(below, key=lambda x: x[1])
        )
        st.markdown(
            f'<div style="background:#111420;border:1px solid #1e2438;border-radius:8px;padding:10px 14px;">'
            f'{rows_b}</div>', unsafe_allow_html=True
        )

        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        st.markdown(
            '<div style="background:#0e1220;border:1px solid #1e2438;border-radius:8px;'
            'padding:12px 14px;font-size:11px;color:#506080;line-height:1.7;">'
            'Béni Mellal-Khénifra (1.40) and Souss-Massa (1.50) combine the lowest '
            'physician density with high NTD burden — the critical bottleneck for '
            'disease control in Morocco. ~ = estimated figure.'
            '</div>',
            unsafe_allow_html=True
        )

# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — GENE EXPLORER
# ════════════════════════════════════════════════════════════════════════════

with gene_tab:
    st.markdown(
        '<p style="color:#506080;font-size:13px;margin-bottom:16px;">'
        'Genomic coordinates and known pathogenic variants for susceptibility genes '
        'associated with NTDs prevalent in Morocco. Powered by pyGeno (Daouda et al.) '
        'and NCBI ClinVar.</p>',
        unsafe_allow_html=True
    )

    # Disease selector for gene explorer
    st.markdown('<div class="section-label">Select disease</div>', unsafe_allow_html=True)
    gene_disease_cols = st.columns(len(DISEASES))
    for gcol, (dkey, d) in zip(gene_disease_cols, DISEASES.items()):
        with gcol:
            dlbl = d["label_fr"] if st.session_state.lang == "fr" else d["label"]
            if st.button(
                f'{d["icon"]} {dlbl}',
                key=f"gene_tab_btn_{dkey}",
                use_container_width=True,
            ):
                st.session_state.selected_disease = dkey
                st.session_state.selected_gene = DISEASES[dkey]["pygeno_genes"][0]
                st.rerun()

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    active_disease = DISEASES[st.session_state.selected_disease]
    active_label   = active_disease["label_fr"] if st.session_state.lang == "fr" else active_disease["label"]
    active_genes   = active_disease["pygeno_genes"]
    active_note    = active_disease["pygeno_note_fr"] if st.session_state.lang == "fr" else active_disease["pygeno_note"]

    st.markdown(
        f'<div style="background:#0e1118;border:1px solid #1e2438;border-radius:8px;'
        f'padding:12px 14px;margin-bottom:12px;">'
        f'<div class="stat-lbl" style="margin-bottom:6px;">{active_label} — genetic basis</div>'
        f'<div style="font-size:12px;color:#8090a8;line-height:1.7;">{active_note}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    render_gene_explorer(active_genes, active_label)
