# 🗺 Morocco NTD Dashboard

An interactive dashboard mapping the burden of neglected tropical diseases across Morocco's 12 administrative regions. Combines official epidemiological data, healthcare infrastructure, and genomic susceptibility information in one place.

Built alongside [pyGeno Scouter](https://github.com/Thatguybassam/pygeno-scouter).

---

## Live preview

**[→ Open interactive preview](https://thatguybassam.github.io/morocco-ntd-dashboard/)**

This is a lightweight HTML version hosted on GitHub Pages — no installation required, works in any browser and on mobile. It is a visual preview only and lacks some functionality available in the full app:

- Gene Explorer (pyGeno genomic coordinates and ClinVar variants require a local Python environment)
- ClinVar live queries
- Region click detail panel with physician density
- Language toggle persistence across sessions

For the full experience, run the Streamlit app locally.

---

## Screenshots

**NTD Map — Tuberculosis with region hover:**
![NTD Map](screenshots/ntd_map.png)

**Healthcare Infrastructure — physician density by region:**
![Healthcare Infrastructure](screenshots/healthcare_infra.png)

**Gene Explorer — pyGeno coordinates + ClinVar pathogenic variants:**
![Gene Explorer](screenshots/gene_explorer.png)

---

## What it does

- Interactive choropleth map of Morocco's 12 regions colored by disease incidence per 100,000 inhabitants (normalized with RGPH 2024 population data)
- Disease selector — switch between 5 diseases and a healthcare infrastructure layer
- Click any region on the map to see all disease burdens and physician density for that region
- Gene Explorer — pyGeno genomic coordinates and ClinVar pathogenic variants for susceptibility genes associated with each disease
- French / English language toggle
- Dark theme consistent with pyGeno Scouter

---

## Diseases covered

| Disease | Year | National total | Data confidence |
|---|---|---|---|
| Cutaneous Leishmaniasis | 2023 | 2,359 cases | CONFIRMED |
| Visceral Leishmaniasis | 2023 | 73 cases | NO REGIONAL DATA |
| Human Rabies | 2024 | 33 deaths | PROPORTIONAL |
| Imported Malaria | 2023 | 622 cases | PARTIAL |
| Tuberculosis | 2023 | 32,429 cases | CONFIRMED |

---

## Data confidence

Each disease layer is labeled with one of four confidence levels:

| Level | Meaning |
|---|---|
| **CONFIRMED** | Figures extracted directly from official government tables |
| **PROPORTIONAL** | National total confirmed; regional distribution derived from historical cumulative data |
| **PARTIAL** | One or more regions confirmed; remainder proportionally distributed |
| **NO REGIONAL DATA** | National total confirmed; no regional breakdown exists in any public source |

**Cutaneous Leishmaniasis** `CONFIRMED`
Regional figures from Annuaire Statistique du Maroc 2025, HCP — Tableau 12-27. National total verified: 2,359 cases.

**Tuberculosis** `CONFIRMED`
Same source — Tableau 12-27. National total verified: 32,429 cases.

**Human Rabies** `PROPORTIONAL`
National totals confirmed: 19 deaths (2023), 33 deaths (2024). Annual regional breakdown does not exist in any publicly available official source (confirmed by exhaustive search of MSPS, DELM, and WHO EMRO publications). Regional distribution proportionally derived from DELM cumulative 2013–2023 data (198 total cases) published in a WOAH Africa / DELM epidemiological presentation (2025).

**Imported Malaria** `PARTIAL`
National total confirmed: 622 cases (2023). Casablanca-Settat confirmed: 55 cases (Rapport Régional Casablanca-Settat ODD 2025). Remaining 567 cases distributed proportionally based on historical migration corridor data.

**Visceral Leishmaniasis** `NO REGIONAL DATA`
National total confirmed: 73 cases (2023). Regional breakdown not published in any official source. No choropleth is rendered — the national total is displayed directly.

---

## Data sources

| Source | Contents | Year |
|---|---|---|
| Annuaire Statistique du Maroc 2025, HCP | Regional disease surveillance (Tableau 12-27), physician counts by region (Tableau 12-4) | January 2026 |
| RGPH 2024, HCP | Legal population by region | November 2024 |
| Santé en Chiffres 2023, MSPS | National MDO totals (Tab 1.5) | 2023 |
| Rapport Régional Casablanca-Settat ODD 2025 | Confirmed malaria figure for Casablanca | 2025 |
| WOAH Africa / DELM epidemiological presentation | Cumulative rabies cases 2013–2023 by region | 2025 |
| MSPS / WHO EMRO 2024 bulletin | Rabies deaths 2024 national total | 2024 |
| Medias24 / MSPS 2024 | Physician density figures (8 of 12 regions confirmed) | 2024 |

---

## Requirements

```
streamlit
pandas
folium
streamlit-folium
```

Also required in the root folder (copy from [pyGeno Scouter](https://github.com/Thatguybassam/pygeno-scouter)):
- `pygeno_query.py`
- `clinvar.py`

---

## Installation

```bash
git clone https://github.com/Thatguybassam/morocco-ntd-dashboard
cd morocco-ntd-dashboard
pip install streamlit pandas folium streamlit-folium
```

Copy `pygeno_query.py` and `clinvar.py` from pyGeno Scouter into the root folder.

Download `Morocco-Regions.geojson` from [Salah-Zkara/Morocco-GeoJson](https://github.com/Salah-Zkara/Morocco-GeoJson) and place it in `data/`.

Open `app.py` and update `PYGENO_PYTHON` to point to your Python 3.6 conda environment:

```python
PYGENO_PYTHON = r"C:\Users\<your_username>\miniconda3\envs\pygeno_env\python.exe"
```

```bash
streamlit run app.py
```

Opens at http://localhost:8501.

---

## Project structure

```
morocco-ntd-dashboard/
├── app.py
├── clinvar.py              ← copy from pyGeno Scouter
├── pygeno_query.py         ← copy from pyGeno Scouter
├── requirements.txt
├── README.md
├── screenshots/
└── data/
    ├── ntd_data.py
    └── Morocco-Regions.geojson   ← not committed (.gitignore)
```

---

## Connection to pyGeno Scouter

Each disease panel shows the human susceptibility genes relevant to that condition. The Gene Explorer tab runs live pyGeno queries and ClinVar lookups for those genes directly inside the dashboard. The two tools work well together — the dashboard maps disease burden by region, Scouter provides the genomic detail.

---

## Limitations

- Regional data for visceral leishmaniasis, rabies, and malaria is not available at the 12-region level in any public official source as of March 2026.
- Physician density is confirmed for 8 of 12 regions. The remaining 4 are estimated.
- pyGeno requires a local Python 3.6 conda environment with GRCh38.78 imported (~4GB disk space).
- Not intended for clinical or public health decision-making.

---

## License

MIT

Data: HCP (public), MSPS (public), WHO EMRO (public), WOAH Africa (public).
