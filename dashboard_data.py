"""Data layer for the dashboard (pure pandas, no Streamlit/Plotly)."""
import os
import pandas as pd, numpy as np

MAX_GAP_H, MAX_COORD_DIFF_DEG = 24, 5
GRADES = ['D','DD','CS','SCS','VSCS','ESCS','SUCS']
BASIN_MAP = {'BOB':'Bay of Bengal','ARB':'Arabian Sea','AS':'Arabian Sea','LAND':'Land-origin'}

def load(path=None):
    # CSV is looked up next to this file, so it works locally and on Streamlit Cloud
    path = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'imd_best_tracks_v4_master.csv')
    df = pd.read_csv(path, parse_dates=['datetime'])
    df = df[df.use_for_plot].sort_values(['cyclone_id','datetime']).reset_index(drop=True)
    df['basin'] = df.cyclone_id.str.split('_').str[-1].map(BASIN_MAP)
    g = df.groupby('cyclone_id')
    df['gap_h'] = g.datetime.diff().dt.total_seconds()/3600
    df['cdiff'] = np.maximum(g.lat.diff().abs(), g.lon.diff().abs())
    df['piece'] = ((df.gap_h > MAX_GAP_H) | (df.cdiff > MAX_COORD_DIFF_DEG)).groupby(df.cyclone_id).cumsum()
    return df

def cyclone_table(df):
    """One row per cyclone_id (this is the unit we count)."""
    def peak(d):
        if d.wind_kt.notna().any(): return d.loc[d.wind_kt.idxmax(), 'grade_from_wind']
        gs = [x for x in d.grade_original.dropna() if x in GRADES]       # fallback: highest original grade (same as EDA)
        return max(gs, key=GRADES.index) if gs else np.nan
    rows = []
    for cid, d in df.groupby('cyclone_id'):
        nm = d.name.dropna()
        rows.append(dict(cyclone_id=cid, name=nm.iloc[0] if len(nm) else '', year=int(d.year.iloc[0]),
                         basin=d.basin.iloc[0], start=d.datetime.min(), end=d.datetime.max(),
                         n_obs=len(d), max_wind=d.wind_kt.max(), min_ecp=d.ecp.min(),
                         peak_grade=peak(d)))
    t = pd.DataFrame(rows)
    t['duration_days'] = ((t.end - t.start).dt.total_seconds()/86400).round(1)
    t['label'] = t.cyclone_id + t.name.apply(lambda s: f' ({s})' if s else '')
    return t

def apply_filters(t, years, basins, grades, include_unknown=True):
    m = t.year.between(*years) & t.basin.isin(basins)
    gm = t.peak_grade.isin(grades)
    if include_unknown: gm |= t.peak_grade.isna()
    return t[m & gm]

def line_groups(df, color_by='basin', COL=None):
    """Return {group: (lats, lons)} with None separators so Plotly draws ONE trace per group.
    Breaks (gap/coordinate-difference) are respected: no line is drawn across them."""
    out = {}
    def add(k, la, lo):
        a = out.setdefault(k, ([], []));  a[0].extend(la+[None]);  a[1].extend(lo+[None])
    for (cid, pc), p in df.groupby(['cyclone_id','piece']):
        if color_by == 'intensity':
            x, y, g = p.lon.tolist(), p.lat.tolist(), p.grade_from_wind.tolist()
            for i in range(len(p)-1):
                add(g[i] if isinstance(g[i], str) else 'wind missing', [y[i], y[i+1]], [x[i], x[i+1]])
        else:
            add(p.basin.iloc[0], p.lat.tolist(), p.lon.tolist())
    return out
