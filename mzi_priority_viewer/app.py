from pathlib import Path

import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
from folium.features import GeoJsonPopup, GeoJsonTooltip
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
LOGO_PATH = BASE_DIR / "UL_FGG-logoENG-HOR-RGB_color.png"

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
    "mzi_gap_index_y",
    "strategic_priority_pre_feasibility_index",
    "heat_hazard_social_index",
    "green_blue_deficit_index",
    "population_total",
    "tree_cover_300m_pct_y",
    "impervious_300m_pct_y",
]

FIELD_ALIASES = {
    "cell_id": "ID celice",
    "final_mzi_action_index": "Končni indeks ukrepanja",
    "final_mzi_action_class": "Končni razred",
    "final_mzi_action_typology": "Tipologija",
    "social_need_index": "Indeks socialno-prostorske potrebe",
    "mzi_gap_index_y": "Indeks biofizikalnega primanjkljaja MZI",
    "strategic_priority_pre_feasibility_index": "Strateška prioriteta pred izvedljivostjo",
    "heat_hazard_social_index": "Indeks toplotne nevarnosti in socialne izpostavljenosti",
    "green_blue_deficit_index": "Primanjkljaj zelene-modre infrastrukture",
    "population_total": "Prebivalstvo v celici",
    "tree_cover_300m_pct_y": "Delež drevesnega pokrova v 300 m (%)",
    "impervious_300m_pct_y": "Delež neprepustnih površin v 300 m (%)",
}

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
# STYLE
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .block-container {
        max-width: 1500px;
        padding-top: 4.5rem !important;
        padding-bottom: 2rem;
    }
    .mzi-title {
        font-size: 2.25rem;
        line-height: 1.12;
        font-weight: 750;
        margin-bottom: 0.15rem;
    }
    .mzi-subtitle {
        font-size: 1.05rem;
        color: #687386;
        margin-bottom: 1rem;
    }
    .legend-row {
        display: flex;
        align-items: center;
        gap: 8px;
        margin: 3px 0;
        font-size: 0.88rem;
    }
    .legend-swatch {
        width: 15px;
        height: 15px;
        border-radius: 3px;
        border: 1px solid rgba(0,0,0,.22);
        flex: 0 0 15px;
    }
    .metric-card {
        border: 1px solid #e3e7ed;
        border-radius: 10px;
        padding: 10px 12px;
        background: #ffffff;
    }
    .metric-value {
        font-size: 1.45rem;
        font-weight: 750;
        line-height: 1.05;
    }
    .metric-label {
        color: #6b7280;
        font-size: 0.78rem;
        margin-top: 3px;
    }
    .small-note {
        color: #737b88;
        font-size: 0.78rem;
        line-height: 1.35;
    }
    .footer {
        color: #7a818b;
        font-size: 0.82rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# DATA
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner="Nalaganje prostorskih podatkov …")
def load_data(path: str) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        raise ValueError("Vhodni sloj nima definiranega koordinatnega sistema.")

    # Web mapping uses WGS84.
    gdf = gdf.to_crs(epsg=4326)

    # Normalize selected numeric fields for cleaner popups and filters.
    for col in [
        "final_mzi_action_index",
        "social_need_index",
        "mzi_gap_index_y",
        "strategic_priority_pre_feasibility_index",
        "heat_hazard_social_index",
        "green_blue_deficit_index",
        "population_total",
        "tree_cover_300m_pct_y",
        "impervious_300m_pct_y",
    ]:
        if col in gdf.columns:
            gdf[col] = pd.to_numeric(gdf[col], errors="coerce")

    return gdf


# Full source layer is retained for the "Vsi atributi izvornega sloja" tab.
gdf_full = load_data(str(DATA_PATH))

# Only selected attributes are sent to Folium, so the interactive map stays responsive.
map_keep = [c for c in DISPLAY_FIELDS if c in gdf_full.columns] + ["geometry"]
gdf = gdf_full[map_keep].copy()


# -----------------------------------------------------------------------------
# HEADER
# -----------------------------------------------------------------------------
col_title, col_logo = st.columns([5.5, 1.5], vertical_alignment="center")
with col_title:
    st.markdown(
        "<div class='mzi-title'>Končna prioritetna območja za razvoj modro-zelene infrastrukture v Ljubljani</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
    """
    <div class='mzi-subtitle'>
        Interaktivni prostorski pregledovalnik rezultatov magistrske naloge 
        <em>Prostorska opredelitev prednostnih območij za razvoj modro-zelene infrastrukture za zmanjševanje urbanega pregrevanja</em>
    </div>
    """,
    unsafe_allow_html=True,
    )
with col_logo:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), use_container_width=True)


