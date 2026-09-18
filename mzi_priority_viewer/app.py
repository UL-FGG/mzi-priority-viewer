from pathlib import Path
from io import BytesIO

import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from branca.element import Element, MacroElement, Template
from folium.features import GeoJsonTooltip
from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim
from streamlit_folium import st_folium
from shapely.geometry import Point


# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Prioritetna območja MZI",
    page_icon="🗺️",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "final_mzi_action_priority_aoi_ozje.gpkg"
LOGO_PATH = BASE_DIR / "UL_FGG-logoVER-RGB_barv.png"
MZI_LOGO_PATH = BASE_DIR / "mzi_priority_viewer_logo.png"

CATEGORY_ORDER = [
    "ni skupna prioriteta",
    "zmerna razvojna prioriteta",
    "socialna prioriteta z zmernim MZI primanjkljajem",
    "biofizikalna prioriteta",
    "visoka skupna prioriteta",
    "ključna jedra ukrepanja",
]

CATEGORY_COLORS = {
    "ni skupna prioriteta": "#D9D9D9",
    "zmerna razvojna prioriteta": "#FFE66D",
    "socialna prioriteta z zmernim MZI primanjkljajem": "#FDAE61",
    "biofizikalna prioriteta": "#67A9CF",
    "visoka skupna prioriteta": "#F46D43",
    "ključna jedra ukrepanja": "#A50026",
}

DEFAULT_VISIBLE = {
    "ni skupna prioriteta": False,
    "zmerna razvojna prioriteta": True,
    "socialna prioriteta z zmernim MZI primanjkljajem": True,
    "biofizikalna prioriteta": True,
    "visoka skupna prioriteta": True,
    "ključna jedra ukrepanja": True,
}

DISPLAY_FIELDS = [
    "cell_id",
    "final_mzi_action_index",
    "final_mzi_action_class",
    "final_mzi_action_typology",
    "social_need_index",
    "green_blue_deficit_index",
    "strategic_priority_pre_feasibility_index",
    "heat_hazard_social_index",
    "population_total",
    "tree_cover_300m_pct",
    "impervious_300m_pct",
]

FIELD_ALIASES = {
    "cell_id": "ID celice",
    "final_mzi_action_index": "Končni indeks ukrepanja",
    "final_mzi_action_class": "Končni razred",
    "final_mzi_action_typology": "Tipologija",
    "social_need_index": "Indeks socialno-prostorske potrebe",
    "green_blue_deficit_index": "Biofizikalni primanjkljaj MZI",
    "strategic_priority_pre_feasibility_index": "Strateška prioriteta pred izvedljivostjo",
    "heat_hazard_social_index": "Indeks toplotne nevarnosti in socialne izpostavljenosti",
    "population_total": "Prebivalstvo v celici",
    "tree_cover_300m_pct": "Delež drevesnega pokrova v 300 m (%)",
    "impervious_300m_pct": "Delež neprepustnih površin v 300 m (%)",
}

# Podrobnosti, namenjene javnemu prikazu. Vrstni red tukaj določa tudi vrstni red v aplikaciji.
DETAIL_GROUPS = {
    "Končna razvrstitev": [
        ("final_mzi_action_class", "Končni razred"),
        ("final_mzi_action_typology", "Tipologija"),
        ("social_need_dominant_component", "Prevladujoča sestavina socialno-prostorske potrebe"),
        ("mzi_gap_dominant_component", "Prevladujoča sestavina biofizikalnega primanjkljaja MZI"),
    ],
    "Površinski pokrov": [
        ("pct_high_vegetation", "Delež visoke vegetacije (%)"),
        ("pct_water", "Delež vodnih površin (%)"),
        ("pct_low_vegetation", "Delež nizke vegetacije (%)"),
        ("pct_buildings", "Delež stavb (%)"),
        ("pct_roads", "Delež cest (%)"),
        ("pct_parking", "Delež parkirišč (%)"),
        ("pct_other_impervious", "Delež drugih neprepustnih površin (%)"),
    ],
    "Okolica v 300 m": [
        ("tree_cover_300m_pct", "Delež drevesnega pokrova v 300 m (%)"),
        ("water_300m_pct", "Delež vodnih površin v 300 m (%)"),
        ("impervious_300m_pct", "Delež neprepustnih površin v 300 m (%)"),
    ],
    "Prostorski in grajeni kontekst": [
        ("distance_to_water_m", "Oddaljenost do vode (m)"),
        ("distance_to_major_water_m", "Oddaljenost do večje vodne površine (m)"),
        ("road_width_mean_m", "Povprečna širina cest (m)"),
        ("building_height_mean_m", "Povprečna višina stavb (m)"),
        ("built_volume_density_m3_m2", "Gostota pozidanega volumna (m³/m²)"),
        ("local_public_space_pct", "Delež lokalnega javnega prostora (%)"),
    ],
    "Modelirana temperatura zemeljskega površja": [
        ("pred_landsat_morning_c", "LST Landsat (°C) ob 12. uri"),
        ("pred_ecostress_morning_c", "LST ECOSTRESS (°C) med 7. in 12. uro"),
        ("pred_ecostress_afternoon_c", "LST ECOSTRESS (°C) med 12. in 18. uro"),
        ("pred_ecostress_evening_c", "LST ECOSTRESS (°C) med 18. in 22. uro"),
        ("pred_ecostress_night_c", "LST ECOSTRESS (°C) med 22. in 7. uro"),
    ],
}

PERCENT_FIELDS = {
    "pct_high_vegetation", "pct_water", "pct_low_vegetation", "pct_buildings",
    "pct_roads", "pct_parking", "pct_other_impervious", "tree_cover_300m_pct",
    "water_300m_pct", "impervious_300m_pct", "local_public_space_pct",
}

METER_FIELDS = {
    "distance_to_water_m", "distance_to_major_water_m", "road_width_mean_m",
    "building_height_mean_m",
}

TEMP_FIELDS = {
    "pred_landsat_morning_c", "pred_ecostress_morning_c",
    "pred_ecostress_afternoon_c", "pred_ecostress_evening_c",
    "pred_ecostress_night_c",
}



DATA_CITATION = (
    "Potočnik Buhvald, Ana. 2026. "
    "Rezultati prostorske opredelitve prednostnih območij za razvoj "
    "modro-zelene infrastrukture za zmanjševanje urbanega pregrevanja v Ljubljani. "
    "Univerza v Ljubljani, Fakulteta za gradbeništvo in geodezijo."
)

