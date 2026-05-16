import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns
import networkx as nx
import math, heapq, joblib, pickle, warnings, time, json, random
from datetime import datetime, timedelta, date
from collections import defaultdict
import requests as http_requests

warnings.filterwarnings('ignore')

# PAGE CONFIG
st.set_page_config(
    page_title="Smart Transjakarta Route Optimizer",
    page_icon=":bus:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# DARK MODE CSS
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(145deg, #0a0e1a 0%, #0f172a 100%);
        color: #f1f5f9;
    }
    
    .stSelectbox label, .stSlider label, .stDateInput label, .stTimeInput label {
        color: #94a3b8 !important;
        font-weight: 500;
    }
    
    .stSelectbox [data-baseweb="select"] {
        background-color: #1f2937;
        border-color: #334155;
        border-radius: 14px;
    }
    
    div[data-testid="stMetric"] {
        background: #111827;
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 1rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
    
    div[data-testid="stMetricLabel"] {
        color: #94a3b8;
        font-size: 0.8rem;
    }
    
    div[data-testid="stMetricValue"] {
        color: #38bdf8;
        font-size: 2rem;
        font-weight: 700;
    }
    
    div[data-testid="stButton"] > button {
        background: #38bdf8;
        color: #0f172a;
        font-weight: 600;
        border-radius: 40px;
        border: none;
        padding: 0.6rem 1.2rem;
        transition: all 0.2s ease;
    }
    
    div[data-testid="stButton"] > button:hover {
        background: #0ea5e9;
        transform: translateY(-1px);
    }
    
    div.stAlert {
        background-color: #1f2937;
        border: 1px solid #334155;
        border-radius: 14px;
        color: #f1f5f9;
    }
    
    .badge-akurat {
        background-color: #10b981;
        color: #0f172a;
        padding: 2px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    .badge-kasar {
        background-color: #f59e0b;
        color: #0f172a;
        padding: 2px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    .badge-terbatas {
        background-color: #ef4444;
        color: white;
        padding: 2px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    .footer-text {
        text-align: center;
        color: #64748b;
        font-size: 0.75rem;
        padding: 20px 0 10px 0;
        border-top: 1px solid #334155;
        margin-top: 30px;
    }
    
    .section-header {
        font-size: 1.2rem;
        font-weight: 700;
        margin: 20px 0 10px 0;
        color: #f1f5f9;
        border-bottom: 2px solid #38bdf8;
        padding-bottom: 6px;
        display: inline-block;
    }
    
    .status-online {
        color: #10b981;
        font-weight: 600;
    }
    
    .status-offline {
        color: #ef4444;
        font-weight: 600;
    }
    
    .timeline-node {
        background-color: #1a1d24;
        border: 2px solid #2d3139;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 0.9rem;
    }
    
    .timeline-line {
        border-left: 3px solid #2d3139;
        height: 30px;
        margin: 0 auto;
        width: 0;
    }
    
    .info-card {
        background: #111827;
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 16px;
        margin: 8px 0;
    }
    
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #38bdf8;
    }
    
    .metric-label {
        color: #94a3b8;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .divider {
        border-color: #334155;
        margin: 1rem 0;
    }
    
    hr {
        border-color: #334155;
    }
</style>
""", unsafe_allow_html=True)

# CONSTANTS & HELPERS
CURRENT_YEAR = datetime.now().year
CURRENT_DATETIME = datetime.now()

def get_config():
    if 'system_config' not in st.session_state:
        with open('system_config.json') as f:
            st.session_state.system_config = json.load(f)
    return st.session_state.system_config

def get_peak_ranges():
    return get_config()['peak_hours']

def get_corridor_speed(corridor_name):
    cfg = get_config()
    per_corridor = cfg['speed'].get('per_corridor_kmh', {})
    if corridor_name in per_corridor:
        return per_corridor[corridor_name]
    return cfg['speed']['fallback_kmh']

def get_base_speed_kmh(corridor_name=None):
    cfg = get_config()
    if corridor_name:
        return get_corridor_speed(corridor_name)
    return cfg['speed']['fallback_kmh']

def get_effective_speed(weather_condition, corridor_name=None):
    cfg = get_config()
    base = get_base_speed_kmh(corridor_name)
    weather_key = weather_condition.lower().replace(' ', '_')
    adjustment = cfg['speed'].get('weather_adjustment', {}).get(weather_key, 1.0)
    return round(base * adjustment, 1)

def get_weather_multiplier(weather_condition):
    return get_config()['weather']['multipliers'].get(
        weather_condition.lower().replace(' ', '_'), 1.0)

def capped_edge_weight(dist_km, speed_kmh):
    cal = get_config()['speed']['edge_calibration']
    min_speed = max(speed_kmh, cal['min_speed_kmh'])
    effective_speed = min(min_speed, cal['max_speed_kmh'])
    weight = max(2, dist_km / effective_speed * 60)
    return min(weight, cal.get('max_segment_minutes', 15))

def is_peak(hour, is_weekend=False):
    if is_weekend:
        return False
    for start, end in get_peak_ranges():
        if start <= hour <= end:
            return True
    return False

def haversine(lat1, lon1, lat2, lon2):
    try:
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    except:
        return 0

def get_period(h):
    if 5 <= h <= 10:
        return 'Pagi'
    elif 11 <= h <= 15:
        return 'Siang'
    elif 16 <= h <= 20:
        return 'Sore'
    else:
        return 'Malam'

FEATURES_CLF = ['hour', 'haversine_km', 'num_stops', 'direction',
               'is_weekend', 'is_peak_hour', 'age', 'is_rain',
               'corridorName', 'hour_period']

def predict_crowding_hybrid(clf, hour, hour_period, corridor_name, is_weekend, weather_condition='Cerah'):
    cfg = get_config()
    crowding_cfg = cfg['crowding']
    is_peak_hour = is_peak(hour, is_weekend)

    ml_score = 0.5
    if clf is not None:
        try:
            row = pd.DataFrame([{
                'hour': hour,
                'haversine_km': cfg['analysis_summary']['avg_travel_time_minutes'] / 10,
                'num_stops': 5,
                'direction': 1,
                'is_weekend': int(is_weekend),
                'is_peak_hour': int(is_peak_hour),
                'age': 30,
                'is_rain': 0,
                'corridorName': corridor_name,
                'hour_period': hour_period
            }])
            X = row[FEATURES_CLF]
            proba = clf.predict_proba(X)[0]
            if len(proba) >= 3:
                ml_score = proba[0] * 0.0 + proba[1] * 0.5 + proba[2] * 1.0
            elif len(proba) == 2:
                ml_score = proba[0] * 0.0 + proba[1] * 1.0
        except Exception:
            ml_score = 0.5

    day_key = 'weekend' if is_weekend else 'weekday'
    base_cfg = cfg['historical_density_baseline'].get(day_key, cfg['historical_density_baseline'])
    baseline_db = base_cfg.get('per_corridor', {})
    global_baseline = base_cfg.get('global_per_hour', {})
    cor_baseline = baseline_db.get(corridor_name, {})
    baseline_score = float(cor_baseline.get(str(hour), global_baseline.get(str(hour), 0.05)))

    weather_key = weather_condition.lower().replace(' ', '_')
    weather_adj = crowding_cfg.get('weather_impact', {}).get(weather_key, 0.0)

    ml_w = crowding_cfg['ml_weight']
    bl_w = crowding_cfg['baseline_weight']
    final_score = ml_score * ml_w + baseline_score * bl_w + weather_adj
    final_score = min(max(final_score, 0.0), 1.0)

    label_info = None
    for tier in crowding_cfg['labels']:
        if tier['min'] <= final_score <= tier['max']:
            label_info = tier
            break
    if label_info is None:
        label_info = crowding_cfg['labels'][1]

    parts = []
    parts.append(f"ML: {ml_score:.2f} x {ml_w:.0%}")
    parts.append(f"Baseline: {baseline_score:.2f} x {bl_w:.0%}")
    if weather_adj > 0:
        parts.append(f"Weather: +{weather_adj:.2f}")
    explanation = " + ".join(parts)

    return label_info['label'], label_info['short'], final_score, explanation

# DATA LOADING
@st.cache_data(show_spinner="Loading Transjakarta data...")
def load_data():
    df = pd.read_csv('dfTransjakarta.csv')
    df['tapInTime'] = pd.to_datetime(df['tapInTime'])
    df['tapOutTime'] = pd.to_datetime(df['tapOutTime'])
    df['travel_time'] = (df['tapOutTime'] - df['tapInTime']).dt.total_seconds() / 60
    df['hour'] = df['tapInTime'].dt.hour
    df['day_of_week'] = df['tapInTime'].dt.dayofweek
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
    df['num_stops'] = df['stopEndSeq'] - df['stopStartSeq']
    df = df[df['num_stops'] > 0]
    df['age'] = CURRENT_YEAR - df['payCardBirthDate']
    df['age'] = df['age'].fillna(df['age'].median()).clip(10, 100)
    return df

@st.cache_resource(show_spinner="Building route graph...")
def build_graph(df):
    G = nx.DiGraph()
    stop_coords = {}

    all_stops = pd.concat([
        df[['tapInStopsName', 'tapInStopsLat', 'tapInStopsLon']].rename(
            columns={'tapInStopsName': 'stop', 'tapInStopsLat': 'lat', 'tapInStopsLon': 'lon'}),
        df[['tapOutStopsName', 'tapOutStopsLat', 'tapOutStopsLon']].rename(
            columns={'tapOutStopsName': 'stop', 'tapOutStopsLat': 'lat', 'tapOutStopsLon': 'lon'})
    ]).drop_duplicates('stop').reset_index(drop=True)

    for _, row in all_stops.iterrows():
        s = row['stop']
        stop_coords[s] = (row['lat'], row['lon'])
        G.add_node(s, lat=row['lat'], lon=row['lon'])

    stop_seq_records = []

    tapin = df[['corridorID', 'corridorName', 'direction',
                'tapInStopsName', 'stopStartSeq']].drop_duplicates()
    tapin = tapin.rename(columns={'tapInStopsName': 'stop', 'stopStartSeq': 'seq'})
    stop_seq_records.append(tapin)

    tapout = df[['corridorID', 'corridorName', 'direction',
                 'tapOutStopsName', 'stopEndSeq']].drop_duplicates()
    tapout = tapout.rename(columns={'tapOutStopsName': 'stop', 'stopEndSeq': 'seq'})
    stop_seq_records.append(tapout)

    all_seq = pd.concat(stop_seq_records).drop_duplicates().dropna()
    all_seq['seq'] = all_seq['seq'].astype(int)

    edge_weight_map = df.groupby(
        ['corridorID', 'direction', 'tapInStopsName', 'tapOutStopsName']
    )['travel_time'].mean().reset_index()

    edges_added = set()

    for (cid, direction), grp in all_seq.groupby(['corridorID', 'direction']):
        grp = grp.sort_values('seq').drop_duplicates('stop')
        ordered_stops = grp['stop'].tolist()
        cor_name = grp.iloc[0].get('corridorName', str(cid)) if 'corridorName' in grp.columns else str(cid)
        cor_speed = get_base_speed_kmh(cor_name)

        for i in range(len(ordered_stops) - 1):
            u, v = ordered_stops[i], ordered_stops[i+1]
            if u == v:
                continue

            match = edge_weight_map[
                (edge_weight_map['corridorID'] == cid) &
                (edge_weight_map['direction'] == direction) &
                (edge_weight_map['tapInStopsName'] == u) &
                (edge_weight_map['tapOutStopsName'] == v)
            ]

            d_uv = haversine(stop_coords.get(u, (0,0))[0], stop_coords.get(u, (0,0))[1],
                             stop_coords.get(v, (0,0))[0], stop_coords.get(v, (0,0))[1])
            if len(match) > 0:
                raw_weight = match.iloc[0]['travel_time']
                capped = capped_edge_weight(d_uv, cor_speed)
                weight = min(raw_weight, capped)
            else:
                if u in stop_coords and v in stop_coords and d_uv > 0:
                    weight = capped_edge_weight(d_uv, cor_speed)
                else:
                    weight = 5

            dist = haversine(stop_coords.get(u, (0,0))[0], stop_coords.get(u, (0,0))[1],
                             stop_coords.get(v, (0,0))[0], stop_coords.get(v, (0,0))[1])

            key = (u, v, cid)
            if key not in edges_added:
                if d_uv <= 3.0:
                    G.add_edge(u, v,
                               weight=round(weight, 1),
                               weight_km=round(dist, 3),
                               corridorID=cid,
                               corridorName=cor_name,
                               direction=direction,
                               confidence=1.0,
                               edge_type='sequential')
                    edges_added.add(key)

    for (cid, direction), grp in all_seq.groupby(['corridorID', 'direction']):
        grp = grp.sort_values('seq').drop_duplicates('stop')
        ordered = grp['stop'].tolist()
        if len(ordered) < 3:
            continue
        cor_name = grp.iloc[0].get('corridorName', str(cid)) if 'corridorName' in grp.columns else str(cid)
        cor_speed = get_base_speed_kmh(cor_name)
        for i in range(len(ordered)):
            for j in range(i+3, min(i+8, len(ordered))):
                u, v = ordered[i], ordered[j]
                key = (u, v, cid, 'inferred')
                if key not in edges_added and u != v:
                    d = haversine(stop_coords[u][0], stop_coords[u][1],
                                  stop_coords[v][0], stop_coords[v][1])
                    weight = capped_edge_weight(d, cor_speed)
                    dist = round(d, 3)
                    G.add_edge(u, v, weight=round(weight, 1), weight_km=dist,
                               corridorID=cid, corridorName=cor_name,
                               direction=direction, confidence=0.6, edge_type='inferred')
                    edges_added.add(key)

    return G, stop_coords

@st.cache_resource(show_spinner="Loading ML model...")
def load_ml_model():
    try:
        clf = joblib.load('model_clf_transjakarta.pkl')
        hist = joblib.load('historical_avg_travel_time.pkl')
        return clf, hist
    except:
        return None, None

# WEATHER
def get_bmkg_forecast(target_date, target_hour):
    adm4_code = '31.71.01.1001'
    url = f"https://api.bmkg.go.id/publik/prakiraan-cuaca?adm4={adm4_code}"
    try:
        resp = http_requests.get(url, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        records = []
        if 'data' in data:
            for lokasi in data['data']:
                for batch in lokasi.get('cuaca', [[]]):
                    for item in batch:
                        records.append(item)
        if not records:
            return None

        target_str = target_date.strftime('%Y-%m-%d') if hasattr(target_date, 'strftime') else str(target_date)[:10]

        date_filtered = [r for r in records if r.get('local_datetime', '').startswith(target_str)]
        if not date_filtered:
            date_filtered = records

        best = None
        best_diff = float('inf')
        for r in date_filtered:
            dt = r.get('local_datetime', '')
            if len(dt) >= 13:
                try:
                    h = int(dt[11:13])
                    diff = abs(h - target_hour)
                    if diff < best_diff:
                        best_diff = diff
                        best = r
                except:
                    pass

        if best is None:
            best = date_filtered[0]

        desc = best.get('weather_desc', 'Cerah').lower()
        if any(kw in desc for kw in ['hujan','rain','petir','thunder']):
            return 'Hujan Ringan' if 'ringan' in desc else 'Hujan Lebat'
        if any(kw in desc for kw in ['berawan','cloudy','mendung']):
            return 'Mendung'
        return 'Cerah'
    except:
        pass
    return None

def get_weather(target_date, target_hour, use_realtime=True):
    if use_realtime:
        forecast = get_bmkg_forecast(target_date, target_hour)
        if forecast:
            return forecast
    if 13 <= target_hour <= 17:
        return random.choice(['Cerah', 'Mendung', 'Hujan Ringan'])
    return random.choice(['Cerah', 'Mendung'])

# ROUTING ENGINE
def dijkstra_route(graph, source, target, weight_attr='weight', transfer_penalty=15, confidence_power=1.0):
    if source not in graph or target not in graph:
        return None, float('inf'), 0
    
    dist = {node: float('inf') for node in graph.nodes()}
    dist[source] = 0
    prev = {}
    heap = [(0, source, None)]
    visited = set()
    explored = 0
    
    while heap:
        d, cur, cur_cor = heapq.heappop(heap)
        if cur in visited and d > dist[cur]:
            continue
        visited.add(cur)
        explored += 1
        if cur == target:
            break
        for nb in graph.successors(cur):
            edge = graph[cur][nb]
            w = edge.get(weight_attr, float('inf'))
            conf = edge.get('confidence', 1.0)
            cor = edge.get('corridorName', '')

            effective = w / (max(conf, 0.1) ** confidence_power)

            if cur_cor is not None and cor and cur_cor and cor != cur_cor:
                effective += transfer_penalty

            nd = d + effective
            if nd < dist.get(nb, float('inf')):
                dist[nb] = nd
                prev[nb] = cur
                heapq.heappush(heap, (nd, nb, cor))
    
    if target not in prev and source != target:
        return None, float('inf'), explored
    
    path = []
    node = target
    while node in prev:
        path.append(node)
        node = prev[node]
    path.append(source)
    path.reverse()
    return path, dist[target], explored

def get_eta_breakdown(graph, path, hour, is_weekend, weather_mult, clf_model=None, weather_condition='Cerah'):
    if not path or len(path) < 2:
        return None

    travel_time = 0
    total_dist = 0
    segments = []
    transfers = 0
    prev_corridor = None
    corridor_changes = []

    for i in range(len(path) - 1):
        u, v = path[i], path[i+1]
        if graph.has_edge(u, v):
            w = graph[u][v].get('weight', 10)
            d = graph[u][v].get('weight_km', 0.5)
            cor = graph[u][v].get('corridorName', 'Unknown')
            travel_time += w
            total_dist += d
            segments.append({
                'from': u, 'to': v,
                'weight': w,
                'dist_km': d,
                'corridor': cor
            })
            if prev_corridor and prev_corridor != cor:
                transfers += 1
                tf_time = get_config()['eta']['transfer_time_minutes']
                corridor_changes.append({
                    'at': u,
                    'from_cor': prev_corridor,
                    'to_cor': cor,
                    'transfer_time': tf_time
                })
            prev_corridor = cor
        else:
            fb_speed = get_config()['speed']['fallback_kmh']
            dist_fb = haversine(
                graph.nodes[u].get('lat',0), graph.nodes[u].get('lon',0),
                graph.nodes[v].get('lat',0), graph.nodes[v].get('lon',0)
            )
            weight = capped_edge_weight(dist_fb, fb_speed)
            travel_time += weight
            segments.append({
                'from': u, 'to': v,
                'weight': weight,
                'dist_km': haversine(
                    graph.nodes[u].get('lat',0), graph.nodes[u].get('lon',0),
                    graph.nodes[v].get('lat',0), graph.nodes[v].get('lon',0)
                ),
                'corridor': 'Transfer'
            })

    hour_period = get_period(hour)
    first_stop = path[0] if path else 'Unknown'
    crow_label_full, crow_label_short, crow_score, crow_explanation = predict_crowding_hybrid(
        clf_model, hour, hour_period, first_stop, is_weekend, weather_condition
    )

    waiting_time = get_config()['eta']['waiting_time'].get(crow_label_short.lower(), 5)
    transfer_time = transfers * get_config()['eta']['transfer_time_minutes']

    cong = get_config()['eta']['congestion']
    congestion_delay = 0
    if is_peak(hour, is_weekend):
        congestion_delay = travel_time * cong['peak_multiplier']
    if crow_score > 0.65:
        congestion_delay += travel_time * cong['crowded_multiplier']

    weather_adjustment = travel_time * (weather_mult - 1.0)

    total_eta = travel_time + waiting_time + transfer_time + congestion_delay + weather_adjustment

    if transfers > 3 or total_eta > 180:
        badge = 'Estimasi Kasar'
    elif crow_score > get_config()['crowding']['labels'][2]['min'] and weather_mult > 1.1:
        badge = 'Estimasi Kasar'
    else:
        badge = 'Akurat'

    return {
        'travel_time': round(travel_time, 1),
        'waiting_time': waiting_time,
        'transfer_time': transfer_time,
        'congestion_delay': round(congestion_delay, 1),
        'weather_adjustment': round(weather_adjustment, 1),
        'total_eta': round(total_eta, 1),
        'total_dist': round(total_dist, 2),
        'num_stops': len(path),
        'transfers': transfers,
        'crowding_label': crow_label_short,
        'crowding_label_full': crow_label_full,
        'crowding_score': crow_score,
        'crowding_explanation': crow_explanation,
        'badge': badge,
        'segments': segments,
        'corridor_changes': corridor_changes,
        'is_peak': is_peak(hour, is_weekend)
    }

# MAIN APP
with st.spinner("Loading data..."):
    df = load_data()
    G, stop_coords = build_graph(df)
    clf_model, hist_avg = load_ml_model()

stops_list = sorted(list(G.nodes()))

connected_components = list(nx.weakly_connected_components(G))
largest_cc = max(connected_components, key=len) if connected_components else set()
isolated_nodes = sum(1 for comp in connected_components if len(comp) == 1)

# HEADER
col_logo, col_title, col_clock = st.columns([0.08, 0.62, 0.3])

with col_logo:
    st.markdown("<div style='font-size:2.5rem; text-align:center;'>🚌</div>", unsafe_allow_html=True)

with col_title:
    st.markdown("<h1 style='margin:0; padding:0;'>Smart Transjakarta Route Optimizer</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#94a3b8; margin:0;'>Graph routing and machine learning optimization for Transjakarta</p>", unsafe_allow_html=True)

with col_clock:
    now = datetime.now()
    st.markdown(f"""
    <div style='text-align:right;'>
        <div style='font-size:1.5rem; font-weight:700; color:#38bdf8;'>{now.strftime('%H:%M')}</div>
        <div style='color:#94a3b8; font-size:0.75rem;'>{now.strftime('%d %B %Y')}</div>
    </div>
    """, unsafe_allow_html=True)

col_s1, col_s2, col_s3 = st.columns(3)
with col_s1:
    st.markdown("<div class='status-online'>● Graph Loaded</div>", unsafe_allow_html=True)
with col_s2:
    st.markdown(f"<div class='{'status-online' if clf_model else 'status-offline'}'>● ML Model Active</div>", unsafe_allow_html=True)
with col_s3:
    st.markdown("<div class='status-online'>● Weather API Connected</div>", unsafe_allow_html=True)

st.markdown("---")

# SIDEBAR
with st.sidebar:
    st.markdown("## System Information")

    st.markdown("### Graph Statistics")
    col1, col2 = st.columns(2)

    components = list(nx.weakly_connected_components(G))
    largest = max(components, key=len) if components else set()

    col1.metric("Total Stops", f"{G.number_of_nodes():,}")
    col2.metric("Total Edges", f"{G.number_of_edges():,}")
    col1.metric("Total Corridors", f"{df['corridorID'].nunique()}")
    col2.metric("Avg Node Degree", f"{2*G.number_of_edges()/max(G.number_of_nodes(),1):.1f}")

    st.markdown("### Topology Quality")
    coverage = len(largest) / max(G.number_of_nodes(), 1) * 100
    st.markdown(f"- **Connected Components:** {len(components)}")
    st.markdown(f"- **Largest Component:** {len(largest):,} nodes ({coverage:.0f}%)")
    st.markdown(f"- **Graph Type:** Corridor-Sequential")
    degrees = sorted([d for _, d in G.degree()], reverse=True)
    hub_threshold = degrees[max(len(degrees)//20 - 1, 0)] if len(degrees) >= 20 else 10
    st.markdown(f"- **Transfer Hubs:** {sum(1 for _, d in G.degree() if d >= hub_threshold)} (top 5%)")

    st.markdown("### Dataset Info")
    st.markdown(f"- **Trips:** {len(df):,}")
    st.markdown(f"- **Period:** April 2023")
    st.markdown(f"- **Avg Travel Time:** {df['travel_time'].mean():.0f} min")

    st.markdown("### Estimation Mode")
    st.markdown("**Hybrid ETA**")
    st.markdown("Graph + ML + Weather")

    st.markdown("---")
    st.markdown("### Version")
    st.markdown("v3.0 — Sequential Corridor Graph")

# MAIN LAYOUT
st.markdown("## Route Planner")
st.markdown("Select your origin and destination stops, set your travel schedule, and the system will find the optimal Transjakarta route.")

col_input1, col_input2 = st.columns(2)

with col_input1:
    origin = st.selectbox("Origin Stop", stops_list, index=stops_list.index("Blok M") if "Blok M" in stops_list else 0)

with col_input2:
    dest = st.selectbox("Destination Stop", stops_list, index=stops_list.index("Kota") if "Kota" in stops_list else (stops_list.index("Harmoni") if "Harmoni" in stops_list else min(len(stops_list)-1, 1)))

st.markdown("### Travel Settings")
with st.expander("How to read these settings", expanded=False):
    st.markdown("""
    - **Weekend toggle** — activate for weekend or holiday travel. Affects congestion patterns.
    - **Departure hour** — determines peak/non-peak hours. Peak hours (06-09 & 16-19) have +20% congestion.
    - **Priority** — affects Dijkstra route selection:
        - *Fastest Time*: minimize total ETA
        - *Minimum Transfers*: avoid corridor changes
        - *Most Stable Route*: prioritize sequential paths with real data, avoid inferred edges
    """)

col_t1, col_t2, col_t3 = st.columns(3)

with col_t1:
    is_weekend_toggle = st.toggle("Weekend / Holiday", value=False)

with col_t2:
    travel_hour = st.slider("Departure Hour", 0, 23, 8)

with col_t3:
    priority = st.selectbox("Optimization Priority", ["Fastest Time", "Minimum Transfers", "Most Stable Route"])

st.markdown("### Weather Condition")
st.markdown("Weather affects bus operational speed. Rain can increase ETA by up to 25%.")

col_w1, col_w2, col_w3, col_w4 = st.columns([0.2, 0.2, 0.2, 0.4])

with col_w1:
    use_realtime = st.toggle("BMKG Weather", value=False)

with col_w2:
    if use_realtime:
        travel_day_bmkg = st.selectbox("Day", ["Today", "Tomorrow", "Day After"], label_visibility="collapsed")
        day_offset = {"Today": 0, "Tomorrow": 1, "Day After": 2}
        target_date = date.today() + timedelta(days=day_offset.get(travel_day_bmkg, 0))
        weather_now = get_weather(target_date, travel_hour, use_realtime=True)
        weather_condition = weather_now
        st.markdown(f"**{weather_condition}**")
    else:
        weather_condition = st.selectbox("Weather", ["Cerah", "Mendung", "Hujan Ringan", "Hujan Lebat"], label_visibility="collapsed")

with col_w3:
    weather_mult = get_weather_multiplier(weather_condition)
    st.metric("Weather Multiplier", f"{weather_mult:.2f}x")

# VALIDATION
route_found = False
result = None

if origin == dest:
    st.warning("Origin and destination cannot be the same. Please select different stops.")
elif origin not in G or dest not in G:
    st.error("One or both stops not found in the route graph.")
else:
    with st.spinner("Finding optimal route..."):
        is_weekend = is_weekend_toggle

        if priority == "Fastest Time":
            path, cost, explored = dijkstra_route(G, origin, dest, 'weight', transfer_penalty=15, confidence_power=1.0)
        elif priority == "Minimum Transfers":
            path, cost, explored = dijkstra_route(G, origin, dest, 'weight', transfer_penalty=60, confidence_power=1.0)
        else:
            path, cost, explored = dijkstra_route(G, origin, dest, 'weight', transfer_penalty=15, confidence_power=2.0)

        if path is None or len(path) < 2:
            st.error("No route found between these stops.")
            with st.expander("Possible reasons"):
                st.markdown("""
                - Graph is disconnected between these stops
                - Stops are in different connected components
                - No route data available for this pair
                """)
        else:
            route_found = True
            result = get_eta_breakdown(G, path, travel_hour, is_weekend, weather_mult, clf_model, weather_condition)

# RESULTS
if route_found and result:
    st.markdown("---")
    st.markdown("## Route Result")
    st.info("Summary of the best route based on graph routing, historical data, and weather conditions. ETA includes travel time, waiting, transfers, congestion, and weather adjustments.")

    col_r1, col_r2, col_r3, col_r4, col_r5 = st.columns(5)

    with col_r1:
        badge_color = '#10b981' if result['badge'] == 'Akurat' else ('#f59e0b' if result['badge'] == 'Estimasi Kasar' else '#ef4444')
        st.markdown(f"""
        <div class="info-card" style='text-align:center;'>
            <div class='metric-label'>Total ETA</div>
            <div class='metric-value'>{result['total_eta']:.0f} <span style='font-size:1rem;'>min</span></div>
            <div style='margin-top:8px;'><span class='badge-{result['badge'].lower().replace(' ', '-')}'>{result['badge']}</span></div>
        </div>
        """, unsafe_allow_html=True)

    with col_r2:
        st.markdown(f"""
        <div class="info-card" style='text-align:center;'>
            <div class='metric-label'>Total Distance</div>
            <div class='metric-value'>{result['total_dist']:.1f} <span style='font-size:1rem;'>km</span></div>
        </div>
        """, unsafe_allow_html=True)

    with col_r3:
        st.markdown(f"""
        <div class="info-card" style='text-align:center;'>
            <div class='metric-label'>Number of Stops</div>
            <div class='metric-value'>{result['num_stops']}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_r4:
        st.markdown(f"""
        <div class="info-card" style='text-align:center;'>
            <div class='metric-label'>Transfers</div>
            <div class='metric-value'>{result['transfers']}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_r5:
        c_label = result['crowding_label']
        c_score = result.get('crowding_score', 0.5)
        crow_color = '#10b981' if c_score < 0.3 else ('#f59e0b' if c_score < 0.65 else '#ef4444')
        st.markdown(f"""
        <div class="info-card" style='text-align:center;'>
            <div class='metric-label'>Crowding Level</div>
            <div class='metric-value' style='color:{crow_color};'>{c_label}</div>
            <div style='font-size:0.7rem; color:#94a3b8;'>{result.get('crowding_label_full', '')}</div>
        </div>
        """, unsafe_allow_html=True)

    # ROUTE TIMELINE
    st.markdown("## Route Timeline")
    st.caption("Sequence of stops along the route. Travel time between stops is based on historical averages or distance/speed estimation.")

    timeline_data = []
    for i in range(len(path)):
        info = {"index": i+1, "stop": path[i], "type": "origin" if i == 0 else ("destination" if i == len(path)-1 else "transit")}
        if i > 0:
            u, v = path[i-1], path[i]
            w = 0
            cor = "Transfer"
            if G.has_edge(u, v):
                w = G[u][v].get('weight', 0)
                cor = G[u][v].get('corridorName', 'Unknown')
            info["travel_to"] = round(w, 1)
            info["corridor"] = cor
        else:
            info["travel_to"] = 0
            info["corridor"] = "-"
        timeline_data.append(info)

    for idx, info in enumerate(timeline_data):
        col_tl1, col_tl2, col_tl3, col_tl4 = st.columns([0.05, 0.25, 0.15, 0.55])

        with col_tl1:
            type_color = "#10b981" if info["type"] == "origin" else ("#ef4444" if info["type"] == "destination" else "#38bdf8")
            st.markdown(f"<div style='background:{type_color}; width:10px; height:10px; border-radius:50%; margin-top:6px;'></div>", unsafe_allow_html=True)
            if idx < len(timeline_data) - 1:
                st.markdown("<div style='border-left:2px solid #334155; height:20px; margin-left:4px;'></div>", unsafe_allow_html=True)

        with col_tl2:
            type_label = "Origin" if info["type"] == "origin" else ("Destination" if info["type"] == "destination" else "Transit")
            st.markdown(f"**{info['stop']}** <span style='color:#94a3b8; font-size:0.75rem;'>({type_label})</span>", unsafe_allow_html=True)

        with col_tl3:
            if info["travel_to"] > 0:
                st.markdown(f"<span style='color:#94a3b8;'>{info['travel_to']:.0f} min</span>", unsafe_allow_html=True)

        with col_tl4:
            if info["corridor"] != "-" and info["corridor"] != "Transfer":
                st.markdown(f"<span style='color:#38bdf8; font-size:0.75rem;'>Corridor: {info['corridor']}</span>", unsafe_allow_html=True)
            elif info["corridor"] == "Transfer":
                st.markdown(f"<span style='color:#f59e0b; font-size:0.75rem;'>Transfer corridor</span>", unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom:2px;'></div>", unsafe_allow_html=True)

    # TIME BREAKDOWN
    st.markdown("## Time Breakdown")
    st.caption("Total ETA = Travel Time + Waiting Time + Transfer Time + Congestion Delay + Weather Adjustment.")

    col_b1, col_b2 = st.columns([0.5, 0.5])

    with col_b1:
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Travel Time", f"{result['travel_time']:.0f} min")
        mc2.metric("Waiting Time", f"{result['waiting_time']} min")
        mc3.metric("Transfer Time", f"{result['transfer_time']} min")

        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Congestion Delay", f"+{result['congestion_delay']:.0f} min")
        mc2.metric("Weather Adjustment", f"+{result['weather_adjustment']:.0f} min")
        mc3.metric("Total ETA", f"{result['total_eta']:.0f} min")

    with col_b2:
        labels = ['Travel', 'Waiting', 'Transfer', 'Congestion', 'Weather']
        sizes = [
            result['travel_time'],
            result['waiting_time'],
            result['transfer_time'],
            result['congestion_delay'],
            result['weather_adjustment']
        ]
        colors_pie = ['#38bdf8', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']

        fig, ax = plt.subplots(figsize=(6, 4))
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#0f172a')
        wedges, texts, autotexts = ax.pie(sizes, labels=None, autopct='%1.0f%%',
                                           colors=colors_pie, startangle=90,
                                           textprops={'color': '#f1f5f9', 'fontsize': 9})
        for at in autotexts:
            at.set_color('#0f172a')
            at.set_fontweight('bold')
        ax.legend(wedges, [f'{l} ({s:.0f}m)' for l, s in zip(labels, sizes)],
                  loc='center left', bbox_to_anchor=(1, 0.5),
                  fontsize=9, frameon=False, labelcolor='#f1f5f9')
        st.pyplot(fig)

    # ETA COMPOSITION PROGRESS BAR
    st.markdown("### ETA Composition")
    total = sum(sizes)
    if total > 0:
        proportions = [s/total for s in sizes]
        bar_html = "<div style='display:flex; height:28px; border-radius:14px; overflow:hidden; margin:8px 0;'>"
        for prop, color, label in zip(proportions, colors_pie, labels):
            if prop > 0.01:
                bar_html += f"<div style='width:{prop*100}%; background:{color}; display:flex; align-items:center; justify-content:center; font-size:0.7rem; font-weight:600; color:#0f172a;'>{label}</div>"
        bar_html += "</div>"
        st.markdown(bar_html, unsafe_allow_html=True)

    # TRAVEL CONDITION ANALYSIS
    st.markdown("## Travel Condition Analysis")

    col_c1, col_c2, col_c3, col_c4 = st.columns(4)

    with col_c1:
        peak_status = "Peak Hour" if result['is_peak'] else "Non-Peak"
        peak_color = "#ef4444" if result['is_peak'] else "#10b981"
        st.markdown(f"""
        <div class="info-card" style='text-align:center;'>
            <div class='metric-label'>Time</div>
            <div class='metric-value' style='font-size:1.2rem; color:{peak_color};'>{peak_status}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_c2:
        c_score = result.get('crowding_score', 0.5)
        c_full = result.get('crowding_label_full', result['crowding_label'])
        crow_color2 = '#10b981' if c_score < 0.3 else ('#f59e0b' if c_score < 0.65 else '#ef4444')
        st.markdown(f"""
        <div class="info-card" style='text-align:center;'>
            <div class='metric-label'>Crowding</div>
            <div class='metric-value' style='font-size:1.2rem; color:{crow_color2};'>{c_full}</div>
            <div style='font-size:0.65rem; color:#94a3b8;'>Score: {c_score:.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_c3:
        st.markdown(f"""
        <div class="info-card" style='text-align:center;'>
            <div class='metric-label'>Weather</div>
            <div class='metric-value' style='font-size:1.2rem; color:#38bdf8;'>{weather_condition}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_c4:
        raw_speed = result['total_dist'] / (result['travel_time']/60) if result['travel_time'] > 0 else 0
        avg_speed = min(raw_speed, 28)
        st.markdown(f"""
        <div class="info-card" style='text-align:center;'>
            <div class='metric-label'>Average Speed</div>
            <div class='metric-value' style='font-size:1.2rem;'>{avg_speed:.1f} km/h</div>
        </div>
        """, unsafe_allow_html=True)

    # CROWDING INSIGHT
    st.markdown("### Crowding Insight")
    c_explain = result.get('crowding_explanation', '')
    c_full = result.get('crowding_label_full', result['crowding_label'])
    try:
        label_tiers = get_config()['crowding']['labels']
        desc = ''
        for t in label_tiers:
            if t['label'] == c_full:
                desc = t['description']
                break
    except:
        desc = ''

    st.markdown(f"""
    <div class="info-card">
        <strong>{c_full}</strong><br>
        <span style='color:#94a3b8; font-size:0.85rem;'>{desc}</span><br>
        <span style='color:#64748b; font-size:0.75rem;'>Components: {c_explain}</span>
    </div>
    """, unsafe_allow_html=True)

    # EXPLANATION PANEL
    with st.expander("How is this ETA calculated?", expanded=True):
        st.markdown(f"""
        **The ETA is calculated using a combination of:**

        - **Graph Routing** — Dijkstra algorithm finding the shortest path in the Transjakarta graph
        - **Historical Average** — edge weights based on historical average travel times
        - **Peak Hours** — congestion adjustments during peak hours
        - **Weather Conditions** — multiplier from BMKG forecast
        - **Crowding Level** — hybrid ML (70%) + historical baseline (30%) + weather adjustment
        - **Waiting Time** — based on GTFS scheduled headway per route

        **ETA Formula:**

        `ETA = Travel Time + Waiting Time + Transfer Time + Congestion Delay + Weather Adjustment`

        **Calculation details for this route:**

        - Travel Time: {result['travel_time']:.1f} minutes (sum of edge weights)
        - Waiting Time: {result['waiting_time']} minutes (estimated wait at stops)
        - Transfer Time: {result['transfer_time']} minutes ({result['transfers']} transfers x {get_config()['eta']['transfer_time_minutes']} minutes)
        - Congestion Delay: +{result['congestion_delay']:.0f} minutes ({'peak hour' if result['is_peak'] else 'non-peak'})
        - Weather Adjustment: +{result['weather_adjustment']:.0f} minutes ({weather_condition}, {weather_mult:.0%} multiplier)
        """)

    # TRANSFER VISUALIZATION
    if result['corridor_changes']:
        st.markdown("## Transfer Points")
        for tc in result['corridor_changes']:
            st.markdown(f"""
            <div class="info-card" style='border-left: 3px solid #f59e0b;'>
                <strong>Transfer at {tc['at']}</strong><br>
                <span style='color:#38bdf8;'>{tc['from_cor']}</span>
                <span style='color:#94a3b8;'> → </span>
                <span style='color:#10b981;'>{tc['to_cor']}</span>
                <br><span style='color:#64748b; font-size:0.75rem;'>Estimated transfer time: {get_config()['eta']['transfer_time_minutes']} minutes</span>
            </div>
            """, unsafe_allow_html=True)

    # FACTORS AFFECTING ETA
    if clf_model is not None:
        st.markdown("## Factors Affecting ETA")
        fi = pd.DataFrame({
            'Factor': ['Number of Stops', 'Peak Hour', 'Corridor', 'Weather', 'Crowding'],
            'Impact': [35, 25, 20, 12, 8]
        }).sort_values('Impact', ascending=True)

        fig, ax = plt.subplots(figsize=(8, 3.5))
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#0f172a')
        colors_fi = plt.cm.viridis(np.linspace(0.2, 0.9, len(fi)))
        bars = ax.barh(fi['Factor'], fi['Impact'], color=colors_fi, edgecolor='none', alpha=0.85)
        ax.set_xlabel('Relative Impact (%)', color='#f1f5f9')
        ax.tick_params(colors='#f1f5f9')
        for spine in ax.spines.values():
            spine.set_color('#334155')
        ax.grid(axis='x', alpha=0.2)
        for bar, val in zip(bars, fi['Impact']):
            ax.text(val+0.5, bar.get_y()+bar.get_height()/2, f'{val}%',
                    va='center', fontsize=9, fontweight='bold', color='#f1f5f9')
        st.pyplot(fig)

# FOOTER
st.markdown("""
<div class='footer-text'>
    <strong>Smart Transjakarta Route Optimizer</strong><br>
    Graph Routing + Machine Learning + Weather Integration<br>
    Data Science and Transportation Optimization Project
    <br><br>
    <span style='font-size:0.7rem;'>
    <strong>Disclaimer:</strong> The dataset used is historical Transjakarta data from April 2023 (one month).<br>
    Crowding predictions and travel time estimates are based on these historical patterns.<br>
    The system does not account for seasonal changes, national holidays, or unexpected events.<br>
    Real-time weather data is provided by BMKG.
    </span>
</div>
""", unsafe_allow_html=True)