# -----------------------------------------------------------------------------
# SIDEBAR CONTROLS
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("Prikaz")

    basemap_name = st.selectbox(
        "Osnovna karta",
        options=list(BASEMAPS.keys()),
        index=0,
    )

    st.subheader("Kategorije")
    selected_categories = []
    category_counts = gdf["final_mzi_action_class"].value_counts().to_dict()

    for i, category in enumerate(CATEGORY_ORDER):
        color = CATEGORY_COLORS[category]
        count = int(category_counts.get(category, 0))
        st.markdown(
            f"<div class='legend-row'><span class='legend-swatch' style='background:{color}'></span>"
            f"<span>{category} <span style='color:#8a929f'>({count:,})</span></span></div>",
            unsafe_allow_html=True,
        )
        if st.checkbox(
            "Prikaži",
            value=DEFAULT_VISIBLE[category],
            key=f"cat_{i}",
            label_visibility="collapsed",
        ):
            selected_categories.append(category)

    st.divider()
    st.subheader("Iskanje celice")
    cell_query = st.text_input(
        "cell_id",
        placeholder="npr. SIHM100_4598_1049",
        label_visibility="collapsed",
    ).strip()

    st.divider()
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

    st.caption(
        "Razred »ni skupna prioriteta« je privzeto izklopljen zaradi preglednosti. "
        "S klikom na celico se odprejo njeni kazalniki."
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

search_match = None
if cell_query:
    exact = gdf[gdf["cell_id"].astype(str).str.casefold() == cell_query.casefold()]
    if len(exact) == 1:
        search_match = exact.iloc[[0]].copy()
    elif len(exact) == 0:
        contains = gdf[
            gdf["cell_id"].astype(str).str.casefold().str.contains(cell_query.casefold(), regex=False)
        ]
        if len(contains) == 1:
            search_match = contains.iloc[[0]].copy()
        elif len(contains) > 1:
            st.sidebar.info(f"Najdenih je {len(contains)} delnih zadetkov. Vnesi natančnejši cell_id.")
        else:
            st.sidebar.warning("Celica s tem ID ni bila najdena.")


# -----------------------------------------------------------------------------
# SUMMARY METRICS
# -----------------------------------------------------------------------------
metric_cols = st.columns(4)
metrics = [
    ("Prikazane celice", f"{len(filtered):,}"),
    (
        "Ključna jedra",
        f"{int((filtered['final_mzi_action_class'] == 'ključna jedra ukrepanja').sum()):,}",
    ),
    (
        "Visoka prioriteta",
        f"{int((filtered['final_mzi_action_class'] == 'visoka skupna prioriteta').sum()):,}",
    ),
    ("Vse celice v sloju", f"{len(gdf):,}"),
]
for col, (label, value) in zip(metric_cols, metrics):
    with col:
        st.markdown(
            f"<div class='metric-card'><div class='metric-value'>{value}</div>"
            f"<div class='metric-label'>{label}</div></div>",
            unsafe_allow_html=True,
        )

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)


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
folium.TileLayer(
    tiles=basemap["tiles"],
    attr=basemap["attr"],
    name=basemap_name,
    overlay=False,
    control=False,
    max_zoom=basemap["max_zoom"],
).add_to(m)

popup_fields = [c for c in DISPLAY_FIELDS if c in gdf.columns]
popup_aliases = [FIELD_ALIASES.get(c, c) for c in popup_fields]

for category in CATEGORY_ORDER:
    part = filtered[filtered["final_mzi_action_class"] == category]
    if part.empty:
        continue

    color = CATEGORY_COLORS[category]
    fill_opacity = 0.14 if category == "ni skupna prioriteta" else (0.58 if category == "ključna jedra ukrepanja" else 0.40)
    weight = 0.5 if category == "ni skupna prioriteta" else (2.2 if category == "ključna jedra ukrepanja" else 1.2)

    fg = folium.FeatureGroup(name=f"{category} ({len(part):,})", show=True)

    folium.GeoJson(
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
        popup=GeoJsonPopup(
            fields=popup_fields,
            aliases=[f"{a}:" for a in popup_aliases],
            localize=True,
            labels=True,
            style="background-color: white; font-size: 12px;",
            max_width=520,
        ),
        zoom_on_click=False,
    ).add_to(fg)
    fg.add_to(m)

# Search result is always highlighted, even when its category is currently hidden.
if search_match is not None:
    selected_id = str(search_match.iloc[0]["cell_id"])
    selected_category = str(search_match.iloc[0]["final_mzi_action_class"])

    folium.GeoJson(
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
        popup=GeoJsonPopup(
            fields=popup_fields,
            aliases=[f"{a}:" for a in popup_aliases],
            localize=True,
            labels=True,
            max_width=520,
        ),
    ).add_to(m)

    sb = search_match.total_bounds
    m.fit_bounds([[sb[1], sb[0]], [sb[3], sb[2]]], padding=(80, 80), max_zoom=18)
    st.success(f"Izbrana celica: **{selected_id}** — {selected_category}")

folium.LayerControl(collapsed=True, position="topright").add_to(m)

