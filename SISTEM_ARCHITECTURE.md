# Arsitektur Sistem — Smart Transjakarta Route Optimizer
**Versi:** 3.0 | **Terakhir diperbarui:** Mei 2026  
**Dataset:** dfTransjakarta.csv (April 2023 — 36.556 perjalanan)

---

## 1. Gambaran Umum

Sistem ini adalah **platform optimasi rute Transjakarta berbasis data** yang menggabungkan tiga teknologi inti:

1. **Graph Routing** — Algoritma Dijkstra pada graf berarah koridor Transjakarta
2. **Machine Learning** — RandomForest untuk klasifikasi tingkat kepadatan
3. **Integrasi Cuaca Real-time** — API BMKG untuk prakiraan cuaca Jakarta

```
 dfTransjakarta.csv (April 2023)
         │
         ▼
 ┌────────────────────────────────────────────────────────────┐
 │            NOTEBOOK (Source of Truth)                      │
 │   Optimasi_Rute_Transjakarta_FINAL.ipynb                   │
 │                                                            │
 │  ① Load & Clean Data       ⑤ Kecepatan per Koridor        │
 │  ② Feature Engineering     ⑥ Historical Density Baseline  │
 │  ③ EDA & Visualisasi       ⑦ Export Model (.pkl)          │
 │  ④ Train RandomForest       ⑧ Export Config (.json)       │
 └──────────────────────┬─────────────────────────────────────┘
                        │ artifact export
                        ▼
 ┌────────────────────────────────────────────────────────────┐
 │                  SYSTEM ARTIFACTS                          │
 │                                                            │
 │  model_clf_transjakarta.pkl   RandomForest (F1-macro 88%) │
 │  system_config.json           Semua config & threshold    │
 │  gtfs_waiting_config.json     Waiting time per koridor    │
 └──────────────────────┬─────────────────────────────────────┘
                        │ load artifacts
                        ▼
 ┌────────────────────────────────────────────────────────────┐
 │               STREAMLIT APP (streamlit_app.py)             │
 │                                                            │
 │  Input User → Build Graph → Dijkstra → ETA → Visualisasi  │
 │  + ML Crowding Prediction + BMKG Weather Integration       │
 └────────────────────────────────────────────────────────────┘
```

---

## 2. Data Pipeline (Notebook)

### 2.1 Data Mentah
| Atribut | Detail |
|---|---|
| Sumber | `dfTransjakarta.csv` |
| Periode | April 2023 (1 bulan) |
| Total baris awal | ~1 juta+ tap-in/tap-out |
| Setelah cleaning | 36.556 trip valid |
| Koridor unik | 221 koridor |
| Halte unik | 3.616 halte |

### 2.2 Tahapan Preprocessing
```
Raw Data
   ↓
① Parse datetime (tapInTime, tapOutTime)
② Drop baris null (tapOutTime, corridorName, koordinat)
③ Hapus duplikat
④ Filter travel_time: 1–300 menit
⑤ Filter speed_kmh < 120 (outlier idle/dwell)
   ↓
df_clean (siap untuk feature engineering)
```

### 2.3 Feature Engineering
Kolom baru yang dibuat dari df_clean:

| Kolom | Formula | Keterangan |
|---|---|---|
| `hour` | `tapInTime.dt.hour` | Jam keberangkatan (0–23) |
| `day_of_week` | `tapInTime.dt.dayofweek` | 0=Senin, 6=Minggu |
| `day_name` | `tapInTime.dt.day_name()` | 'Monday', …, 'Sunday' |
| `is_weekend` | `day_of_week >= 5` | Flag akhir pekan |
| `is_peak_hour` | `(bukan weekend) & (6–9 atau 16–19)` | Flag jam sibuk |
| `hour_period` | Pagi/Siang/Sore/Malam | Periode hari |
| `haversine_km` | Haversine(tap_in, tap_out) | Jarak lurus GPS (km) |
| `num_stops` | `stopEndSeq - stopStartSeq` | Jumlah halte dilewati |
| `travel_time` | `(tapOut - tapIn).total_seconds() / 60` | Waktu tempuh (menit) |
| `speed_kmh` | `haversine_km / (travel_time / 60)` | Kecepatan estimasi |
| `age` | `CURRENT_YEAR - payCardBirthDate` | Umur penumpang |