# Atributi za izvoz posamezne izbrane celice. Izvoz vsebuje samo javno prikazane
# oziroma vsebinsko izbrane atribute, ne celotnega tehničnega izvornega sloja.
EXPORT_FIELDS = [
    "cell_id",
    "final_mzi_action_index",
    "final_mzi_action_class",
    "final_mzi_action_typology",
    "social_need_index",
    "social_need_dominant_component",
    "green_blue_deficit_index",
    "mzi_gap_dominant_component",
    "strategic_priority_pre_feasibility_index",
    "heat_hazard_social_index",
    "population_total",
    "pct_high_vegetation",
    "pct_water",
    "pct_low_vegetation",
    "pct_buildings",
    "pct_roads",
    "pct_parking",
    "pct_other_impervious",
    "tree_cover_300m_pct",
    "water_300m_pct",
    "impervious_300m_pct",
    "distance_to_water_m",
    "distance_to_major_water_m",
    "road_width_mean_m",
    "building_height_mean_m",
    "built_volume_density_m3_m2",
    "local_public_space_pct",
    "pred_landsat_morning_c",
    "pred_ecostress_morning_c",
    "pred_ecostress_afternoon_c",
    "pred_ecostress_evening_c",
    "pred_ecostress_night_c",
]

EXPORT_ALIASES = {
    **FIELD_ALIASES,
    "social_need_dominant_component": "Prevladujoča sestavina socialno-prostorske potrebe",
    "mzi_gap_dominant_component": "Prevladujoča sestavina biofizikalnega primanjkljaja MZI",
    "pct_high_vegetation": "Delež visoke vegetacije (%)",
    "pct_water": "Delež vodnih površin (%)",
    "pct_low_vegetation": "Delež nizke vegetacije (%)",
    "pct_buildings": "Delež stavb (%)",
    "pct_roads": "Delež cest (%)",
    "pct_parking": "Delež parkirišč (%)",
    "pct_other_impervious": "Delež drugih neprepustnih površin (%)",
    "water_300m_pct": "Delež vodnih površin v 300 m (%)",
    "distance_to_water_m": "Oddaljenost do vode (m)",
    "distance_to_major_water_m": "Oddaljenost do večje vodne površine (m)",
    "road_width_mean_m": "Povprečna širina cest (m)",
    "building_height_mean_m": "Povprečna višina stavb (m)",
    "built_volume_density_m3_m2": "Gostota pozidanega volumna (m³/m²)",
    "local_public_space_pct": "Delež lokalnega javnega prostora (%)",
    "pred_landsat_morning_c": "LST Landsat (°C) ob 12. uri",
    "pred_ecostress_morning_c": "LST ECOSTRESS (°C) med 7. in 12. uro",
    "pred_ecostress_afternoon_c": "LST ECOSTRESS (°C) med 12. in 18. uro",
    "pred_ecostress_evening_c": "LST ECOSTRESS (°C) med 18. in 22. uro",
    "pred_ecostress_night_c": "LST ECOSTRESS (°C) med 22. in 7. uro",
}


