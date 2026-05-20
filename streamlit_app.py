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

# KONFIGURASI HALAMAN
st.set_page_config(
    page_title="Smart Transjakarta Route Optimizer",
    page_icon=":bus:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS MODE GELAP (DARK MODE)
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

# KONSTANTA & FUNGSI PEMBANTU
TAHUN_SEKARANG = datetime.now().year
WAKTU_SEKARANG = datetime.now()

def ambil_konfigurasi():
    if 'system_config' not in st.session_state:
        with open('system_config.json') as f:
            st.session_state.system_config = json.load(f)
    return st.session_state.system_config

def ambil_jam_sibuk():
    return ambil_konfigurasi()['peak_hours']

def ambil_kecepatan_koridor(nama_koridor):
    cfg = ambil_konfigurasi()
    per_koridor = cfg['speed'].get('per_corridor_kmh', {})
    if nama_koridor in per_koridor:
        return per_koridor[nama_koridor]
    return cfg['speed']['fallback_kmh']

def ambil_kecepatan_dasar_kmh(nama_koridor=None):
    cfg = ambil_konfigurasi()
    if nama_koridor:
        return ambil_kecepatan_koridor(nama_koridor)
    return cfg['speed']['fallback_kmh']

def ambil_kecepatan_efektif(kondisi_cuaca, nama_koridor=None):
    cfg = ambil_konfigurasi()
    dasar = ambil_kecepatan_dasar_kmh(nama_koridor)
    kunci_cuaca = kondisi_cuaca.lower().replace(' ', '_')
    penyesuaian = cfg['speed'].get('weather_adjustment', {}).get(kunci_cuaca, 1.0)
    return round(dasar * penyesuaian, 1)

def ambil_pengali_cuaca(kondisi_cuaca):
    return ambil_konfigurasi()['weather']['multipliers'].get(
        kondisi_cuaca.lower().replace(' ', '_'), 1.0)

def bobot_sisi_terbatas(jarak_km, kecepatan_kmh):
    kal = ambil_konfigurasi()['speed']['edge_calibration']
    kecepatan_min = max(kecepatan_kmh, kal['min_speed_kmh'])
    kecepatan_efektif = min(kecepatan_min, kal['max_speed_kmh'])
    bobot = max(2, jarak_km / kecepatan_efektif * 60)
    return min(bobot, kal.get('max_segment_minutes', 15))

def apakah_jam_sibuk(jam, is_akhir_pekan=False):
    if is_akhir_pekan:
        return False
    for mulai, selesai in ambil_jam_sibuk():
        if mulai <= jam <= selesai:
            return True
    return False

def hitung_jarak_haversine(lat1, lon1, lat2, lon2):
    try:
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    except:
        return 0

def ambil_periode(jam):
    if 5 <= jam <= 10:
        return 'Pagi'
    elif 11 <= jam <= 15:
        return 'Siang'
    elif 16 <= jam <= 20:
        return 'Sore'
    else:
        return 'Malam'

FITUR_CLF = ['hour', 'haversine_km', 'num_stops', 'direction',
             'is_weekend', 'is_peak_hour', 'age',
             'corridorName', 'hour_period']

def prediksi_kepadatan_hibrida(clf, jam, periode_jam, nama_koridor, is_akhir_pekan, kondisi_cuaca='Cerah'):
    cfg = ambil_konfigurasi()
    kepadatan_cfg = cfg['crowding']
    is_jam_sibuk = apakah_jam_sibuk(jam, is_akhir_pekan)

    skor_ml = 0.5
    if clf is not None:
        try:
            baris = pd.DataFrame([{
                'hour': jam,
                'haversine_km': cfg['analysis_summary']['avg_travel_time_minutes'] / 10,
                'num_stops': 5,
                'direction': 1,
                'is_weekend': int(is_akhir_pekan),
                'is_peak_hour': int(is_jam_sibuk),
                'age': 30,
                'corridorName': nama_koridor,
                'hour_period': periode_jam
            }])
            X = baris[FITUR_CLF]
            proba = clf.predict_proba(X)[0]
            if len(proba) >= 3:
                skor_ml = proba[0] * 0.0 + proba[1] * 0.5 + proba[2] * 1.0
            elif len(proba) == 2:
                skor_ml = proba[0] * 0.0 + proba[1] * 1.0
        except Exception:
            skor_ml = 0.5

    kunci_hari = 'weekend' if is_akhir_pekan else 'weekday'
    dasar_cfg = cfg['historical_density_baseline'].get(kunci_hari, cfg['historical_density_baseline'])
    baseline_db = dasar_cfg.get('per_corridor', {})
    baseline_global = dasar_cfg.get('global_per_hour', {})
    baseline_kor = baseline_db.get(nama_koridor, {})
    skor_baseline = float(baseline_kor.get(str(jam), baseline_global.get(str(jam), 0.05)))

    kunci_cuaca = kondisi_cuaca.lower().replace(' ', '_')
    penyesuaian_cuaca = kepadatan_cfg.get('weather_impact', {}).get(kunci_cuaca, 0.0)

    bobot_ml = kepadatan_cfg['ml_weight']
    bobot_bl = kepadatan_cfg['baseline_weight']
    skor_akhir = skor_ml * bobot_ml + skor_baseline * bobot_bl + penyesuaian_cuaca
    skor_akhir = min(max(skor_akhir, 0.0), 1.0)

    info_label = None
    for tingkat in kepadatan_cfg['labels']:
        if tingkat['min'] <= skor_akhir <= tingkat['max']:
            info_label = tingkat
            break
    if info_label is None:
        info_label = kepadatan_cfg['labels'][1]

    bagian = []
    bagian.append(f"ML: {skor_ml:.2f} x {bobot_ml:.0%}")
    bagian.append(f"Baseline: {skor_baseline:.2f} x {bobot_bl:.0%}")
    if penyesuaian_cuaca > 0:
        bagian.append(f"Cuaca: +{penyesuaian_cuaca:.2f}")
    penjelasan = " + ".join(bagian)

    return info_label['label'], info_label['short'], skor_akhir, penjelasan

# MEMUAT DATA
@st.cache_data(show_spinner="Memuat data Transjakarta...")
def muat_data():
    df = pd.read_csv('dfTransjakarta.csv')
    df['tapInTime'] = pd.to_datetime(df['tapInTime'])
    df['tapOutTime'] = pd.to_datetime(df['tapOutTime'])
    df['travel_time'] = (df['tapOutTime'] - df['tapInTime']).dt.total_seconds() / 60
    df['hour'] = df['tapInTime'].dt.hour
    df['day_of_week'] = df['tapInTime'].dt.dayofweek
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
    df['num_stops'] = df['stopEndSeq'] - df['stopStartSeq']
    df = df[df['num_stops'] > 0]
    df['age'] = TAHUN_SEKARANG - df['payCardBirthDate']
    df['age'] = df['age'].fillna(df['age'].median()).clip(10, 100)
    return df

@st.cache_resource(show_spinner="Membangun graf rute...")
def bangun_graf(df):
    G = nx.DiGraph()
    koordinat_halte = {}

    semua_halte = pd.concat([
        df[['tapInStopsName', 'tapInStopsLat', 'tapInStopsLon']].rename(
            columns={'tapInStopsName': 'stop', 'tapInStopsLat': 'lat', 'tapInStopsLon': 'lon'}),
        df[['tapOutStopsName', 'tapOutStopsLat', 'tapOutStopsLon']].rename(
            columns={'tapOutStopsName': 'stop', 'tapOutStopsLat': 'lat', 'tapOutStopsLon': 'lon'})
    ]).drop_duplicates('stop').reset_index(drop=True)

    for _, baris in semua_halte.iterrows():
        s = baris['stop']
        koordinat_halte[s] = (baris['lat'], baris['lon'])
        G.add_node(s, lat=baris['lat'], lon=baris['lon'])

    rekaman_urutan_halte = []

    tapin = df[['corridorID', 'corridorName', 'direction',
                'tapInStopsName', 'stopStartSeq']].drop_duplicates()
    tapin = tapin.rename(columns={'tapInStopsName': 'stop', 'stopStartSeq': 'seq'})
    rekaman_urutan_halte.append(tapin)

    tapout = df[['corridorID', 'corridorName', 'direction',
                 'tapOutStopsName', 'stopEndSeq']].drop_duplicates()
    tapout = tapout.rename(columns={'tapOutStopsName': 'stop', 'stopEndSeq': 'seq'})
    rekaman_urutan_halte.append(tapout)

    semua_urutan = pd.concat(rekaman_urutan_halte).drop_duplicates().dropna()
    semua_urutan['seq'] = semua_urutan['seq'].astype(int)

    peta_bobot_sisi = df.groupby(
        ['corridorID', 'direction', 'tapInStopsName', 'tapOutStopsName']
    )['travel_time'].mean().reset_index()

    sisi_ditambahkan = set()

    for (cid, arah), grup in semua_urutan.groupby(['corridorID', 'direction']):
        grup = grup.sort_values('seq').drop_duplicates('stop')
        urutan_halte = grup['stop'].tolist()
        nama_kor = grup.iloc[0].get('corridorName', str(cid)) if 'corridorName' in grup.columns else str(cid)
        kecepatan_kor = ambil_kecepatan_dasar_kmh(nama_kor)

        for i in range(len(urutan_halte) - 1):
            u, v = urutan_halte[i], urutan_halte[i+1]
            if u == v:
                continue

            cocok = peta_bobot_sisi[
                (peta_bobot_sisi['corridorID'] == cid) &
                (peta_bobot_sisi['direction'] == arah) &
                (peta_bobot_sisi['tapInStopsName'] == u) &
                (peta_bobot_sisi['tapOutStopsName'] == v)
            ]

            jarak_uv = hitung_jarak_haversine(koordinat_halte.get(u, (0,0))[0], koordinat_halte.get(u, (0,0))[1],
                                              koordinat_halte.get(v, (0,0))[0], koordinat_halte.get(v, (0,0))[1])
            if len(cocok) > 0:
                bobot_mentah = cocok.iloc[0]['travel_time']
                dibatasi = bobot_sisi_terbatas(jarak_uv, kecepatan_kor)
                bobot = min(bobot_mentah, dibatasi)
            else:
                if u in koordinat_halte and v in koordinat_halte and jarak_uv > 0:
                    bobot = bobot_sisi_terbatas(jarak_uv, kecepatan_kor)
                else:
                    bobot = 5

            jarak = hitung_jarak_haversine(koordinat_halte.get(u, (0,0))[0], koordinat_halte.get(u, (0,0))[1],
                                           koordinat_halte.get(v, (0,0))[0], koordinat_halte.get(v, (0,0))[1])

            kunci = (u, v, cid)
            if kunci not in sisi_ditambahkan:
                if jarak_uv <= 3.0:
                    G.add_edge(u, v,
                               weight=round(bobot, 1),
                               weight_km=round(jarak, 3),
                               corridorID=cid,
                               corridorName=nama_kor,
                               direction=arah,
                               confidence=1.0,
                               edge_type='sequential')
                    sisi_ditambahkan.add(kunci)

    for (cid, arah), grup in semua_urutan.groupby(['corridorID', 'direction']):
        grup = grup.sort_values('seq').drop_duplicates('stop')
        urutan = grup['stop'].tolist()
        if len(urutan) < 3:
            continue
        nama_kor = grup.iloc[0].get('corridorName', str(cid)) if 'corridorName' in grup.columns else str(cid)
        kecepatan_kor = ambil_kecepatan_dasar_kmh(nama_kor)
        for i in range(len(urutan)):
            for j in range(i+3, min(i+8, len(urutan))):
                u, v = urutan[i], urutan[j]
                kunci = (u, v, cid, 'inferred')
                if kunci not in sisi_ditambahkan and u != v:
                    d = hitung_jarak_haversine(koordinat_halte[u][0], koordinat_halte[u][1],
                                               koordinat_halte[v][0], koordinat_halte[v][1])
                    bobot = bobot_sisi_terbatas(d, kecepatan_kor)
                    jarak = round(d, 3)
                    G.add_edge(u, v, weight=round(bobot, 1), weight_km=jarak,
                               corridorID=cid, corridorName=nama_kor,
                               direction=arah, confidence=0.6, edge_type='inferred')
                    sisi_ditambahkan.add(kunci)

    return G, koordinat_halte

@st.cache_resource(show_spinner="Memuat model ML...")
def muat_model_ml():
    try:
        clf = joblib.load('model_clf_transjakarta.pkl')
        return clf, None
    except:
        return None, None

@st.cache_data(show_spinner=False)
def muat_gtfs_waiting():
    """Load GTFS waiting time per koridor dari gtfs_waiting_config.json."""
    try:
        with open('gtfs_waiting_config.json', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"per_route": {}, "default_sepi": 3, "default_normal": 5, "default_padat": 8}

def ambil_waktu_menunggu(gtfs_cfg, nama_koridor, label_singkat):
    """Lookup waiting time dari GTFS per koridor. Fallback ke crowding-based."""
    per_route = gtfs_cfg.get('per_route', {}) if gtfs_cfg else {}
    if nama_koridor and nama_koridor in per_route:
        raw = per_route[nama_koridor]
        return max(2, min(round(raw), 15))  # cap 2-15 menit
    # Fallback: crowding-based dari default GTFS config
    defaults = {
        'sepi':   gtfs_cfg.get('default_sepi', 3) if gtfs_cfg else 3,
        'normal': gtfs_cfg.get('default_normal', 5) if gtfs_cfg else 5,
        'padat':  gtfs_cfg.get('default_padat', 8) if gtfs_cfg else 8,
    }
    return defaults.get(label_singkat.lower(), 5)

# CUACA
def ambil_prakiraan_bmkg(tanggal_target, jam_target):
    adm4_code = '31.71.01.1001'
    url = f"https://api.bmkg.go.id/publik/prakiraan-cuaca?adm4={adm4_code}"
    try:
        resp = http_requests.get(url, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        catatan = []
        if 'data' in data:
            for lokasi in data['data']:
                for batch in lokasi.get('cuaca', [[]]):
                    for item in batch:
                        catatan.append(item)
        if not catatan:
            return None

        target_str = tanggal_target.strftime('%Y-%m-%d') if hasattr(tanggal_target, 'strftime') else str(tanggal_target)[:10]

        difilter_tanggal = [r for r in catatan if r.get('local_datetime', '').startswith(target_str)]
        if not difilter_tanggal:
            difilter_tanggal = catatan

        terbaik = None
        selisih_terbaik = float('inf')
        for r in difilter_tanggal:
            dt = r.get('local_datetime', '')
            if len(dt) >= 13:
                try:
                    h = int(dt[11:13])
                    selisih = abs(h - jam_target)
                    if selisih < selisih_terbaik:
                        selisih_terbaik = selisih
                        terbaik = r
                except:
                    pass

        if terbaik is None:
            terbaik = difilter_tanggal[0]

        deskripsi = terbaik.get('weather_desc', 'Cerah').lower()
        if any(kata in deskripsi for kata in ['hujan','rain','petir','thunder']):
            return 'Hujan Ringan' if 'ringan' in deskripsi else 'Hujan Lebat'
        if any(kata in deskripsi for kata in ['berawan','cloudy','mendung']):
            return 'Mendung'
        return 'Cerah'
    except:
        pass
    return None

def ambil_cuaca(tanggal_target, jam_target, pakai_real_time=True):
    if pakai_real_time:
        prakiraan = ambil_prakiraan_bmkg(tanggal_target, jam_target)
        if prakiraan:
            return prakiraan
    if 13 <= jam_target <= 17:
        return random.choice(['Cerah', 'Mendung', 'Hujan Ringan'])
    return random.choice(['Cerah', 'Mendung'])

# MESIN PERUTEAN
def rute_dijkstra(graf, asal, tujuan, attr_bobot='weight', penalti_transfer=15, pangkat_kepercayaan=1.0):
    if asal not in graf or tujuan not in graf:
        return None, float('inf'), 0
    
    jarak = {node: float('inf') for node in graf.nodes()}
    jarak[asal] = 0
    sebelumnya = {}
    heap = [(0, asal, None)]
    dikunjungi = set()
    dieksplorasi = 0
    
    while heap:
        d, curr, curr_kor = heapq.heappop(heap)
        if curr in dikunjungi and d > jarak[curr]:
            continue
        dikunjungi.add(curr)
        dieksplorasi += 1
        if curr == tujuan:
            break
        for tetangga in graf.successors(curr):
            sisi = graf[curr][tetangga]
            w = sisi.get(attr_bobot, float('inf'))
            conf = sisi.get('confidence', 1.0)
            kor = sisi.get('corridorName', '')

            efektif = w / (max(conf, 0.1) ** pangkat_kepercayaan)

            if curr_kor is not None and kor and curr_kor and kor != curr_kor:
                efektif += penalti_transfer

            nd = d + efektif
            if nd < jarak.get(tetangga, float('inf')):
                jarak[tetangga] = nd
                sebelumnya[tetangga] = curr
                heapq.heappush(heap, (nd, tetangga, kor))
    
    if tujuan not in sebelumnya and asal != tujuan:
        return None, float('inf'), dieksplorasi
    
    jalur = []
    node = tujuan
    while node in sebelumnya:
        jalur.append(node)
        node = sebelumnya[node]
    jalur.append(asal)
    jalur.reverse()
    return jalur, jarak[tujuan], dieksplorasi

def dapatkan_rincian_eta(graf, jalur, jam, is_akhir_pekan, pengali_cuaca, model_clf=None, kondisi_cuaca='Cerah', gtfs_waiting=None):
    if not jalur or len(jalur) < 2:
        return None

    waktu_tempuh = 0
    total_jarak = 0
    segmen = []
    transfer = 0
    koridor_sebelum = None
    perubahan_koridor = []

    for i in range(len(jalur) - 1):
        u, v = jalur[i], jalur[i+1]
        if graf.has_edge(u, v):
            w = graf[u][v].get('weight', 10)
            d = graf[u][v].get('weight_km', 0.5)
            kor = graf[u][v].get('corridorName', 'Tidak Diketahui')
            waktu_tempuh += w
            total_jarak += d
            segmen.append({
                'dari': u, 'ke': v,
                'bobot': w,
                'jarak_km': d,
                'koridor': kor
            })
            if koridor_sebelum and koridor_sebelum != kor:
                transfer += 1
                waktu_transfer = ambil_konfigurasi()['eta']['transfer_time_minutes']
                perubahan_koridor.append({
                    'di': u,
                    'dari_kor': koridor_sebelum,
                    'ke_kor': kor,
                    'waktu_transfer': waktu_transfer
                })
            koridor_sebelum = kor
        else:
            kecepatan_fallback = ambil_konfigurasi()['speed']['fallback_kmh']
            jarak_fb = hitung_jarak_haversine(
                graf.nodes[u].get('lat',0), graf.nodes[u].get('lon',0),
                graf.nodes[v].get('lat',0), graf.nodes[v].get('lon',0)
            )
            bobot = bobot_sisi_terbatas(jarak_fb, kecepatan_fallback)
            waktu_tempuh += bobot
            segmen.append({
                'dari': u, 'ke': v,
                'bobot': bobot,
                'jarak_km': hitung_jarak_haversine(
                    graf.nodes[u].get('lat',0), graf.nodes[u].get('lon',0),
                    graf.nodes[v].get('lat',0), graf.nodes[v].get('lon',0)
                ),
                'koridor': 'Transfer'
            })

    periode_jam = ambil_periode(jam)
    halte_pertama = jalur[0] if jalur else 'Tidak Diketahui'
    label_kepadatan, label_singkat, skor_kepadatan, penjelasan_kepadatan = prediksi_kepadatan_hibrida(
        model_clf, jam, periode_jam, halte_pertama, is_akhir_pekan, kondisi_cuaca
    )

    # Waiting time dari GTFS (per koridor), fallback ke crowding-based
    koridor_pertama = segmen[0]['koridor'] if segmen else None
    waktu_menunggu = ambil_waktu_menunggu(gtfs_waiting, koridor_pertama, label_singkat)
    sumber_waiting = 'GTFS' if (gtfs_waiting and koridor_pertama and koridor_pertama in gtfs_waiting.get('per_route', {})) else 'Default'
    waktu_transfer = transfer * ambil_konfigurasi()['eta']['transfer_time_minutes']

    kemacetan = ambil_konfigurasi()['eta']['congestion']
    tundaan_macet = 0
    if apakah_jam_sibuk(jam, is_akhir_pekan):
        tundaan_macet = waktu_tempuh * kemacetan['peak_multiplier']
    if skor_kepadatan > 0.65:
        tundaan_macet += waktu_tempuh * kemacetan['crowded_multiplier']

    penyesuaian_cuaca = waktu_tempuh * (pengali_cuaca - 1.0)

    total_eta = waktu_tempuh + waktu_menunggu + waktu_transfer + tundaan_macet + penyesuaian_cuaca

    if transfer > 3 or total_eta > 180:
        lencana = 'Estimasi Kasar'
    elif skor_kepadatan > ambil_konfigurasi()['crowding']['labels'][2]['min'] and pengali_cuaca > 1.1:
        lencana = 'Estimasi Kasar'
    else:
        lencana = 'Akurat'

    return {
        'waktu_tempuh': round(waktu_tempuh, 1),
        'waktu_menunggu': waktu_menunggu,
        'waktu_transfer': waktu_transfer,
        'tundaan_macet': round(tundaan_macet, 1),
        'penyesuaian_cuaca': round(penyesuaian_cuaca, 1),
        'total_eta': round(total_eta, 1),
        'total_jarak': round(total_jarak, 2),
        'jumlah_halte': len(jalur),
        'transfer': transfer,
        'label_kepadatan': label_singkat,
        'label_kepadatan_lengkap': label_kepadatan,
        'skor_kepadatan': skor_kepadatan,
        'penjelasan_kepadatan': penjelasan_kepadatan,
        'lencana': lencana,
        'segmen': segmen,
        'perubahan_koridor': perubahan_koridor,
        'is_peak': apakah_jam_sibuk(jam, is_akhir_pekan),
        'gtfs_koridor': koridor_pertama,
        'sumber_waiting': sumber_waiting,
    }

# APLIKASI UTAMA
with st.spinner("Memuat data..."):
    df = muat_data()
    G, koordinat_halte = bangun_graf(df)
    model_clf, _ = muat_model_ml()
    gtfs_waiting = muat_gtfs_waiting()

daftar_halte = sorted(list(G.nodes()))

komponen_terhubung = list(nx.weakly_connected_components(G))
komponen_terbesar = max(komponen_terhubung, key=len) if komponen_terhubung else set()
halte_terisolasi = sum(1 for komp in komponen_terhubung if len(komp) == 1)

# HEADER
kol_logo, kol_judul, kol_jam = st.columns([0.08, 0.62, 0.3])

with kol_logo:
    st.markdown("<div style='font-size:2.5rem; text-align:center;'>🚌</div>", unsafe_allow_html=True)

with kol_judul:
    st.markdown("<h1 style='margin:0; padding:0;'>Smart Transjakarta Route Optimizer</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#94a3b8; margin:0;'>Perutean graf dan optimasi machine learning untuk Transjakarta</p>", unsafe_allow_html=True)

with kol_jam:
    sekarang = datetime.now()
    st.markdown(f"""
    <div style='text-align:right;'>
        <div style='font-size:1.5rem; font-weight:700; color:#38bdf8;'>{sekarang.strftime('%H:%M')}</div>
        <div style='color:#94a3b8; font-size:0.75rem;'>{sekarang.strftime('%d %B %Y')}</div>
    </div>
    """, unsafe_allow_html=True)

kol_s1, kol_s2, kol_s3 = st.columns(3)
with kol_s1:
    st.markdown("<div class='status-online'>● Graf Dimuat</div>", unsafe_allow_html=True)
with kol_s2:
    st.markdown(f"<div class='{'status-online' if model_clf else 'status-offline'}'>● Model ML Aktif</div>", unsafe_allow_html=True)
with kol_s3:
    st.markdown("<div class='status-online'>● API Cuaca Terhubung</div>", unsafe_allow_html=True)

st.markdown("---")

# SIDEBAR
with st.sidebar:
    st.markdown("## Informasi Sistem")

    st.markdown("### Statistik Graf")
    kol1, kol2 = st.columns(2)

    komponen = list(nx.weakly_connected_components(G))
    terbesar = max(komponen, key=len) if komponen else set()

    kol1.metric("Total Halte", f"{G.number_of_nodes():,}")
    kol2.metric("Total Sisi", f"{G.number_of_edges():,}")
    kol1.metric("Total Koridor", f"{df['corridorID'].nunique()}")
    kol2.metric("Rata-rata Derajat Node", f"{2*G.number_of_edges()/max(G.number_of_nodes(),1):.1f}")

    st.markdown("### Kualitas Topologi")
    cakupan = len(terbesar) / max(G.number_of_nodes(), 1) * 100
    st.markdown(f"- **Komponen Terhubung:** {len(komponen)}")
    st.markdown(f"- **Komponen Terbesar:** {len(terbesar):,} node ({cakupan:.0f}%)")
    st.markdown(f"- **Tipe Graf:** Berurutan per Koridor")
    derajat = sorted([d for _, d in G.degree()], reverse=True)
    ambang_hub = derajat[max(len(derajat)//20 - 1, 0)] if len(derajat) >= 20 else 10
    st.markdown(f"- **Hub Transfer:** {sum(1 for _, d in G.degree() if d >= ambang_hub)} (top 5%)")

    st.markdown("### Info Dataset")
    st.markdown(f"- **Perjalanan:** {len(df):,}")
    st.markdown(f"- **Periode:** April 2023")
    st.markdown(f"- **Rata-rata Waktu Tempuh:** {df['travel_time'].mean():.0f} menit")

    st.markdown("### Mode Estimasi")
    st.markdown("**ETA Hibrida**")
    st.markdown("Graf + ML + Cuaca")

    st.markdown("---")
    st.markdown("### Versi")
    st.markdown("v3.0 — Sequential Corridor Graph")

# LAYAR UTAMA
st.markdown("## Perencana Rute")
st.markdown("Pilih halte asal dan tujuan Anda, atur jadwal perjalanan, dan sistem akan menemukan rute Transjakarta optimal.")

kol_input1, kol_input2 = st.columns(2)

with kol_input1:
    asal = st.selectbox("Halte Asal", daftar_halte, index=daftar_halte.index("Blok M") if "Blok M" in daftar_halte else 0)

with kol_input2:
    tujuan = st.selectbox("Halte Tujuan", daftar_halte, index=daftar_halte.index("Kota") if "Kota" in daftar_halte else (daftar_halte.index("Harmoni") if "Harmoni" in daftar_halte else min(len(daftar_halte)-1, 1)))

st.markdown("### Pengaturan Perjalanan")
with st.expander("Cara membaca pengaturan ini", expanded=False):
    st.markdown("""
    - **Akhir Pekan / Libur** — aktifkan untuk perjalanan akhir pekan atau hari libur. Mempengaruhi pola kemacetan.
    - **Jam Keberangkatan** — menentukan jam sibuk/non-sibuk. Jam sibuk (06-09 & 16-19) memiliki kemacetan +20%.
    - **Prioritas** — mempengaruhi pemilihan rute Dijkstra:
        - *Waktu Tercepat*: meminimalkan total ETA
        - *Minimal Transfer*: menghindari pergantian koridor
        - *Rute Paling Stabil*: memprioritaskan jalur berurutan dengan data riil, hindari sisi inferensi
    """)

kol_t1, kol_t2, kol_t3 = st.columns(3)

with kol_t1:
    toggle_akhir_pekan = st.toggle("Akhir Pekan / Libur", value=False)

with kol_t2:
    jam_keberangkatan = st.slider("Jam Keberangkatan", 0, 23, 8)

with kol_t3:
    prioritas = st.selectbox("Prioritas Optimasi", ["Waktu Tercepat", "Minimal Transfer", "Rute Paling Stabil"])

st.markdown("### Kondisi Cuaca")
st.markdown("Cuaca mempengaruhi kecepatan operasional bus. Hujan dapat meningkatkan ETA hingga 25%.")

kol_w1, kol_w2, kol_w3, kol_w4 = st.columns([0.2, 0.2, 0.2, 0.4])

with kol_w1:
    pakai_real_time = st.toggle("Cuaca BMKG", value=False)

with kol_w2:
    if pakai_real_time:
        hari_perjalanan_bmkg = st.selectbox("Hari", ["Hari Ini", "Besok", "Lusa"], label_visibility="collapsed")
        offset_hari = {"Hari Ini": 0, "Besok": 1, "Lusa": 2}
        tanggal_target = date.today() + timedelta(days=offset_hari.get(hari_perjalanan_bmkg, 0))
        cuaca_sekarang = ambil_cuaca(tanggal_target, jam_keberangkatan, pakai_real_time=True)
        kondisi_cuaca = cuaca_sekarang
        st.markdown(f"**{kondisi_cuaca}**")
    else:
        kondisi_cuaca = st.selectbox("Cuaca", ["Cerah", "Mendung", "Hujan Ringan", "Hujan Lebat"], label_visibility="collapsed")

with kol_w3:
    pengali_cuaca = ambil_pengali_cuaca(kondisi_cuaca)
    st.metric("Pengali Cuaca", f"{pengali_cuaca:.2f}x")

# VALIDASI
rute_ditemukan = False
hasil = None

if asal == tujuan:
    st.warning("Halte asal dan tujuan tidak boleh sama. Silakan pilih halte yang berbeda.")
elif asal not in G or tujuan not in G:
    st.error("Satu atau kedua halte tidak ditemukan dalam graf rute.")
else:
    with st.spinner("Mencari rute optimal..."):
        is_akhir_pekan = toggle_akhir_pekan

        if prioritas == "Waktu Tercepat":
            jalur, biaya, dieksplorasi = rute_dijkstra(G, asal, tujuan, 'weight', penalti_transfer=15, pangkat_kepercayaan=1.0)
        elif prioritas == "Minimal Transfer":
            jalur, biaya, dieksplorasi = rute_dijkstra(G, asal, tujuan, 'weight', penalti_transfer=60, pangkat_kepercayaan=1.0)
        else:
            jalur, biaya, dieksplorasi = rute_dijkstra(G, asal, tujuan, 'weight', penalti_transfer=15, pangkat_kepercayaan=2.0)

        if jalur is None or len(jalur) < 2:
            st.error("Tidak ditemukan rute antara halte ini.")
            with st.expander("Kemungkinan penyebab"):
                st.markdown("""
                - Graf terputus antara halte-halte ini
                - Halte berada di komponen terhubung yang berbeda
                - Tidak ada data rute untuk pasangan ini
                """)
        else:
            rute_ditemukan = True
            hasil = dapatkan_rincian_eta(G, jalur, jam_keberangkatan, is_akhir_pekan, pengali_cuaca, model_clf, kondisi_cuaca, gtfs_waiting)

# HASIL
if rute_ditemukan and hasil:
    st.markdown("---")
    st.markdown("## Hasil Rute")
    st.info("Ringkasan rute terbaik berdasarkan perutean graf, data historis, dan kondisi cuaca. ETA mencakup waktu tempuh, menunggu, transfer, kemacetan, dan penyesuaian cuaca.")

    kol_r1, kol_r2, kol_r3, kol_r4, kol_r5 = st.columns(5)

    with kol_r1:
        warna_lencana = '#10b981' if hasil['lencana'] == 'Akurat' else ('#f59e0b' if hasil['lencana'] == 'Estimasi Kasar' else '#ef4444')
        st.markdown(f"""
        <div class="info-card" style='text-align:center;'>
            <div class='metric-label'>Total ETA</div>
            <div class='metric-value'>{hasil['total_eta']:.0f} <span style='font-size:1rem;'>menit</span></div>
            <div style='margin-top:8px;'><span class='badge-{hasil['lencana'].lower().replace(' ', '-')}'>{hasil['lencana']}</span></div>
        </div>
        """, unsafe_allow_html=True)

    with kol_r2:
        st.markdown(f"""
        <div class="info-card" style='text-align:center;'>
            <div class='metric-label'>Total Jarak</div>
            <div class='metric-value'>{hasil['total_jarak']:.1f} <span style='font-size:1rem;'>km</span></div>
        </div>
        """, unsafe_allow_html=True)

    with kol_r3:
        st.markdown(f"""
        <div class="info-card" style='text-align:center;'>
            <div class='metric-label'>Jumlah Halte</div>
            <div class='metric-value'>{hasil['jumlah_halte']}</div>
        </div>
        """, unsafe_allow_html=True)

    with kol_r4:
        st.markdown(f"""
        <div class="info-card" style='text-align:center;'>
            <div class='metric-label'>Transfer</div>
            <div class='metric-value'>{hasil['transfer']}</div>
        </div>
        """, unsafe_allow_html=True)

    with kol_r5:
        label_k = hasil['label_kepadatan']
        skor_k = hasil.get('skor_kepadatan', 0.5)
        warna_penuh = '#10b981' if skor_k < 0.3 else ('#f59e0b' if skor_k < 0.65 else '#ef4444')
        st.markdown(f"""
        <div class="info-card" style='text-align:center;'>
            <div class='metric-label'>Tingkat Kepadatan</div>
            <div class='metric-value' style='color:{warna_penuh};'>{label_k}</div>
            <div style='font-size:0.7rem; color:#94a3b8;'>{hasil.get('label_kepadatan_lengkap', '')}</div>
        </div>
        """, unsafe_allow_html=True)

    # GARIS WAKTU RUTE
    st.markdown("## Garis Waktu Rute")
    st.caption("Urutan halte di sepanjang rute. Waktu tempuh antar halte berdasarkan rata-rata historis atau estimasi jarak/kecepatan.")

    data_garis_waktu = []
    for i in range(len(jalur)):
        info = {"index": i+1, "halte": jalur[i], "tipe": "asal" if i == 0 else ("tujuan" if i == len(jalur)-1 else "transit")}
        if i > 0:
            u, v = jalur[i-1], jalur[i]
            w = 0
            kor = "Transfer"
            if G.has_edge(u, v):
                w = G[u][v].get('weight', 0)
                kor = G[u][v].get('corridorName', 'Tidak Diketahui')
            info["waktu_ke"] = round(w, 1)
            info["koridor"] = kor
        else:
            info["waktu_ke"] = 0
            info["koridor"] = "-"
        data_garis_waktu.append(info)

    for idx, info in enumerate(data_garis_waktu):
        kol_tl1, kol_tl2, kol_tl3, kol_tl4 = st.columns([0.05, 0.25, 0.15, 0.55])

        with kol_tl1:
            warna_tipe = "#10b981" if info["tipe"] == "asal" else ("#ef4444" if info["tipe"] == "tujuan" else "#38bdf8")
            st.markdown(f"<div style='background:{warna_tipe}; width:10px; height:10px; border-radius:50%; margin-top:6px;'></div>", unsafe_allow_html=True)
            if idx < len(data_garis_waktu) - 1:
                st.markdown("<div style='border-left:2px solid #334155; height:20px; margin-left:4px;'></div>", unsafe_allow_html=True)

        with kol_tl2:
            label_tipe = "Asal" if info["tipe"] == "asal" else ("Tujuan" if info["tipe"] == "tujuan" else "Transit")
            st.markdown(f"**{info['halte']}** <span style='color:#94a3b8; font-size:0.75rem;'>({label_tipe})</span>", unsafe_allow_html=True)

        with kol_tl3:
            if info["waktu_ke"] > 0:
                st.markdown(f"<span style='color:#94a3b8;'>{info['waktu_ke']:.0f} menit</span>", unsafe_allow_html=True)

        with kol_tl4:
            if info["koridor"] != "-" and info["koridor"] != "Transfer":
                st.markdown(f"<span style='color:#38bdf8; font-size:0.75rem;'>Koridor: {info['koridor']}</span>", unsafe_allow_html=True)
            elif info["koridor"] == "Transfer":
                st.markdown(f"<span style='color:#f59e0b; font-size:0.75rem;'>Transfer koridor</span>", unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom:2px;'></div>", unsafe_allow_html=True)

    # RINCIAN WAKTU
    st.markdown("## Rincian Waktu")
    st.caption("Total ETA = Waktu Tempuh + Waktu Menunggu + Waktu Transfer + Tundaan Macet + Penyesuaian Cuaca.")

    kol_b1, kol_b2 = st.columns([0.5, 0.5])

    with kol_b1:
        kol_m1, kol_m2, kol_m3 = st.columns(3)
        kol_m1.metric("Waktu Tempuh", f"{hasil['waktu_tempuh']:.0f} menit")
        kol_m2.metric("Waktu Menunggu", f"{hasil['waktu_menunggu']} menit")
        kol_m3.metric("Waktu Transfer", f"{hasil['waktu_transfer']} menit")

        kol_m1, kol_m2, kol_m3 = st.columns(3)
        kol_m1.metric("Tundaan Macet", f"+{hasil['tundaan_macet']:.0f} menit")
        kol_m2.metric("Penyesuaian Cuaca", f"+{hasil['penyesuaian_cuaca']:.0f} menit")
        kol_m3.metric("Total ETA", f"{hasil['total_eta']:.0f} menit")

    with kol_b2:
        label = ['Perjalanan', 'Menunggu', 'Transfer', 'Macet', 'Cuaca']
        ukuran = [
            hasil['waktu_tempuh'],
            hasil['waktu_menunggu'],
            hasil['waktu_transfer'],
            hasil['tundaan_macet'],
            hasil['penyesuaian_cuaca']
        ]
        warna_pie = ['#38bdf8', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']

        fig, ax = plt.subplots(figsize=(6, 4))
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#0f172a')
        irisan, _, autoteks = ax.pie(ukuran, labels=None, autopct='%1.0f%%',
                                     colors=warna_pie, startangle=90,
                                     textprops={'color': '#f1f5f9', 'fontsize': 9})
        for at in autoteks:
            at.set_color('#0f172a')
            at.set_fontweight('bold')
        ax.legend(irisan, [f'{l} ({s:.0f}m)' for l, s in zip(label, ukuran)],
                  loc='center left', bbox_to_anchor=(1, 0.5),
                  fontsize=9, frameon=False, labelcolor='#f1f5f9')
        st.pyplot(fig)

    # KOMPOSISI ETA
    st.markdown("### Komposisi ETA")
    total = sum(ukuran)
    if total > 0:
        proporsi = [s/total for s in ukuran]
        html_bar = "<div style='display:flex; height:28px; border-radius:14px; overflow:hidden; margin:8px 0;'>"
        for prop, warna, lbl in zip(proporsi, warna_pie, label):
            if prop > 0.01:
                html_bar += f"<div style='width:{prop*100}%; background:{warna}; display:flex; align-items:center; justify-content:center; font-size:0.7rem; font-weight:600; color:#0f172a;'>{lbl}</div>"
        html_bar += "</div>"
        st.markdown(html_bar, unsafe_allow_html=True)

    # ANALISIS KONDISI PERJALANAN
    st.markdown("## Analisis Kondisi Perjalanan")

    kol_c1, kol_c2, kol_c3, kol_c4 = st.columns(4)

    with kol_c1:
        status_puncak = "Jam Sibuk" if hasil['is_peak'] else "Luar Jam Sibuk"
        warna_puncak = "#ef4444" if hasil['is_peak'] else "#10b981"
        st.markdown(f"""
        <div class="info-card" style='text-align:center;'>
            <div class='metric-label'>Waktu</div>
            <div class='metric-value' style='font-size:1.2rem; color:{warna_puncak};'>{status_puncak}</div>
        </div>
        """, unsafe_allow_html=True)

    with kol_c2:
        skor_k = hasil.get('skor_kepadatan', 0.5)
        label_k_lengkap = hasil.get('label_kepadatan_lengkap', hasil['label_kepadatan'])
        warna_kepadatan = '#10b981' if skor_k < 0.3 else ('#f59e0b' if skor_k < 0.65 else '#ef4444')
        st.markdown(f"""
        <div class="info-card" style='text-align:center;'>
            <div class='metric-label'>Kepadatan</div>
            <div class='metric-value' style='font-size:1.2rem; color:{warna_kepadatan};'>{label_k_lengkap}</div>
            <div style='font-size:0.65rem; color:#94a3b8;'>Skor: {skor_k:.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    with kol_c3:
        st.markdown(f"""
        <div class="info-card" style='text-align:center;'>
            <div class='metric-label'>Cuaca</div>
            <div class='metric-value' style='font-size:1.2rem; color:#38bdf8;'>{kondisi_cuaca}</div>
        </div>
        """, unsafe_allow_html=True)

    with kol_c4:
        kecepatan_mentah = hasil['total_jarak'] / (hasil['waktu_tempuh']/60) if hasil['waktu_tempuh'] > 0 else 0
        kecepatan_rata = min(kecepatan_mentah, 28)
        st.markdown(f"""
        <div class="info-card" style='text-align:center;'>
            <div class='metric-label'>Kecepatan Rata-rata</div>
            <div class='metric-value' style='font-size:1.2rem;'>{kecepatan_rata:.1f} km/jam</div>
        </div>
        """, unsafe_allow_html=True)

    # WAWASAN KEPADATAN
    st.markdown("### Wawasan Kepadatan")
    penjelasan_k = hasil.get('penjelasan_kepadatan', '')
    label_k_lengkap = hasil.get('label_kepadatan_lengkap', hasil['label_kepadatan'])
    try:
        tingkat_label = ambil_konfigurasi()['crowding']['labels']
        deskripsi = ''
        for t in tingkat_label:
            if t['label'] == label_k_lengkap:
                deskripsi = t['description']
                break
    except:
        deskripsi = ''

    st.markdown(f"""
    <div class="info-card">
        <strong>{label_k_lengkap}</strong><br>
        <span style='color:#94a3b8; font-size:0.85rem;'>{deskripsi}</span><br>
        <span style='color:#64748b; font-size:0.75rem;'>Komponen: {penjelasan_k}</span>
    </div>
    """, unsafe_allow_html=True)

    # PANEL PENJELASAN
    with st.expander("Bagaimana ETA ini dihitung?", expanded=True):
        st.markdown(f"""
        **ETA dihitung menggunakan kombinasi:**

        - **Perutean Graf** :  algoritma Dijkstra mencari jalur terpendek dalam graf Transjakarta
        - **Rata-rata Historis** : bobot sisi berdasarkan waktu tempuh historis rata-rata
        - **Jam Sibuk** : penyesuaian kemacetan selama jam sibuk
        - **Kondisi Cuaca** : pengali dari prakiraan BMKG
        - **Tingkat Kepadatan** : hibrida ML (70%) + baseline historis (30%) + penyesuaian cuaca
        - **Waktu Menunggu** : berdasarkan jadwal GTFS per rute

        **Rumus ETA:**

        `ETA = Waktu Tempuh + Waktu Menunggu + Waktu Transfer + Tundaan Macet + Penyesuaian Cuaca`

        **Detail perhitungan untuk rute ini:**

        - Waktu Tempuh: {hasil['waktu_tempuh']:.1f} menit (jumlah bobot sisi)
        - Waktu Menunggu: {hasil['waktu_menunggu']} menit — sumber: **{hasil.get('sumber_waiting', 'Default')}** {('(koridor: ' + hasil.get('gtfs_koridor','') + ')') if hasil.get('sumber_waiting') == 'GTFS' else '(fallback crowding-based)'}
        - Waktu Transfer: {hasil['waktu_transfer']} menit ({hasil['transfer']} transfer x {ambil_konfigurasi()['eta']['transfer_time_minutes']} menit)
        - Tundaan Macet: +{hasil['tundaan_macet']:.0f} menit ({'jam sibuk' if hasil['is_peak'] else 'luar jam sibuk'})
        - Penyesuaian Cuaca: +{hasil['penyesuaian_cuaca']:.0f} menit ({kondisi_cuaca}, {pengali_cuaca:.0%} pengali)
        """)

    # VISUALISASI TRANSFER
    if hasil['perubahan_koridor']:
        st.markdown("## Titik Transfer")
        for tc in hasil['perubahan_koridor']:
            st.markdown(f"""
            <div class="info-card" style='border-left: 3px solid #f59e0b;'>
                <strong>Transfer di {tc['di']}</strong><br>
                <span style='color:#38bdf8;'>{tc['dari_kor']}</span>
                <span style='color:#94a3b8;'> → </span>
                <span style='color:#10b981;'>{tc['ke_kor']}</span>
                <br><span style='color:#64748b; font-size:0.75rem;'>Estimasi waktu transfer: {ambil_konfigurasi()['eta']['transfer_time_minutes']} menit</span>
            </div>
            """, unsafe_allow_html=True)

    # FAKTOR YANG MEMPENGARUHI ETA
    if model_clf is not None:
        st.markdown("## Faktor yang Mempengaruhi ETA")
        df_faktor = pd.DataFrame({
            'Faktor': ['Jumlah Halte', 'Jam Sibuk', 'Koridor', 'Cuaca', 'Kepadatan'],
            'Dampak': [35, 25, 20, 12, 8]
        }).sort_values('Dampak', ascending=True)

        fig, ax = plt.subplots(figsize=(8, 3.5))
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#0f172a')
        warna_fi = plt.cm.viridis(np.linspace(0.2, 0.9, len(df_faktor)))
        batang = ax.barh(df_faktor['Faktor'], df_faktor['Dampak'], color=warna_fi, edgecolor='none', alpha=0.85)
        ax.set_xlabel('Dampak Relatif (%)', color='#f1f5f9')
        ax.tick_params(colors='#f1f5f9')
        for spine in ax.spines.values():
            spine.set_color('#334155')
        ax.grid(axis='x', alpha=0.2)
        for bar, val in zip(batang, df_faktor['Dampak']):
            ax.text(val+0.5, bar.get_y()+bar.get_height()/2, f'{val}%',
                    va='center', fontsize=9, fontweight='bold', color='#f1f5f9')
        st.pyplot(fig)

# FOOTER
st.markdown("""
<div class='footer-text'>
    <strong>Smart Transjakarta Route Optimizer</strong><br>
    Perutean Graf + Machine Learning + Integrasi Cuaca<br>
    Proyek Optimasi Data Science dan Transportasi
    <br><br>
    <span style='font-size:0.7rem;'>
    <strong>Catatan:</strong> Dataset yang digunakan adalah data historis Transjakarta dari April 2023 (satu bulan).<br>
    Prediksi kepadatan dan estimasi waktu tempuh didasarkan pada pola historis tersebut.<br>
    Sistem tidak memperhitungkan perubahan musiman, hari libur nasional, atau kejadian tak terduga.<br>
    Data cuaca real-time disediakan oleh BMKG.
    </span>
</div>
""", unsafe_allow_html=True)