---

## 3. Model Machine Learning

### 3.1 Tugas: Klasifikasi Kepadatan
Model memprediksi **tingkat kepadatan relatif** suatu koridor pada jam tertentu dibanding rata-rata historisnya.

### 3.2 Labeling (Data-Driven)
```
station_density = jumlah penumpang per (halte, jam)
relative_density = station_density / mean_density_historis_koridor_pada_jam_itu

Label:
  0 → Sepi   (relative_density < 0.8)
  1 → Normal  (0.8 ≤ relative_density ≤ 1.5)
  2 → Padat   (relative_density > 1.5)
```

### 3.3 Fitur Model (9 fitur)
```python
NUM_FEATURES = ['hour', 'haversine_km', 'num_stops', 'direction',
                'is_weekend', 'is_peak_hour', 'age']
CAT_FEATURES = ['corridorName', 'hour_period']
```

### 3.4 Pipeline Training
```
Data → ColumnTransformer
          ├── StandardScaler   (numerical features)
          └── OrdinalEncoder   (categorical features, handle_unknown='use_encoded_value')
       → RandomForestClassifier
            n_estimators = 200
            class_weight = 'balanced'
            random_state = 42
```

### 3.5 Evaluasi
| Metode | Hasil |
|---|---|
| Validasi | 5-fold Stratified Cross Validation |
| Metrik utama | F1-macro |
| F1-macro (CV) | ≈ 88% |
| Split data | 80% train (time-based) / 20% test |

### 3.6 Artifact Output
- `model_clf_transjakarta.pkl` — model siap pakai (±145 MB)

---

## 4. Graf Rute (Graph Routing)

### 4.1 Konstruksi Graf
Graf berarah dibangun dari data historis tap-in/tap-out:

```
Input: corridorID, direction, tapInStopsName, stopStartSeq,
       tapOutStopsName, stopEndSeq, tapInStopsLat/Lon, tapOutStopsLat/Lon

→ Rekonstruksi urutan halte per (koridor, arah)
→ Tambahkan edge antar halte berurutan (sequential)
→ Tambahkan edge inferensi (skip 3–7 halte dalam koridor sama)
→ Bobot edge = min(historical_avg_travel_time, capped_by_distance)
```

### 4.2 Tipe Edge
| Tipe | Definisi | Confidence |
|---|---|---|
| Sequential | Halte n → halte n+1 dalam urutan koridor | 1.0 |
| Inferred | Halte n → halte n+3 s/d n+7 (skip, sama koridor) | 0.6 |

### 4.3 Edge Weight Calibration
```
raw_weight = historical_avg_travel_time (menit)
capped_weight = distance_km / effective_speed * 60

Edge weight = min(raw_weight, capped_weight)

Batas kalibrasi (dari system_config.json):
  min_speed_kmh     = 10   (mencegah edge terlalu lambat karena idle/dwell)
  max_speed_kmh     = 40   (mencegah edge terlalu cepat karena outlier)
  max_segment_min   = 15   (cap maksimum per segmen)
  max_edge_distance = 3.0 km (filter edge yang tidak realistis)
```

### 4.4 Statistik Graf
| Metrik | Nilai |
|---|---|
| Total node (halte) | 3.616 |
| Total corridors | 221 |
| Konektivitas | ~98% node dalam komponen terbesar |

---

## 5. Algoritma Routing (Dijkstra)