# -----------------------------------------------------------------------------
# FORMATTED EXCEL EXPORT
# -----------------------------------------------------------------------------
def build_selected_cell_excel(full_row, selected_id):
    """Create a formatted Excel workbook for the currently selected grid cell."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Izbrana celica"
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A2"

    # Palette consistent with the public application.
    header_fill = PatternFill("solid", fgColor="5B9BD5")
    label_fill = PatternFill("solid", fgColor="DDEBF7")
    citation_fill = PatternFill("solid", fgColor="E2F0D9")
    white_font = Font(color="FFFFFF", bold=True)
    label_font = Font(color="1F4E78", bold=True)
    citation_font = Font(color="375623", italic=True)
    thin_blue = Side(style="thin", color="BDD7EE")
    bottom_border = Border(bottom=thin_blue)

    ws["A1"] = "Kazalnik"
    ws["B1"] = "Vrednost"
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = white_font
        cell.alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 24

    existing_export_fields = [
        field for field in EXPORT_FIELDS if field in full_row.index
    ]

    index_fields = {
        "final_mzi_action_index",
        "social_need_index",
        "green_blue_deficit_index",
        "strategic_priority_pre_feasibility_index",
        "heat_hazard_social_index",
    }

    row = 2
    for field in existing_export_fields:
        label = EXPORT_ALIASES.get(field, field)
        value = full_row[field]

        label_cell = ws.cell(row=row, column=1, value=label)
        value_cell = ws.cell(row=row, column=2)

        label_cell.fill = label_fill
        label_cell.font = label_font
        label_cell.alignment = Alignment(vertical="top", wrap_text=True)
        label_cell.border = bottom_border

        if pd.isna(value):
            value_cell.value = "—"
        elif field in {
            "cell_id",
            "final_mzi_action_class",
            "final_mzi_action_typology",
            "social_need_dominant_component",
            "mzi_gap_dominant_component",
        }:
            value_cell.value = str(value)
        elif field == "population_total":
            value_cell.value = int(round(float(value)))
            value_cell.number_format = "0"
        else:
            # Keep numeric values numeric so Excel cannot interpret e.g. 6.02 as a date.
            value_cell.value = float(value)

            if field in index_fields:
                value_cell.number_format = "0.000"
            elif field in PERCENT_FIELDS:
                value_cell.number_format = "0.00"
            elif field in TEMP_FIELDS:
                value_cell.number_format = "0.00"
            elif field in {"distance_to_water_m", "distance_to_major_water_m"}:
                value_cell.number_format = "0.0"
            elif field in {"road_width_mean_m", "building_height_mean_m"}:
                value_cell.number_format = "0.00"
            elif field == "built_volume_density_m3_m2":
                value_cell.number_format = "0.000"
            else:
                value_cell.number_format = "0.000"

        value_cell.alignment = Alignment(vertical="top", wrap_text=True)
        value_cell.border = bottom_border
        ws.row_dimensions[row].height = 21
        row += 1

    # Citation is part of every exported workbook.
    ws.cell(row=row, column=1, value="Citiranje podatkov")
    ws.cell(row=row, column=2, value=DATA_CITATION)
    ws.cell(row=row, column=1).fill = citation_fill
    ws.cell(row=row, column=2).fill = citation_fill
    ws.cell(row=row, column=1).font = Font(color="375623", bold=True)
    ws.cell(row=row, column=2).font = citation_font
    ws.cell(row=row, column=1).alignment = Alignment(vertical="top", wrap_text=True)
    ws.cell(row=row, column=2).alignment = Alignment(vertical="top", wrap_text=True)
    ws.row_dimensions[row].height = 58

    # Readable dimensions for a two-column, one-cell report.
    ws.column_dimensions["A"].width = 54
    ws.column_dimensions["B"].width = 92
    ws.auto_filter.ref = f"A1:B{row-1}"

    # Metadata in workbook properties.
    wb.properties.title = f"MZI - podatki celice {selected_id}"
    wb.properties.creator = "Ana Potočnik Buhvald"
    wb.properties.subject = "Rezultati prostorske opredelitve prednostnih območij za razvoj MZI"

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


BASEMAPS = {
    "Satelitski posnetek (Esri)": {
        "tiles": (
            "https://server.arcgisonline.com/ArcGIS/rest/services/"
            "World_Imagery/MapServer/tile/{z}/{y}/{x}"
        ),
        "attr": "Esri and imagery contributors",
        "max_zoom": 20,
    },
    "Topografska karta (Esri)": {
        "tiles": (
            "https://server.arcgisonline.com/ArcGIS/rest/services/"
            "World_Topo_Map/MapServer/tile/{z}/{y}/{x}"
        ),
        "attr": "Esri and contributors",
        "max_zoom": 20,
    },
    "Svetla siva karta (Esri)": {
        "tiles": (
            "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/"
            "World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"
        ),
        "attr": "Esri and contributors",
        "max_zoom": 16,
    },
}


# -----------------------------------------------------------------------------
# PRETTY MAP POPUP
# -----------------------------------------------------------------------------
class PrettyGeoJsonPopup(MacroElement):
    """Compact card-style popup bound to every feature in a Folium GeoJson layer."""

    _template = Template(
        r"""
        {% macro script(this, kwargs) %}
        {{ this._parent.get_name() }}.eachLayer(function(layer) {
            layer.on('click', function(e) {
                const p = layer.feature.properties || {};

                const escapeHtml = (value) => String(value ?? '—')
                    .replaceAll('&', '&amp;')
                    .replaceAll('<', '&lt;')
                    .replaceAll('>', '&gt;')
                    .replaceAll('"', '&quot;')
                    .replaceAll("'", '&#039;');

                const fmt = (value, digits=2) => {
                    if (value === null || value === undefined || value === '' || Number.isNaN(Number(value))) {
                        return '—';
                    }
                    return Number(value).toLocaleString('sl-SI', {
                        minimumFractionDigits: 0,
                        maximumFractionDigits: digits
                    });
                };

                const classStyles = {
                    'ni skupna prioriteta': ['#F1F3F4', '#657178'],
                    'zmerna razvojna prioriteta': ['#FFF6CF', '#856D00'],
                    'socialna prioriteta z zmernim MZI primanjkljajem': ['#FFF0E0', '#9A5700'],
                    'biofizikalna prioriteta': ['#E6F2F8', '#2D6E8C'],
                    'visoka skupna prioriteta': ['#FCE8E3', '#B54428'],
                    'ključna jedra ukrepanja': ['#F6E2E7', '#8D1731']
                };

                const cls = p.final_mzi_action_class || '—';
                const pill = classStyles[cls] || ['#EEF2F3', '#4D5A60'];
                const cellId = escapeHtml(p.cell_id);

                const html = `
                    <div class="mzi-popup-card">
                        <div class="mzi-popup-title-row">
                            <div class="mzi-popup-title">Celica ID: <strong>${cellId}</strong></div>
                        </div>

                        <div class="mzi-popup-pill"
                             style="background:${pill[0]}; color:${pill[1]};">
                            ${escapeHtml(cls)}
                        </div>

                        <div class="mzi-popup-coord-title">Koordinati (WGS84)</div>
                        <div class="mzi-popup-coord">
                            ${e.latlng.lat.toFixed(5)}, ${e.latlng.lng.toFixed(5)}
                        </div>

                        <div class="mzi-popup-divider"></div>

                        <div class="mzi-popup-section-title">Ključni kazalniki</div>

                        <div class="mzi-popup-row">
                            <span><span class="mzi-dot">•</span> Socialno-prostorska potreba</span>
                            <strong>${fmt(p.social_need_index, 2)}</strong>
                        </div>

                        <div class="mzi-popup-row">
                            <span><span class="mzi-dot">•</span> Biofizikalni primanjkljaj MZI</span>
                            <strong>${fmt(p.green_blue_deficit_index, 2)}</strong>
                        </div>

                        <div class="mzi-popup-row">
                            <span><span class="mzi-dot">•</span> Strateška prioriteta</span>
                            <strong>${fmt(p.strategic_priority_pre_feasibility_index, 2)}</strong>
                        </div>

                        <div class="mzi-popup-more">
                            <span class="mzi-popup-more-icon">⌄</span>
                            Poglej podrobnosti pod zemljevidom
                        </div>
                    </div>
                `;

                layer.bindPopup(html, {
                    maxWidth: 330,
                    minWidth: 290,
                    className: 'mzi-pretty-popup',
                    closeButton: true,
                    autoPan: true,
                    autoPanPadding: [28, 28]
                });
                layer.openPopup(e.latlng);
            });
        });
        {% endmacro %}
        """
    )


# -----------------------------------------------------------------------------
# STYLE
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    :root {
        --mzi-navy: #17324D;
        --mzi-teal: #2F6F73;
        --mzi-green: #5E8874;
        --mzi-soft-green: #EAF3EE;
        --mzi-soft-blue: #EDF5FA;
        --mzi-border: #DDE7E3;
        --mzi-muted: #667784;
        --mzi-bg: #F7FAF8;
        --mzi-white: #FFFFFF;
    }

    .stApp {
        background:
            radial-gradient(circle at 82% 0%, rgba(122, 167, 142, 0.12), transparent 28rem),
            linear-gradient(180deg, #FBFDFC 0%, #F5F9F7 100%);
        color: var(--mzi-navy);
    }

    .block-container {
        max-width: 1540px;
        padding-top: 2.0rem !important;
        padding-bottom: 2.2rem;
    }

    [data-testid="stHeader"] {
        background: rgba(255,255,255,0.82);
        backdrop-filter: blur(8px);
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(235,245,240,0.98) 0%, rgba(247,251,249,0.98) 100%);
        border-right: 1px solid #D8E5DF;
    }

    [data-testid="stSidebar"] .block-container {
        padding-top: 1.5rem !important;
    }

    .sidebar-brand {
        padding: 0.15rem 0.15rem 0.65rem 0.15rem;
        margin-bottom: 0.35rem;
        text-align: center;
    }

    .sidebar-brand img {
        max-width: 100%;
        height: auto;
    }

    .sidebar-nav {
        background: linear-gradient(90deg, #DDEEE7 0%, #EAF4F0 100%);
        border: 1px solid #D0E2DA;
        border-radius: 12px;
        padding: 11px 13px;
        margin: 0 0 1.2rem 0;
        color: #23495A;
        font-weight: 700;
        font-size: 0.97rem;
    }

    .sidebar-section-title {
        font-size: 0.88rem;
        font-weight: 800;
        color: #23495A;
        margin: 0.9rem 0 0.3rem 0;
        letter-spacing: 0.01em;
    }



    /* Compact category checkboxes: one row = checkbox + swatch + label + count */
    [data-testid="stSidebar"] [data-testid="stCheckbox"] {
        margin: 0 !important;
        padding: 0 !important;
    }

    [data-testid="stSidebar"] [data-testid="stCheckbox"] label {
        min-height: 31px !important;
        padding-top: 1px !important;
        padding-bottom: 1px !important;
        align-items: center !important;
    }

    [data-testid="stSidebar"] [data-testid="stCheckbox"] p {
        font-size: 0.84rem !important;
        line-height: 1.22 !important;
        color: #344955 !important;
        margin: 0 !important;
    }

    [data-testid="stSidebar"] .st-key-cat_0 p::before,
    [data-testid="stSidebar"] .st-key-cat_1 p::before,
    [data-testid="stSidebar"] .st-key-cat_2 p::before,
    [data-testid="stSidebar"] .st-key-cat_3 p::before,
    [data-testid="stSidebar"] .st-key-cat_4 p::before,
    [data-testid="stSidebar"] .st-key-cat_5 p::before {
        content: "";
        display: inline-block;
        width: 13px;
        height: 13px;
        border-radius: 4px;
        margin-right: 8px;
        vertical-align: -2px;
        border: 1px solid rgba(0,0,0,.14);
    }

    [data-testid="stSidebar"] .st-key-cat_0 p::before { background: #D9D9D9; }
    [data-testid="stSidebar"] .st-key-cat_1 p::before { background: #FFE66D; }
    [data-testid="stSidebar"] .st-key-cat_2 p::before { background: #FDAE61; }
    [data-testid="stSidebar"] .st-key-cat_3 p::before { background: #67A9CF; }
    [data-testid="stSidebar"] .st-key-cat_4 p::before { background: #F46D43; }
    [data-testid="stSidebar"] .st-key-cat_5 p::before { background: #A50026; }

    .sidebar-note {
        background: #EAF5FB;
        border: 1px solid #D4EAF6;
        border-radius: 10px;
        padding: 10px 12px;
        color: #3E6476;
        font-size: 0.82rem;
        line-height: 1.4;
        margin-top: 0.9rem;
    }

    .legend-row {
        display: flex;
        align-items: center;
        gap: 8px;
        margin: 2px 0 1px 0;
        font-size: 0.84rem;
    }

    .legend-swatch {
        width: 14px;
        height: 14px;
        border-radius: 4px;
        border: 1px solid rgba(0,0,0,.14);
        flex: 0 0 14px;
    }

    .mzi-hero {
        position: relative;
        overflow: hidden;
        border: 1px solid #DDE8E3;
        border-radius: 18px;
        padding: 1.35rem 1.55rem 1.2rem 1.55rem;
        margin-bottom: 1.0rem;
        background:
            radial-gradient(circle at 80% 35%, rgba(108,154,128,0.18), transparent 18rem),
            linear-gradient(110deg, rgba(255,255,255,0.98) 0%, rgba(244,250,247,0.96) 58%, rgba(233,243,237,0.92) 100%);
        box-shadow: 0 10px 28px rgba(31, 63, 52, 0.06);
    }

    .mzi-hero::after {
        content: "";
        position: absolute;
        right: -45px;
        top: -70px;
        width: 240px;
        height: 240px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(88,135,109,0.13), rgba(88,135,109,0));
        pointer-events: none;
    }

    .mzi-title {
        color: #142F49;
        font-size: clamp(2rem, 3.0vw, 2.7rem);
        line-height: 1.06;
        font-weight: 800;
        letter-spacing: -0.025em;
        margin-bottom: 0.45rem;
        max-width: 980px;
    }

    .mzi-subtitle {
        font-size: 1.03rem;
        line-height: 1.5;
        color: #5E7180;
        margin-bottom: 0;
        max-width: 1020px;
    }

    .mzi-subtitle em {
        color: #547486;
    }

    .logo-wrap {
        padding-top: 0.3rem;
        text-align: right;
    }

    .metric-card {
        min-height: 92px;
        border: 1px solid #DDE7E3;
        border-radius: 14px;
        padding: 13px 15px;
        background: rgba(255,255,255,0.96);
        box-shadow: 0 5px 18px rgba(29, 55, 47, 0.045);
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .metric-icon {
        width: 42px;
        height: 42px;
        border-radius: 11px;
        background: #EEF6F2;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #2E6970;
        font-size: 1.35rem;
        flex: 0 0 42px;
    }

    .metric-value {
        color: #17324D;
        font-size: 1.55rem;
        font-weight: 800;
        line-height: 1.0;
    }

    .metric-label {
        color: #6A7983;
        font-size: 0.79rem;
        margin-top: 5px;
    }

    .stTextInput input,
    div[data-baseweb="select"] > div {
        border-radius: 10px !important;
    }

    iframe {
        border-radius: 15px !important;
    }

    [data-testid="stIFrame"] {
        border-radius: 15px;
        overflow: hidden;
        border: 1px solid #DDE7E3;
        box-shadow: 0 10px 28px rgba(23,50,77,0.07);
    }

    [data-baseweb="tab-list"] {
        gap: 0.6rem;
    }

    [data-baseweb="tab"] {
        border-radius: 9px 9px 0 0;
    }

    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #E1E8E5;
    }

    [data-testid="stExpander"] {
        border: 1px solid #DEE8E3;
        border-radius: 12px;
        background: rgba(255,255,255,0.84);
    }

    .small-note {
        color: #737B88;
        font-size: 0.78rem;
        line-height: 1.35;
    }

    .footer {
        color: #6C7D82;
        font-size: 0.82rem;
    }

    .footer-card {
        margin-top: 1rem;
        border-top: 1px solid #DCE7E2;
        padding-top: 1rem;
    }

    @media (max-width: 900px) {
        .mzi-title { font-size: 2rem; }
        .metric-card { min-height: 82px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# DATA
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner="Nalaganje prostorskih podatkov …")
def load_data(path: str, file_version: int) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        raise ValueError("Vhodni sloj nima definiranega koordinatnega sistema.")

    # Web mapping uses WGS84.
    gdf = gdf.to_crs(epsg=4326)

    # Normalize selected numeric fields for cleaner popups and filters.
    for col in [
        "final_mzi_action_index",
        "social_need_index",
        "strategic_priority_pre_feasibility_index",
        "heat_hazard_social_index",
        "green_blue_deficit_index",
        "population_total",
        "tree_cover_300m_pct",
        "impervious_300m_pct",
    ]:
        if col in gdf.columns:
            gdf[col] = pd.to_numeric(gdf[col], errors="coerce")

    return gdf


@st.cache_data(ttl=86400, show_spinner=False)
def geocode_ljubljana_address(address: str):
    """
    Geocode a user-entered address in Ljubljana with OpenStreetMap Nominatim.

    The query is deliberately restricted to Slovenia and biased toward Ljubljana.
    Results are cached for 24 hours to avoid repeated requests for the same address.
    """
    geolocator = Nominatim(
        user_agent="mzi-priority-viewer-ul-fgg",
        timeout=10,
    )

    query = address.strip()
    if "ljubljana" not in query.casefold():
        query = f"{query}, Ljubljana, Slovenija"

    location = geolocator.geocode(
        query,
        exactly_one=True,
        country_codes="si",
        language="sl",
        addressdetails=True,
    )

    if location is None:
        return None

    return {
        "lat": float(location.latitude),
        "lon": float(location.longitude),
        "label": str(location.address),
    }


# Full source layer is retained for the "Vsi atributi izvornega sloja" tab.
gdf_full = load_data(
    str(DATA_PATH),
    DATA_PATH.stat().st_mtime_ns,
)

# Only selected attributes are sent to Folium, so the interactive map stays responsive.
map_keep = [c for c in DISPLAY_FIELDS if c in gdf_full.columns] + ["geometry"]
gdf = gdf_full[map_keep].copy()


# -----------------------------------------------------------------------------
# HEADER
# -----------------------------------------------------------------------------
st.markdown("<div class='mzi-hero'>", unsafe_allow_html=True)

col_title, col_logo = st.columns([5.7, 1.55], vertical_alignment="top")
with col_title:
    st.markdown(
        "<div class='mzi-title'>Prednostna območja za razvoj modro-zelene infrastrukture v Ljubljani</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
    """
    <div class='mzi-subtitle'>
        <strong>
            Kje se prekrivajo ponavljajoča se toplotna obremenitev,
            velika socialno-prostorska potreba in izrazit biofizikalni primanjkljaj MZI?
        </strong>
        <br>
        <span style="font-size:0.95rem;">
            <em>Interaktivni prostorski pregledovalnik rezultatov prostorske prioritizacije</em>
        </span>
    </div>
    """,
    unsafe_allow_html=True,
    )

with col_logo:
    if LOGO_PATH.exists():
        st.markdown("<div class='logo-wrap'>", unsafe_allow_html=True)
        st.image(str(LOGO_PATH), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# SIDEBAR CONTROLS
# -----------------------------------------------------------------------------
with st.sidebar:
    # Projektni logotip MZI Priority Viewer je prikazan na vrhu stranske vrstice.
    if MZI_LOGO_PATH.exists():
        st.markdown("<div class='sidebar-brand'>", unsafe_allow_html=True)
        st.image(str(MZI_LOGO_PATH), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='sidebar-nav'>⌂ &nbsp; Pregled</div>", unsafe_allow_html=True)

    st.markdown("<div class='sidebar-section-title'>Vnesi naslov</div>", unsafe_allow_html=True)

    with st.form("address_search_form", clear_on_submit=False):
        address_query = st.text_input(
            "Naslov",
            placeholder="Vnesi naslov, npr. Dunajska cesta 48 ...",
            label_visibility="collapsed",
        ).strip()

        address_search_submitted = st.form_submit_button(
            "⌕ Poišči naslov",
            use_container_width=True,
        )

    st.caption("Vnesi naslov ali klikni lokacijo na zemljevidu.")

    st.markdown("<div class='sidebar-section-title'>Prikaz kategorij</div>", unsafe_allow_html=True)
    selected_categories = []
    category_counts = gdf["final_mzi_action_class"].value_counts().to_dict()

    for i, category in enumerate(CATEGORY_ORDER):
        count = int(category_counts.get(category, 0))
        count_txt = f"{count:,}".replace(",", ".")

        if st.checkbox(
            f"{category} ({count_txt})",
            value=DEFAULT_VISIBLE[category],
            key=f"cat_{i}",
        ):
            selected_categories.append(category)

    st.markdown("<div class='sidebar-section-title'>Podlaga zemljevida</div>", unsafe_allow_html=True)
    basemap_name = st.selectbox(
        "Osnovna karta",
        options=list(BASEMAPS.keys()),
        index=0,
        label_visibility="collapsed",
    )

    with st.expander("Napredni filtri", expanded=False):
        typologies = sorted(gdf["final_mzi_action_typology"].dropna().unique().tolist())
        selected_typologies = st.multiselect(
            "Tipologija",
            options=typologies,
            default=[],
            help="Prazna izbira pomeni vse tipologije.",
        )

        if "final_mzi_action_index" in gdf.columns:
            min_idx = float(gdf["final_mzi_action_index"].min())
            max_idx = float(gdf["final_mzi_action_index"].max())
            index_range = st.slider(
                "Končni indeks ukrepanja",
                min_value=min_idx,
                max_value=max_idx,
                value=(min_idx, max_idx),
                step=0.01,
                format="%.2f",
            )
        else:
            index_range = None

    st.markdown(
        """
        <div class='sidebar-note'>
            ⓘ Lokacijo lahko poiščeš po naslovu ali jo izbereš neposredno s klikom na zemljevid.
            Razred »ni skupna prioriteta« je zaradi preglednosti privzeto izklopljen.
        </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# FILTER DATA
