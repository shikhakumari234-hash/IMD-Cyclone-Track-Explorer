# IMD Cyclone Track Explorer (1982-2025)
Interactive visualization tool for North Indian Ocean cyclone tracks (IMD Best Tracks).

- `app.py` : Streamlit dashboard (filters, map, cyclone statistics)
- `dashboard_data.py` : data loading, QC filters, track-break logic
- `imd_best_tracks_v4_master.csv` : validated master dataset (6,981 records; 6,977 used for tracks)
- Run locally: `pip install -r requirements.txt` then `python -m streamlit run app.py`
