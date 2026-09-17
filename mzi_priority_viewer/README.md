# Interaktivni pregledovalnik prioritetnih območij MZI

Streamlit aplikacija za interaktivni pregled končne tipologije prednostnih območij za razvoj MZI na ožjem analitičnem območju.

## Funkcionalnosti

- šest končnih kategorij prioritetnih območij,
- vklop/izklop posameznih kategorij,
- iskanje po `cell_id`,
- klik na celico in prikaz ključnih kazalnikov,
- filtri po tipologiji in končnem indeksu ukrepanja,
- Esri satelitska, topografska in svetlo siva podlaga,
- poudarjanje iskane celice,
- osnovne sumarizacijske metrike.

## Lokalni zagon

Iz korena repozitorija:

```bash
pip install -r mzi_priority_viewer/requirements.txt
streamlit run mzi_priority_viewer/app.py
```

## Streamlit Community Cloud

Pri ustvarjanju nove aplikacije nastavi:

- **Repository:** ta GitHub repozitorij
- **Branch:** `main`
- **Main file path:** `mzi_priority_viewer/app.py`

Po prvem deployu kopiraj javni URL aplikacije in ga dodaj kot GitHub Actions repository variable:

- `MZI_STREAMLIT_URL`

Pot: **Settings → Secrets and variables → Actions → Variables → New repository variable**.

Workflow `.github/workflows/keep-awake.yml` nato na tri ure odpre aplikacijo s Playwrightom in po potrebi klikne Streamlitov gumb za ponovno prebujanje aplikacije.

## Podatki

Aplikacija bere:

`mzi_priority_viewer/data/final_mzi_action_priority_aoi_ozje.gpkg`

Če je repozitorij javen, je tudi ta datoteka javno dostopna prek GitHuba. Pred objavo preveri, ali je javna distribucija vhodnega sloja dovoljena.

## Avtorstvo

Ana Potočnik Buhvald  
Univerza v Ljubljani, Fakulteta za gradbeništvo in geodezijo (UL FGG), 2026
