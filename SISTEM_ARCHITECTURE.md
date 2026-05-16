# Sistem Optimasi Rute Transjakarta

## Arsitektur Sistem

```
┌─────────────────────────────────────────────────────────────────┐
│                    NOTEBOOK (Source of Truth)                    │
│  generate_config.py + Optimasi_Rute_Transjakarta_FINAL.ipynb    │
│                                                                  │
│  1. Load & Clean Data         6. Hitung Speed per Corridor      │
│  2. Feature Engineering       7. Hitung Historical Density      │
│  3. EDA                       Baseline untuk Crowding           │
│  4. Split Data (80/20)        8. Export Model (RandomForest)    │
│  5. Train Klasifikasi (RF)    9. Export System Config (JSON)   │
└─────────────────────────┬───────────────────────────────────────┘
                          │ Output Artifacts
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SYSTEM ARTIFACTS                            │
│                                                                  │
│  model_clf_transjakarta.pkl   RandomForest (F1 88%)             │
│  system_config.json           Semua threshold, speed, rule     │
│  gtfs_headway.json            Headway per rute (GTFS)          │
│  gtfs_waiting_config.json     Waiting time per rute            │
│                                                                  │
│  Seluruh logic berasal dari notebook.                            │
│  TIDAK ada hardcode di Streamlit.                                │
└─────────────────────────┬───────────────────────────────────────┘
                          │ Load artifacts
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STREAMLIT APP                                 │
│  streamlit_app.py                                               │
│                                                                  │
│  Menerima input user → Load artifacts → Routing → Display       │
│  - Hanya layer visualisasi dan interaksi                         │
│  - Tidak mengandung business logic sendiri                       │
└─────────────────────────────────────────────────────────────────┘
```

## Apakah Terintegrasi dengan Notebook?

**Ya, penuh.** Streamlit app TIDAK memiliki logic sendiri. Semua konfigurasi, threshold, dan keputusan berasal dari notebook (`generate_config.py`).

| Item di App | Berasal Dari |
|---|---|
| Speed per koridor | `system_config.json` → dihitung notebook |
| Fallback speed (15 km/h) | `system_config.json` → analisis data historis |
| Edge cap (max 15 menit/segmen) | `system_config.json` |
| Weather multipliers | `system_config.json` → riset transportasi |
| Crowding ML weight (0.7) | `system_config.json` |
| Crowding baseline weight (0.3) | `system_config.json` → historical density |
| Crowding labels & threshold | `system_config.json` |
| Waiting time (GTFS) | `gtfs_waiting_config.json` |
| Transfer time (5 menit) | `system_config.json` |
| Congestion multipliers | `system_config.json` |
| Peak hours (6-9, 16-19) | `system_config.json` |
| Model prediksi | `model_clf_transjakarta.pkl` |

**Satu-satunya yang tidak dari notebook:** string cuaca dari BMKG API (karena interface eksternal). Tapi multiplier-nya tetap dari config.

## Alur Input → Proses → Output

```
┌──────────┐    ┌──────────────┐    ┌──────────────────┐    ┌──────────┐
│  USER    │    │  PROCESSING  │    │    ROUTING       │    │  OUTPUT  │
│  INPUT   │    │              │    │                  │    │          │
└──────────┘    └──────────────┘    └──────────────────┘    └──────────┘

INPUT:
├─ Halte Asal (searchable select)
├─ Halte Tujuan (searchable select)
├─ Hari Perjalanan (hari ini/besok/lusa)
├─ Jam Keberangkatan (slider 0-23)
├─ Prioritas (Waktu/Transfer/Stabil)
├─ Cuaca (realtime BMKG / manual override)

PROCESSING:
├─ Load graph (sequential corridor graph)
│  ├─ 3.616 nodes (halte)
│  ├─ 5.413 sequential edges
│  └─ 98% node terhubung
├─ Load ML model (RandomForest)
├─ Load GTFS headway (253 rute)
├─ Predict crowding via hybrid scoring:
│     crowding = ML × 0.7 + baseline × 0.3 + weather_adjustment
├─ Tentukan weight_attr & confidence_power
│  └─ Berdasarkan prioritas user

ROUTING (Dijkstra):
├─ Goal: Cari jalur dengan cost minimal
├─ Cost = Σ (weight / confidence^power) + Σ transfer_penalty
│  └─ Waktu Tercepat:      power=1.0, penalty=15
│  └─ Transfer Minimal:    power=1.0, penalty=60
│  └─ Rute Paling Stabil:  power=2.0, penalty=15
├─ confidence sequential = 1.0
├─ confidence inferred    = 0.6
├─ confidence fallback    = 0.3

OUTPUT:
├─ Route Timeline (halte berurutan)
├─ Total ETA (travel + waiting + transfer + congestion + weather)
├─ Total Jarak (Haversine per segmen)
├─ Jumlah Halte & Transfer
├─ Kepadatan (hybrid scoring, explainable)
├─ Time Breakdown (pie chart + progress bar)
├─ Analisis Kondisi (peak, cuaca, speed)
└─ Crowding Insight (komponen ML + baseline + weather)
```