map_state = st_folium(
    m,
    use_container_width=True,
    height=760,
    returned_objects=["last_object_clicked"],
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

    tab_key, tab_all = st.tabs(
        ["Ključni kazalniki", "Vsi atributi izvornega sloja"]
    )

    with tab_key:
        key_fields = [
            "cell_id",
            "final_mzi_action_index",
            "final_mzi_action_class",
            "final_mzi_action_typology",
            "social_need_index",
            "mzi_gap_index_y",
            "strategic_priority_pre_feasibility_index",
            "heat_hazard_social_index",
            "green_blue_deficit_index",
            "population_total",
            "tree_cover_300m_pct_y",
            "impervious_300m_pct_y",
        ]

        key_rows = []
        for field in key_fields:
            if field not in full_row.index:
                continue

            value = full_row[field]

            if pd.isna(value):
                display_value = "—"
            elif field in {"tree_cover_300m_pct_y", "impervious_300m_pct_y"}:
                display_value = f"{float(value):.1f} %"
            elif field == "population_total":
                display_value = f"{int(round(float(value))):,}"
            elif isinstance(value, (int, float)):
                display_value = f"{float(value):.3f}".rstrip("0").rstrip(".")
            else:
                display_value = str(value)

            key_rows.append(
                {
                    "Kazalnik": FIELD_ALIASES.get(field, field),
                    "Vrednost": display_value,
                }
            )

        st.dataframe(
            pd.DataFrame(key_rows),
            use_container_width=True,
            hide_index=True,
        )

    with tab_all:
        all_rows = []
        for field in gdf_full.columns:
            if field == "geometry":
                continue

            value = full_row.get(field)

            if pd.isna(value):
                display_value = "—"
            elif field in {"tree_cover_300m_pct_y", "impervious_300m_pct_y"}:
                display_value = f"{float(value):.1f} %"
            elif isinstance(value, float):
                display_value = f"{value:.6f}".rstrip("0").rstrip(".")
            else:
                display_value = str(value)

            all_rows.append(
                {
                    "Atribut": field,
                    "Vrednost": display_value,
                }
            )

        st.dataframe(
            pd.DataFrame(all_rows),
            use_container_width=True,
            hide_index=True,
            height=620,
        )


# -----------------------------------------------------------------------------
# EXPLANATION / FOOTER
# -----------------------------------------------------------------------------
with st.expander("O magistrskem delu in interaktivnem prikazu", expanded=True):
    st.markdown(
        """
        **Urbano pregrevanje je prostorsko heterogen pojav**, zato najtoplejše površine
        niso nujno tudi območja z največjo prednostjo za razvoj modro-zelene infrastrukture
        (MZI). Magistrsko delo na primeru Mestne občine Ljubljana razvija pregleden in
        ponovljiv prostorski pristop za prepoznavanje območij, kjer se ponavljajoča površinska
        toplotna obremenitev prekriva z veliko socialno-prostorsko potrebo po ukrepanju in
        izrazitim biofizikalnim primanjkljajem MZI.

        Analiza je izvedena na **mreži 100 × 100 m** in temelji na **174 poletnih satelitskih
        prizorih Landsat in ECOSTRESS iz obdobja 2018–2025**. Modularni metodološki okvir
        povezuje veččasovno oceno relativne površinske toplotne nevarnosti (Model 1A),
        pojasnjevalno-napovedno modeliranje LST z modeloma GAM in LightGBM (Model 1B),
        socialno-prostorsko potrebo po ukrepanju (Model 2A) ter biofizikalni primanjkljaj MZI
        (Model 2B). V zaključnem koraku sta socialno-prostorska in biofizikalna razsežnost
        povezani v končno tipologijo prednostnih območij.

        Interaktivna karta omogoča preklapljanje med končnimi razredi, iskanje posamezne
        analitične celice ter pregled ključnih kazalnikov in vseh atributov izvornega sloja.
        Namen prikaza je dopolniti statične karte magistrskega dela ter omogočiti podrobnejše
        prostorsko raziskovanje rezultatov na ravni posamezne celice.

        > Pri uporabi metodologije na drugi lokaciji bi bilo treba posamezne kazalnike, uteži in odločitvena
        > pravila prilagoditi lokalnim podatkom in prostorskim razmeram. Osnovno načelo pa
        > ostaja prenosljivo: prednostnih območij za razvoj MZI ni smiselno določati samo tam,
        > kjer je površje najtoplejše, temveč predvsem tam, kjer se ponavljajoča toplotna
        > obremenitev prekriva z veliko socialno-prostorsko potrebo in omejeno hladilno ponudbo
        > prostora.
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

st.markdown("---")
footer_left, footer_right = st.columns(2)
with footer_left:
    st.markdown(
        "<div class='footer'>Avtorica: Ana Potočnik Buhvald · Univerza v Ljubljani, UL FGG</div>",
        unsafe_allow_html=True,
    )
with footer_right:
    st.markdown(
        "<div class='footer' style='text-align:right'>© UL FGG, 2026</div>",
        unsafe_allow_html=True,
    )
