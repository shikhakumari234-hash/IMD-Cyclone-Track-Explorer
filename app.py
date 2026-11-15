"""IMD Best Tracks 1982-2025: interactive cyclone track explorer.
Run:  pip install streamlit plotly pandas   then   streamlit run app.py
(keep imd_best_tracks_v4_master.csv and dashboard_data.py in the same folder)"""
import streamlit as st, plotly.graph_objects as go, pandas as pd
try:
    import dashboard_data as dd      # correct file name
except ModuleNotFoundError:
    import dashboard as dd           # works even if the file was saved as dashboard.py

st.set_page_config(page_title='IMD Cyclone Track Explorer', layout='wide')

@st.cache_data
def get_data():
    df = dd.load(); return df, dd.cyclone_table(df)
df, tab = get_data()


def show_table(d, height=380):
    """Plain HTML table. Avoids st.dataframe, which needs PyArrow (blocked by some Windows policies)."""
    html = d.to_html(index=False, border=0, na_rep='', float_format=lambda v: f'{v:g}')
    st.markdown(f'<div style="max-height:{height}px;overflow:auto;font-size:13px">{html}</div>', unsafe_allow_html=True)

BASIN_COL = {'Bay of Bengal':'#1d4e89','Arabian Sea':'#2a9d8f','Land-origin':'#c1440e'}
GRADE_COL = {'D':'#74c69d','DD':'#2a9df4','CS':'#f4d35e','SCS':'#f28c28','VSCS':'#e63946','ESCS':'#8d0f2f','SUCS':'#d291ff','<D':'#b7e4c7','wind missing':'#9e9e9e'}

# ---------------- sidebar: filters (each one narrows the table of cyclones) ----------------
st.sidebar.header('Filters')
years  = st.sidebar.slider('Year range', 1982, 2025, (1982, 2025))
basins = st.sidebar.multiselect('Basin (ARB+AS merged)', list(BASIN_COL), default=list(BASIN_COL))
grades = st.sidebar.multiselect('Peak intensity', dd.GRADES, default=dd.GRADES,
                                help='D<28kt, DD 28-33, CS 34-47, SCS 48-63, VSCS 64-89, ESCS 90-119, SuCS>=120 (from max wind)')
unk    = st.sidebar.checkbox('Include systems with unknown peak intensity', True)
color_by = st.sidebar.radio('Colour tracks by', ['basin','intensity'], horizontal=True)
sel_t = dd.apply_filters(tab, years, basins, grades, unk)
choice = st.sidebar.selectbox('Highlight one cyclone', ['(none)'] + sel_t.label.tolist())

# ---------------- header + summary numbers ----------------
st.title('IMD Best Tracks: Cyclone Track Explorer (1982-2025)')
c1, c2, c3, c4 = st.columns(4)
c1.metric('Cyclone systems', len(sel_t))
c2.metric('Observations', int(sel_t.n_obs.sum()))
c3.metric('Strongest wind (kt)', 'n/a' if sel_t.max_wind.isna().all() else int(sel_t.max_wind.max()))
c4.metric('Mean duration (days)', 'n/a' if sel_t.empty else round(sel_t.duration_days.mean(), 1))
st.caption('Counts are unique cyclone_id, not observations. Lines are not drawn across gaps >24 h or coordinate '
           'differences >5 deg (plotting breaks only; no observation is deleted).')

# ---------------- map ----------------
sub = df[df.cyclone_id.isin(sel_t.cyclone_id)]
fig = go.Figure()
cmap = BASIN_COL if color_by == 'basin' else GRADE_COL
for k, (la, lo) in dd.line_groups(sub, color_by).items():
    fig.add_trace(go.Scattergeo(lat=la, lon=lo, mode='lines', name=k, line=dict(width=1, color=cmap.get(k, '#555')),
                                opacity=.45 if choice != '(none)' else .8, hoverinfo='skip'))