# -----------------------------------------------------------------------------
filtered = gdf.copy()

if selected_categories:
    filtered = filtered[filtered["final_mzi_action_class"].isin(selected_categories)]
else:
    filtered = filtered.iloc[0:0]

if selected_typologies:
    filtered = filtered[filtered["final_mzi_action_typology"].isin(selected_typologies)]

if index_range is not None and "final_mzi_action_index" in filtered.columns:
    lo, hi = index_range
    filtered = filtered[
        filtered["final_mzi_action_index"].between(lo, hi, inclusive="both")
    ]

# -----------------------------------------------------------------------------
# ADDRESS SEARCH
# -----------------------------------------------------------------------------
search_match = None
search_location = None
search_address_label = None

# Persist the last successful address search through normal Streamlit reruns.
if "searched_cell_id" not in st.session_state:
    st.session_state.searched_cell_id = None
if "searched_location" not in st.session_state:
    st.session_state.searched_location = None
if "searched_address_label" not in st.session_state:
    st.session_state.searched_address_label = None

if address_search_submitted:
    if not address_query:
        st.sidebar.warning("Vnesi naslov, ki ga želiš poiskati.")
    else:
        try:
            with st.spinner("Iskanje naslova ..."):
                geocoded = geocode_ljubljana_address(address_query)

            if geocoded is None:
                st.sidebar.warning(
                    "Naslova ni bilo mogoče najti. Poskusi vnesti ulico, hišno številko in kraj."
                )
                st.session_state.searched_cell_id = None
                st.session_state.searched_location = None
                st.session_state.searched_address_label = None
            else:
                point = Point(geocoded["lon"], geocoded["lat"])

                hit = gdf[
                    gdf.geometry.contains(point)
                    | gdf.geometry.touches(point)
                ]

                if hit.empty:
                    st.sidebar.warning(
                        "Naslov je bil najden, vendar leži zunaj analiziranega območja."
                    )
                    st.session_state.searched_cell_id = None
                    st.session_state.searched_location = (
                        geocoded["lat"],
                        geocoded["lon"],
                    )
                    st.session_state.searched_address_label = geocoded["label"]
                else:
                    found = hit.iloc[[0]].copy()
                    st.session_state.searched_cell_id = str(found.iloc[0]["cell_id"])
                    st.session_state.searched_location = (
                        geocoded["lat"],
                        geocoded["lon"],
                    )
                    st.session_state.searched_address_label = geocoded["label"]

        except (GeocoderTimedOut, GeocoderServiceError):
            st.sidebar.error(
                "Storitev za iskanje naslovov trenutno ni dosegljiva. Poskusi ponovno čez nekaj trenutkov."
            )
        except Exception:
            st.sidebar.error(
                "Pri iskanju naslova je prišlo do napake. Poskusi ponovno."
            )