### 5.1 Cost Function
```
cost(u → v) = weight(u,v) / max(confidence, 0.1) ^ confidence_power
             + transfer_penalty (jika ganti koridor)
```

### 5.2 Mode Prioritas
| Mode | confidence_power | transfer_penalty | Efek |
|---|---|---|---|
| Waktu Tercepat | 1.0 | 15 menit | Minimasi total waktu |
| Minimal Transfer | 1.0 | 60 menit | Hindari ganti koridor |
| Rute Paling Stabil | 2.0 | 15 menit | Prioritaskan edge sequential (confidence tinggi) |

---

## 6. Prediksi Kepadatan (Hybrid Scoring)

### 6.1 Formula
```
final_score = (ml_score × ml_weight) + (baseline_score × baseline_weight) + weather_adj

Bobot aktual (dari system_config.json):
  ml_weight       = 0.3   (30%)
  baseline_weight = 0.7   (70%)
```

### 6.2 Komponen
| Komponen | Sumber | Bobot |
|---|---|---|
| **ML Score** | RandomForest `predict_proba`, diubah jadi skor 0–1 | 30% |
| **Baseline Score** | Rata-rata historis density per (koridor, jam), dinormalisasi 0–1 | 70% |
| **Weather Adj** | Tambahan berdasarkan kondisi cuaca | +0 s/d +0.15 |

### 6.3 Threshold Label
| Label | Range Score | Keterangan |
|---|---|---|
| Sepi | 0.00 – 0.30 | Lebih lengang dari rata-rata historis |
| Normal | 0.30 – 0.65 | Sesuai rata-rata historis |
| Padat | 0.65 – 1.00 | Lebih ramai dari rata-rata historis |

### 6.4 Weather Adjustment pada Crowding
| Cuaca | Tambahan Skor |
|---|---|
| Cerah | +0.00 |
| Mendung | +0.05 |
| Hujan Ringan | +0.10 |
| Hujan Lebat | +0.15 |

---

## 7. Integrasi Cuaca (BMKG)

### 7.1 Sumber Data
- **API:** `https://api.bmkg.go.id/publik/prakiraan-cuaca?adm4=31.71.01.1001`
- **Wilayah:** Jakarta Pusat (kode ADM4: 31.71.01.1001)
- **Mode:** Real-time (prakiraan) atau manual override

### 7.2 Pemetaan Kondisi
| Kata Kunci BMKG | Kondisi Sistem |
|---|---|
| hujan, rain, petir, thunder | Hujan Ringan / Hujan Lebat |
| berawan, cloudy, mendung | Mendung |
| (lainnya) | Cerah |

### 7.3 Dampak Cuaca pada ETA & Kecepatan
| Kondisi | ETA Multiplier | Kecepatan Efektif |
|---|---|---|
| Cerah | 1.00× | 15.0 km/jam (fallback) |
| Mendung | 1.05× | 14.3 km/jam |
| Hujan Ringan | 1.12× | 12.8 km/jam |
| Hujan Lebat | 1.25× | 10.5 km/jam |

---

## 8. Formula ETA Lengkap

```
Total ETA = Waktu Tempuh
          + Waktu Menunggu
          + Waktu Transfer
          + Tundaan Macet
          + Penyesuaian Cuaca
```

| Komponen | Formula | Nilai Tipikal |
|---|---|---|
| Waktu Tempuh | Σ bobot edge di jalur Dijkstra | Sesuai rute |
| Waktu Menunggu | GTFS per koridor (`waiting = headway/2`), fallback crowding-based | 3–15 menit (GTFS: 253 koridor) |
| Waktu Transfer | `jumlah_transfer × 5 menit` | 0–20 menit |
| Tundaan Macet | Jam sibuk: +20% travel_time; Padat: +10% | 0–30% tambahan |
| Penyesuaian Cuaca | `travel_time × (weather_mult - 1.0)` | 0–25% tambahan |