if choice != '(none)':
    cid = sel_t.loc[sel_t.label == choice, 'cyclone_id'].iloc[0]; one = sub[sub.cyclone_id == cid]
    for _, p in one.groupby('piece'):
        fig.add_trace(go.Scattergeo(lat=p.lat, lon=p.lon, mode='lines+markers', showlegend=False,
            line=dict(width=3, color='black'), marker=dict(size=5, color='black'),
            text=[f'{t:%d %b %Y %H:%M} UTC<br>wind {w if pd.notna(w) else "n/a"} kt<br>ECP {e if pd.notna(e) else "n/a"} hPa<br>grade {g}'
                  for t, w, e, g in zip(p.datetime, p.wind_kt, p.ecp, p.grade_original)], hoverinfo='text'))
    fig.add_trace(go.Scattergeo(lat=[one.lat.iloc[0]], lon=[one.lon.iloc[0]], mode='markers', name='Start',
                                marker=dict(size=11, color='#2e7d32', line=dict(width=1, color='#000000'))))
    fig.add_trace(go.Scattergeo(lat=[one.lat.iloc[-1]], lon=[one.lon.iloc[-1]], mode='markers', name='End',
                                marker=dict(size=11, symbol='square', color='#c62828', line=dict(width=1, color='#000000'))))
fig.update_geos(lonaxis_range=[40, 105], lataxis_range=[0, 35], resolution=50, showcoastlines=True, showland=True,
                landcolor='#f1efe7', showocean=True, oceancolor='#dbe9f6', showcountries=True, countrycolor='#aaa')
fig.update_layout(height=620, margin=dict(l=0, r=0, t=0, b=0), legend=dict(title='Legend'))
st.plotly_chart(fig, use_container_width=True)

# ---------------- selected cyclone details ----------------
if choice != '(none)':
    r = sel_t[sel_t.cyclone_id == cid].iloc[0]
    st.subheader(f'{r.label}: {r.basin}')
    a, b, c, d = st.columns(4)
    a.metric('Peak intensity', r.peak_grade if pd.notna(r.peak_grade) else 'unknown')
    b.metric('Max wind (kt)', 'n/a' if pd.isna(r.max_wind) else int(r.max_wind))
    c.metric('Min ECP (hPa)', 'n/a' if pd.isna(r.min_ecp) else int(r.min_ecp))
    d.metric('Duration (days)', r.duration_days)
    f2 = go.Figure(go.Scatter(x=one.datetime, y=one.wind_kt, mode='lines+markers', name='Wind (kt)'))
    for lim, nm in [(34, 'CS'), (48, 'SCS'), (64, 'VSCS'), (90, 'ESCS'), (120, 'SuCS')]:
        f2.add_hline(y=lim, line_dash='dot', line_color='#999', annotation_text=nm, annotation_position='right')
    f2.update_layout(height=340, yaxis_title='Max sustained wind (kt)', xaxis_title='Date (UTC)', margin=dict(t=20))
    st.plotly_chart(f2, use_container_width=True)
    with st.expander('Observation table'):
        show_table(one[['datetime', 'lat', 'lon', 'wind_kt', 'ecp', 'grade_original', 'grade_from_wind', 'qc_action']])

# ---------------- statistics for the current filter ----------------
st.subheader('Statistics for the current selection')
l, rr = st.columns(2)
yr = sel_t.groupby(['year', 'basin']).size().unstack(fill_value=0)
l.plotly_chart(go.Figure([go.Bar(x=yr.index, y=yr[b], name=b, marker_color=BASIN_COL[b]) for b in yr.columns])
               .update_layout(barmode='stack', title='Systems per year', height=320, margin=dict(t=40)), use_container_width=True)
mo = sel_t.assign(m=sel_t.start.dt.month).groupby(['m', 'basin']).size().unstack(fill_value=0).reindex(range(1, 13), fill_value=0)
rr.plotly_chart(go.Figure([go.Bar(x=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'], y=mo[b], name=b, marker_color=BASIN_COL[b]) for b in mo.columns])
                .update_layout(barmode='stack', title='Systems per month (month of first observation)', height=320, margin=dict(t=40)), use_container_width=True)
with st.expander('Cyclone list (current selection)'):
    show_table(sel_t.drop(columns=['label']), 450)
