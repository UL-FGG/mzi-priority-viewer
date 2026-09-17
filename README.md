# MZI Priority Viewer

Repozitorij vsebuje Streamlit aplikacijo za interaktivni prikaz končnih prioritetnih območij za razvoj MZI ter GitHub Actions workflow za periodično prebujanje aplikacije.

## Struktura

```text
.github/
└── workflows/
    └── keep-awake.yml

mzi_priority_viewer/
├── .streamlit/
│   └── config.toml
├── data/
│   └── final_mzi_action_priority_aoi_ozje.gpkg
├── app.py
├── requirements.txt
├── README.md
└── UL_FGG-logoENG-HOR-RGB_color.png
```

Za navodila za deploy glej `mzi_priority_viewer/README.md`.