### Badge Akurasi
- **Akurat** — Rute normal, cuaca tidak ekstrem, transfer ≤ 3
- **Estimasi Kasar** — Transfer > 3 atau ETA > 180 menit atau (padat + hujan lebat)

---

## 9. Kecepatan Per Koridor

Kecepatan operasional **128+ koridor** dihitung dari data historis (median speed per koridor):

```
speed_kmh = haversine_km / (travel_time / 60)
Filter: 5 ≤ speed ≤ 80 km/jam, minimal 10 sample
```

| Tier | Rentang | Contoh Koridor |
|---|---|---|
| Padat/Lokal | 5 – 12 km/jam | Blok M - Kota (7.8), Ciledug - Tendean (7.0) |
| Sedang | 12 – 20 km/jam | Bekasi Barat - Blok M (20.5) |
| Utama/Express | 20 – 30 km/jam | Palem Semi - Bundaran Senayan (21.9) |
| **Fallback** | **15.0 km/jam** | Digunakan jika koridor tidak ada data |

---

## 10. Struktur File Proyek

```
📁 Proyek/
├── 📓 Optimasi_Rute_Transjakarta_FINAL.ipynb   ← Notebook (source of truth)
├── 🐍 streamlit_app.py                          ← Aplikasi web
├── 🐍 generate_config.py                        ← Script bantu generate config
│
├── 📊 dfTransjakarta.csv                        ← Dataset raw (8.9 MB)
│
├── ⚙️  system_config.json                       ← Config utama (speed, ETA, crowding)
├── ⚙️  gtfs_waiting_config.json                 ← Waiting time per koridor dari GTFS (AKTIF — 253 rute)
│
├── 🤖 model_clf_transjakarta.pkl                ← Model RandomForest (145 MB, tidak di-push)
│
├── 🖼️  eda_01_distribusi.png                    ← Visualisasi EDA (dihasilkan notebook)
├── 🖼️  vis_03_feature_importance.png            ← Feature importance (dihasilkan notebook)
├── 🖼️  vis_04_confusion_matrix.png              ← Confusion matrix (dihasilkan notebook)
│
├── 📄 SISTEM_ARCHITECTURE.md                   ← Dokumen ini
├── 📄 NARASI_DEMO.md                            ← Narasi presentasi
└── 📄 README.md                                 ← Panduan umum
```

---

## 11. Cara Menjalankan

```bash
# 1. Jalankan notebook di Google Colab (jika belum ada artifacts)
#    Upload dfTransjakarta.csv → Run All → Download model_clf_transjakarta.pkl

# 2. Pastikan semua file ada di folder yang sama:
#    system_config.json, model_clf_transjakarta.pkl, dfTransjakarta.csv

# 3. Jalankan aplikasi Streamlit
streamlit run streamlit_app.py

# 4. Buka browser ke http://localhost:8501
```

---

## 12. Ringkasan Teknis (untuk Akademik)

| Komponen | Teknologi | Metrik/Keterangan |
|---|---|---|
| Data Pipeline | Pandas, NumPy | 36.556 trip bersih dari raw dataset April 2023 |
| Klasifikasi Kepadatan | RandomForest (200 trees) | F1-macro 88%, 5-fold CV |
| Graph Routing | NetworkX + Dijkstra custom | 3.616 node, ~98% connected |
| Crowding Hybrid | ML 30% + Baseline 70% + Weather | Explainable, data-driven |
| ETA Estimation | Empirical + ML | 5 komponen waktu |
| Kecepatan Koridor | Per-corridor historical median | 128+ koridor, fallback 15 km/jam |
| Integrasi Cuaca | BMKG API real-time | 4 kondisi, multiplier 1.00–1.25× |
| Waiting Time GTFS | gtfs_waiting_config.json | 253 koridor, headway/2, cap 2–15 menit |
| Frontend | Streamlit + Matplotlib + NetworkX | Dark mode UI |