if st.session_state.searched_cell_id:
    stored_id = st.session_state.searched_cell_id
    stored_match = gdf[gdf["cell_id"].astype(str) == str(stored_id)]

    if not stored_match.empty:
        search_match = stored_match.iloc[[0]].copy()

search_location = st.session_state.searched_location
search_address_label = st.session_state.searched_address_label

if search_match is not None and search_address_label:
    st.sidebar.success(
        f"Najdena lokacija: {search_address_label}"
    )


# -----------------------------------------------------------------------------
# SUMMARY METRICS
# -----------------------------------------------------------------------------
metric_cols = st.columns(4)
metrics = [
    ("▦", "Prikazane celice", f"{len(filtered):,}".replace(",", ".")),
    (
        "◎",
        "Ključna jedra",
        f"{int((filtered['final_mzi_action_class'] == 'ključna jedra ukrepanja').sum()):,}".replace(",", "."),
    ),
    (
        "↗",
        "Visoka prioriteta",
        f"{int((filtered['final_mzi_action_class'] == 'visoka skupna prioriteta').sum()):,}".replace(",", "."),
    ),
    ("◫", "Vse celice v sloju", f"{len(gdf):,}".replace(",", ".")),
]

for col, (icon, label, value) in zip(metric_cols, metrics):
    with col:
        st.markdown(
            f"""
            <div class='metric-card'>
                <div class='metric-icon'>{icon}</div>
                <div>
                    <div class='metric-value'>{value}</div>
                    <div class='metric-label'>{label}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# MAP
# -----------------------------------------------------------------------------
basemap = BASEMAPS[basemap_name]
m = folium.Map(
    location=[46.0569, 14.5058],
    zoom_start=13,
    tiles=None,
    control_scale=True,
    prefer_canvas=True,
)


# Styling inside the Folium/Leaflet iframe.
m.get_root().header.add_child(
    Element(
        r"""
        <style>
        .mzi-pretty-popup .leaflet-popup-content-wrapper {
            background: #ffffff;
            color: #294454;
            border-radius: 15px;
            padding: 0;
            box-shadow: 0 9px 30px rgba(20, 45, 60, 0.22);
            border: 1px solid rgba(43, 76, 91, 0.10);
        }

        .mzi-pretty-popup .leaflet-popup-content {
            margin: 0 !important;
            width: 292px !important;
        }

        .mzi-pretty-popup .leaflet-popup-tip {
            background: #ffffff;
            box-shadow: 3px 3px 8px rgba(20,45,60,0.08);
        }

        .mzi-pretty-popup a.leaflet-popup-close-button {
            top: 9px;
            right: 9px;
            width: 24px;
            height: 24px;
            color: #6B7F88;
            font-size: 21px;
            font-weight: 400;
            line-height: 22px;
        }

        .mzi-popup-card {
            box-sizing: border-box;
            padding: 14px 15px 13px 15px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            font-size: 12px;
            line-height: 1.32;
        }

        .mzi-popup-title-row {
            padding-right: 22px;
            margin-bottom: 7px;
        }

        .mzi-popup-title {
            color: #294454;
            font-size: 14px;
            font-weight: 700;
        }

        .mzi-popup-pill {
            display: inline-block;
            border-radius: 999px;
            padding: 5px 10px;
            margin-bottom: 10px;
            font-size: 10.5px;
            font-weight: 600;
            line-height: 1.1;
        }

        .mzi-popup-coord-title {
            color: #71818A;
            font-size: 10.5px;
            margin-bottom: 2px;
        }

        .mzi-popup-coord {
            color: #315C77;
            font-size: 11px;
            font-weight: 600;
        }

        .mzi-popup-divider {
            height: 1px;
            background: #E3EAED;
            margin: 9px 0 8px 0;
        }

        .mzi-popup-section-title {
            color: #294454;
            font-size: 11.5px;
            font-weight: 750;
            margin-bottom: 5px;
        }

        .mzi-popup-row {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 12px;
            padding: 2px 0;
            color: #5B7180;
            font-size: 10.5px;
        }

        .mzi-popup-row span:first-child {
            max-width: 210px;
        }

        .mzi-popup-row strong {
            color: #34586B;
            white-space: nowrap;
            font-weight: 700;
        }

        .mzi-dot {
            color: #2D6F78;
            font-size: 13px;
            margin-right: 3px;
        }

        .mzi-popup-more {
            margin-top: 10px;
            padding: 8px 10px;
            border-radius: 8px;
            background: linear-gradient(90deg, #EEF7F3 0%, #F3F8F6 100%);
            color: #3B6D62;
            font-size: 10.5px;
            font-weight: 650;
            text-align: left;
        }

        .mzi-popup-more-icon {
            display: inline-block;
            width: 16px;
            font-size: 14px;
            vertical-align: -1px;
        }
        </style>
        """
    )
)
folium.TileLayer(
    tiles=basemap["tiles"],
    attr=basemap["attr"],
    name=basemap_name,
    overlay=False,
    control=False,
    max_zoom=basemap["max_zoom"],
).add_to(m)

for category in CATEGORY_ORDER:
    part = filtered[filtered["final_mzi_action_class"] == category]
    if part.empty:
        continue

    color = CATEGORY_COLORS[category]
    fill_opacity = 0.14 if category == "ni skupna prioriteta" else (0.58 if category == "ključna jedra ukrepanja" else 0.40)
    weight = 0.5 if category == "ni skupna prioriteta" else (2.2 if category == "ključna jedra ukrepanja" else 1.2)

    fg = folium.FeatureGroup(name=f"{category} ({len(part):,})", show=True)

    geo = folium.GeoJson(
        data=part.__geo_interface__,
        name=category,
        style_function=lambda feature, _color=color, _fill=fill_opacity, _weight=weight: {
            "color": _color,
            "weight": _weight,
            "opacity": 0.95,
            "fillColor": _color,
            "fillOpacity": _fill,
        },
        highlight_function=lambda feature: {
            "color": "#111111",
            "weight": 3.5,
            "fillOpacity": 0.68,
        },
        tooltip=GeoJsonTooltip(
            fields=["cell_id", "final_mzi_action_class", "final_mzi_action_index"],
            aliases=["ID celice:", "Razred:", "Indeks ukrepanja:"],
            localize=True,
            sticky=False,
            labels=True,
        ),
        zoom_on_click=False,
    ).add_to(fg)

    PrettyGeoJsonPopup().add_to(geo)
    fg.add_to(m)

# Address search result is highlighted even when its category is currently hidden.
if search_match is not None:
    selected_id = str(search_match.iloc[0]["cell_id"])
    selected_category = str(search_match.iloc[0]["final_mzi_action_class"])

    search_geo = folium.GeoJson(
        data=search_match.__geo_interface__,
        name=f"Izbrana celica: {selected_id}",
        style_function=lambda feature: {
            "color": "#111111",
            "weight": 5,
            "fillColor": "#FFFF00",
            "fillOpacity": 0.25,
        },
        tooltip=GeoJsonTooltip(
            fields=["cell_id", "final_mzi_action_class"],
            aliases=["ID celice:", "Razred:"],
            sticky=False,
        ),
    ).add_to(m)
    PrettyGeoJsonPopup().add_to(search_geo)

    # Show the geocoded address as a point inside the selected 100 x 100 m cell.
    if search_location is not None:
        folium.Marker(
            location=[search_location[0], search_location[1]],
            tooltip=search_address_label or "Iskana lokacija",
            icon=folium.Icon(
                color="darkgreen",
                icon="map-marker",
                prefix="fa",
            ),
        ).add_to(m)

        m.location = [search_location[0], search_location[1]]
        m.options["zoom"] = 17
    else:
        sb = search_match.total_bounds
        m.fit_bounds(
            [[sb[1], sb[0]], [sb[3], sb[2]]],
            padding=(80, 80),
            max_zoom=18,
        )

    st.success(
        f"Najdena analitična celica: **{selected_id}** — {selected_category}"
    )

folium.LayerControl(collapsed=True, position="topright").add_to(m)

map_state = st_folium(
    m,
    use_container_width=True,
    height=800,
    returned_objects=["last_object_clicked"],
    key="mzi_priority_map_v2",
)


# -----------------------------------------------------------------------------
# SELECTED CELL DETAILS
# -----------------------------------------------------------------------------
selected_row = None

# A cell found through the search box takes precedence.
if search_match is not None:
    selected_row = search_match.iloc[0]

# Otherwise identify the grid cell from the last click on the map.
elif map_state and map_state.get("last_object_clicked"):
    clicked = map_state["last_object_clicked"]
    lat = clicked.get("lat")
    lng = clicked.get("lng")

    if lat is not None and lng is not None:
        click_point = Point(lng, lat)
        hit = gdf[
            gdf.geometry.contains(click_point)
            | gdf.geometry.touches(click_point)
        ]
        if not hit.empty:
            selected_row = hit.iloc[0]

if selected_row is not None:
    selected_id = str(selected_row.get("cell_id", ""))
    selected_class = str(selected_row.get("final_mzi_action_class", ""))

    # Retrieve the original feature with all source attributes.
    full_match = gdf_full[
        gdf_full["cell_id"].astype(str).str.casefold() == selected_id.casefold()
    ]
    full_row = full_match.iloc[0] if not full_match.empty else selected_row

    st.markdown(f"## Izbrana celica: `{selected_id}`")
    st.caption(f"Končni razred: {selected_class}")

    tab_key, tab_details = st.tabs(
        ["Ključni kazalniki", "Podrobnosti"]
    )

    def format_public_value(field, value):
        """Format a value for a non-technical public display."""
        if pd.isna(value):
            return "—"

        if field in PERCENT_FIELDS:
            return f"{float(value):.1f} %".replace(".", ",")

        if field in TEMP_FIELDS:
            return f"{float(value):.1f} °C".replace(".", ",")

        if field in {"distance_to_water_m", "distance_to_major_water_m"}:
            return f"{float(value):.0f} m".replace(".", ",")

        if field in {"road_width_mean_m", "building_height_mean_m"}:
            return f"{float(value):.1f} m".replace(".", ",")

        if field == "built_volume_density_m3_m2":
            return f"{float(value):.2f} m³/m²".replace(".", ",")

        if field == "population_total":
            return f"{int(round(float(value))):,}".replace(",", ".")

        if field in {
            "final_mzi_action_index",
            "social_need_index",
            "green_blue_deficit_index",
            "strategic_priority_pre_feasibility_index",
            "heat_hazard_social_index",
        }:
            return f"{float(value):.3f}".rstrip("0").rstrip(".").replace(".", ",")

        return str(value)

    with tab_key:
        key_fields = [
            "cell_id",
            "final_mzi_action_class",
            "final_mzi_action_typology",
            "social_need_index",
            "green_blue_deficit_index",
            "strategic_priority_pre_feasibility_index",
            "population_total",
            "tree_cover_300m_pct",
            "impervious_300m_pct",
        ]

        key_rows = []
        for field in key_fields:
            if field not in full_row.index:
                continue

            key_rows.append(
                {
                    "Kazalnik": FIELD_ALIASES.get(field, field),
                    "Vrednost": format_public_value(field, full_row[field]),
                }
            )

        st.dataframe(
            pd.DataFrame(key_rows),
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            "Ključni kazalniki so izbrani za hiter javni pregled. "
            "Podrobnejši prostorski in modelni podatki so v zavihku »Podrobnosti«."
        )

    with tab_details:
        st.caption(
            "Podrobnosti prikazujejo izbrane atribute, ki pomagajo pojasniti prostorske "
            "značilnosti, razvrstitev celice in modelirano toplotno obremenitev."
        )

        for group_title, fields in DETAIL_GROUPS.items():
            st.markdown(f"#### {group_title}")
            detail_rows = []

            for field, label in fields:
                if field not in full_row.index:
                    continue

                detail_rows.append(
                    {
                        "Kazalnik": label,
                        "Vrednost": format_public_value(field, full_row[field]),
                    }
                )

            if detail_rows:
                st.dataframe(
                    pd.DataFrame(detail_rows),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.caption("Za to skupino v izvornem sloju ni razpoložljivih podatkov.")

    # -------------------------------------------------------------------------
    # IZVOZ PODATKOV IZBRANE CELICE
    # -------------------------------------------------------------------------
    # Excel je uporabljen namesto oblikovanega CSV, ker CSV ne podpira barv,
    # širin stolpcev ali številskih formatov. Tako se tudi prepreči, da Excel
    # decimalne vrednosti (npr. 6.02 ali temperature) napačno razume kot datume.
    excel_selected = build_selected_cell_excel(full_row, selected_id)

    st.download_button(
        label="⬇ Izvozi podatke izbrane celice (Excel)",
        data=excel_selected,
        file_name=f"{selected_id}_MZI.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=False,
        key=f"download_{selected_id}",
    )

    st.caption(
        "Excel vsebuje izbrane kazalnike in podrobnosti trenutno izbrane celice."
    )

    st.markdown(
        f"""
        <div style="
            margin-top:0.4rem;
            padding:10px 12px;
            background:#F6F9F7;
            border-left:4px solid #5E8874;
            border-radius:8px;
            font-size:0.82rem;
            line-height:1.45;
            color:#5E6F78;
        ">
            <strong>Citiranje podatkov:</strong><br>
            {DATA_CITATION}
        </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# EXPLANATION / FOOTER
# -----------------------------------------------------------------------------
with st.expander("O interaktivnem prikazu", expanded=True):
    st.markdown(
        """
        **Interaktivni prikaz predstavlja strateško prostorsko usmeritev za prepoznavanje
        območij, kjer je razvoj modro-zelene infrastrukture (MZI) z vidika zmanjševanja
        urbanega pregrevanja posebej relevanten.** Prednostna območja niso določena zgolj
        glede na to, kje so površine najtoplejše, temveč predvsem tam, kjer se ponavljajoča
        toplotna obremenitev prekriva z veliko socialno-prostorsko potrebo in izrazitim
        biofizikalnim primanjkljajem MZI.

        Rezultati temeljijo na **empiričnih prostorskih podatkih**, večletnih satelitskih
        opazovanjih Landsat in ECOSTRESS iz obdobja **2018–2025** ter podatkih o prebivalstvu,
        rabi in pokrovnosti prostora, vegetaciji, neprepustnih površinah, grajeni strukturi
        in drugih značilnostih urbanega okolja. Analiza je izvedena na mreži **100 × 100 m**,
        kar omogoča primerjavo prostorskih razlik znotraj mesta in prepoznavanje območij,
        kjer se različne razsežnosti ranljivosti in primanjkljaja MZI prostorsko prekrivajo.

        **Rezultati ne določajo, kateri ukrep MZI je treba na posamezni lokaciji izvesti,
        temveč predvsem, kje je smiselno podrobnejšo prostorsko presojo začeti.** Pred
        konkretnim umeščanjem ukrepov je treba upoštevati še lastništvo zemljišč, namensko
        rabo prostora, obstoječo in načrtovano infrastrukturo, hidrološke in varstvene pogoje,
        razpoložljiv prostor ter druge lokalne tehnične in finančne omejitve.

        > **Ključno načelo:** prednostnih območij za razvoj MZI ni smiselno določati samo tam,
        > kjer je površje najtoplejše, temveč predvsem tam, kjer se ponavljajoča toplotna
        > obremenitev prekriva z veliko socialno-prostorsko potrebo in omejeno hladilno ponudbo prostora.
        """
    )


with st.expander("Kako interpretirati končno tipologijo", expanded=False):
    st.markdown(
        """
        Končna prioritizacija ni zasnovana kot preprosto kartiranje najtoplejših delov mesta.
        Prednost dobijo predvsem območja, kjer se hkrati pojavijo izrazitejša in ponavljajoča
        površinska toplotna obremenitev, velika socialno-prostorska potreba ter pomanjkanje
        obstoječih hladilnih elementov MZI.

        **Končna tipologija je strateška podpora prostorskemu načrtovanju in ne neposredna
        presoja izvedljivosti posameznega ukrepa.** Pred izvedbenim umeščanjem bi bilo treba
        preveriti še lastništvo zemljišč, namensko rabo prostora, obstoječo in načrtovano
        infrastrukturo, hidrološke in varstvene pogoje, razpoložljiv prostor ter druge lokalne
        tehnične in finančne omejitve.
        """
    )

st.markdown("<div class='footer-card'>", unsafe_allow_html=True)
footer_left, footer_right = st.columns([1.4, 1.0])
with footer_left:
    st.markdown(
        """
        <div class='footer'>
            <strong>Magistrsko delo:</strong><br>
            <em>Prostorska opredelitev prednostnih območij za razvoj modro-zelene infrastrukture
            za zmanjševanje urbanega pregrevanja</em><br>
            <a href="https://mzi-priority-viewer.streamlit.app/" target="_blank">Interaktivni pregledovalnik</a>
        </div>
        """,
        unsafe_allow_html=True,
    )
with footer_right:
    st.markdown(
        """
        <div class='footer' style='text-align:right'>
            <strong>Ana Potočnik Buhvald</strong><br>
            Univerza v Ljubljani, Fakulteta za gradbeništvo in geodezijo (UL FGG)<br>
            2026
        </div>
        """,
        unsafe_allow_html=True,
    )
st.markdown("</div>", unsafe_allow_html=True)