## Detail Komponen

### 1. Graph Routing

Graph dibangun dari data historis tap-in/tap-out:

```
Data: corridorID, direction, stopStartSeq, stopEndSeq, tapIn, tapOut
  → Rekonstruksi urutan halte per koridor
  → Edge: halte_n → halte_n+1 (sequential)
  → Edge confidence: 1.0 (sequential), 0.6 (inferred), 0.3 (fallback)
  → Edge weight: min(historical_avg, distance / speed * 60, 15 menit)
```

Hasil: **3.616 node, 5.413 edge, 98% connected.**

### 2. Klasifikasi Kepadatan (ML)

| Model | Akurasi | F1-macro |
|---|---|---|
| RandomForest | 91% | **88%** |

Fitur: hour, haversine_km, num_stops, direction, is_weekend, is_peak_hour, age, is_rain, corridorName, hour_period

Label: relatif terhadap historis koridor di jam yang sama:
- **Sepi** (< 0.8× rata-rata historis)
- **Normal** (0.8-1.5×)
- **Padat** (> 1.5×)

### 3. Hybrid Crowding

```
final_score = ML_predict_proba × 0.7 + historical_baseline × 0.3 + weather_adjustment
```

- **ML**: RandomForest predict_proba, output continuous score 0-1
- **Baseline**: rata-rata historis density per (corridor, hour), dinormalisasi
- **Weather adjustment**: hujan → naik 0.05-0.15 (boarding lebih lambat)

### 4. GTFS Headway

Waiting time per koridor dari GTFS Transjakarta resmi:
- Formula: `waiting = headway / 2`
- Cap: 2-15 menit
- Sumber: `frequencies.txt` dari GTFS (253 rute, 772 entry)

### 5. Weather Integration

| Kondisi | ETA Multiplier | Speed |
|---|---|---|
| Cerah | 1.00× | 15.0 km/jam |
| Mendung | 1.05× | 14.3 km/jam |
| Hujan Ringan | 1.12× | 12.8 km/jam |
| Hujan Lebat | 1.25× | 10.5 km/jam |

### 6. ETA Formula

```
ETA = travel_time + waiting_time + transfer_time + congestion_delay + weather_adjustment
```

- **travel_time**: total bobot edge di graf
- **waiting_time**: dari GTFS headway / kapasitas
- **transfer_time**: 5 menit × jumlah transfer
- **congestion_delay**: peak +20%, padat +10%
- **weather_adjustment**: travel_time × (weather_mult - 1.0)

## Cara Menjalankan

```bash
# 1. Generate config (kalau ada data baru)
python generate_config.py

# 2. Jalankan app
streamlit run streamlit_app.py
```

## Catatan Akademik

Sistem ini dirancang sebagai **Hybrid ML + Empirical Estimation**:

| Komponen | Metode | Validasi |
|---|---|---|
| Klasifikasi | RandomForest | F1 88%, CV 5-fold |
| Bobot Waktu | Historical Average | Stabil, tanpa overfit |
| Crowding | ML + Baseline + Weather | Explainable |
| Waiting Time | GTFS Scheduled Headway | Data resmi operator |
| Graph Routing | Sequential Dijkstra | 98% connected |
| Edge Weight | Capped min_speed (10 km/h) | Cegah outlier idle/dwell |
