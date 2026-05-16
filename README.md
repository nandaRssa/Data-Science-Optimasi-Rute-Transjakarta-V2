# 🚌 Smart Transjakarta Route Optimizer

**Sistem Optimasi Rute Transjakarta berbasis Graph Routing, Machine Learning, dan Data Historis**

---

## 📋 Daftar Isi

- [Tentang Proyek](#tentang-proyek)
- [Arsitektur Sistem](#arsitektur-sistem)
- [Alur Pengguna](#alur-pengguna)
- [Komponen Teknis](#komponen-teknis)
- [Cara Menjalankan](#cara-menjalankan)
- [Catatan Akademis](#catatan-akademis)
- [Keterbatasan & Saran Pengembangan](#keterbatasan--saran-pengembangan)
- [Struktur File](#struktur-file)

---

## Tentang Proyek

Proyek ini adalah sistem optimasi rute Transjakarta yang menggabungkan **Graph Routing**, **Machine Learning**, dan **Data Historis** untuk memberikan rekomendasi rute yang optimal berdasarkan:

- **Waktu tempuh** — estimasi perjalanan dari data historis
- **Kepadatan penumpang** — prediksi sepi/normal/padat per koridor per jam
- **Kondisi cuaca** — real-time dari BMKG
- **Prioritas pengguna** — waktu tercepat, transfer minimal, atau rute paling stabil

### 🔍 Masalah yang Diselesaikan

1. **Ketidakpastian waktu tempuh** — variasi besar antar jam dan kondisi cuaca
2. **Kepadatan halte tidak merata** — rute alternatif sering lebih lengang
3. **Pengaruh cuaca** — hujan meningkatkan kemacetan secara signifikan
4. **Kurangnya informasi pengguna** — tidak tahu koridor mana yang sepi atau padat

---

## Arsitektur Sistem

```
┌─────────────────────────────────────────────────────────────────┐
│                    SOURCE OF TRUTH (Notebook)                    │
│                                                                  │
│  generate_config.py                                              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 1. Load & Clean Dataset (36.556 trips)                  │    │
│  │ 2. Feature Engineering (jam, hari, jarak, dll)          │    │
│  │ 3. Training RandomForest (F1-macro 88%)                 │    │
│  │ 4. Hitung Speed per Koridor (128 koridor)              │    │
│  │ 5. Hitung Density Baseline per (koridor, jam)           │    │
│  │    - Weekday vs Weekend (baseline terpisah)             │    │
│  │ 6. Export Model (.pkl) + Config (.json)                 │    │
│  └─────────────────────────────────────────────────────────┘    │
│                            │                                     │
│                            ▼                                     │
│                    SYSTEM ARTIFACTS                               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ model_clf_transjakarta.pkl  (RandomForest)              │    │
│  │ system_config.json          (threshold, speed, weight)  │    │
│  │ gtfs_headway.json           (headway 253 rute)          │    │
│  │ gtfs_waiting_config.json    (waiting time per rute)     │    │
│  └─────────────────────────────────────────────────────────┘    │
└────────────────────────────────┬────────────────────────────────┘
                                 │ load
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STREAMLIT APP                                 │
│                                                                  │
│  streamlit_app.py                                                │
│                                                                  │
│  INPUT: halte asal, tujuan, jam, weekend, cuaca, prioritas      │
│  PROSES: → load graph → load ML → Dijkstra routing → hitung ETA │
│  OUTPUT: → rute, timeline, ETA, crowding, insight              │
│                                                                  │
│  CATATAN: App TIDAK mengandung business logic sendiri.          │
│           Semua threshold dari config hasil notebook.           │
└─────────────────────────────────────────────────────────────────┘
```

### Filosofi Arsitektur

| Lapisan | Peran | Contoh |
|---|---|---|
| **Notebook** | Source of truth | `generate_config.py` — semua analisis, training, export |
| **Config** | Blueprint sistem | `system_config.json` — semua threshold, weight, speed |
| **App** | Layer visualisasi | `streamlit_app.py` — hanya load artifact, tampilkan hasil |

**Prinsip:** App tidak boleh punya hardcoded threshold. Semua angka berasal dari analisis notebook.

---

## Alur Pengguna

### Step-by-step menggunakan aplikasi

```
┌──────────┐    ┌──────────────┐    ┌──────────────────┐    ┌──────────┐
│  INPUT   │    │  PROSES      │    │  ROUTING         │    │  OUTPUT  │
└──────────┘    └──────────────┘    └──────────────────┘    └──────────┘
```

#### 1️⃣ Pilih Halte

- **Halte Asal** — cari dan pilih halte keberangkatan
- **Halte Tujuan** — cari dan pilih halte tujuan
- Tersedia **3.616 halte** dari seluruh jaringan Transjakarta

#### 2️⃣ Atur Perjalanan

| Pengaturan | Fungsi |
|---|---|
| **Weekend toggle** | ON = pola hari libur (lebih sepi). Mempengaruhi baseline crowding dan congestion. |
| **Jam keberangkatan** | Slider 0-23. Jam sibuk (06-09 & 16-19) memiliki congestion +20%. |
| **Prioritas** | Pilih tujuan: Waktu Tercepat / Transfer Minimal / Rute Paling Stabil |

#### 3️⃣ Atur Cuaca

| Mode | Cara Kerja |
|---|---|
| **BMKG Realtime** | Ambil forecast dari BMKG untuk hari ini/besok/lusa |
| **Manual** | Pilih kondisi: Cerah / Mendung / Hujan Ringan / Hujan Lebat |

Cuaca memengaruhi:
- **Kecepatan bus** — hujan turunkan speed hingga 30%
- **ETA multiplier** — hujan lebat +25%
- **Crowding** — hujan naikkan crowding score

#### 4️⃣ Dapatkan Hasil

**A. Summary Card**
| Metrik | Sumber |
|---|---|
| Total ETA | Travel + Waiting + Transfer + Congestion + Weather |
| Total Jarak | Haversine per segmen rute |
| Jumlah Halte | Dari rute yang dipilih Dijkstra |
| Transfer | Jumlah perubahan koridor |
| Kepadatan | Hybrid ML (30%) + Historical Baseline (70%) + Weather |

**B. Route Timeline**
Urutan halte lengkap + waktu tempuh per segmen + koridor aktif

**C. Time Breakdown**
- Travel Time — total bobot edge graf
- Waiting Time — dari GTFS headway / 2 (cap 2-15 menit)
- Transfer Time — 5 menit × jumlah transfer
- Congestion Delay — peak +20%, padat +10%
- Weather Adjustment — travel_time × (multiplier - 1.0)

**D. Crowding Insight**
Penjelasan komponen: `ML: 0.21 × 30% + Baseline: 0.49 × 70%`

**E. Travel Condition Analysis**
Peak/Non-Peak, crowding label, cuaca, effective corridor speed

---

## Komponen Teknis

### 1. Graph Routing

| Properti | Nilai |
|---|---|
| Total Nodes (Halte) | 3.616 |
| Total Edges | 5.413 |
| Connected Components | 66 |
| Largest Component | 3.540 node (98%) |
| Tipe Edge | Sequential (dari urutan data historis) |
| Tipe Graf | DiGraph (directed) |

**Pembangunan Graf:**
```
Data: corridorID + direction + stopStartSeq + stopEndSeq
  → Urutkan berdasarkan sequence number
  → Edge: halte_n → halte_n+1
  → Bobot: min(historical_avg, distance / speed * 60, 15 menit)
  → Edge confidence: 1.0 (sequential), 0.6 (inferred), 0.3 (fallback)
```

### 2. Machine Learning (Klasifikasi Kepadatan)

| Metrik | Nilai |
|---|---|
| Model | RandomForest (scikit-learn) |
| F1-macro (CV) | 88% |
| Accuracy | 91% |
| Features | hour, haversine_km, num_stops, direction, is_weekend, is_peak_hour, age, corridorName, hour_period |
| Target | Relative density (0=Sepi, 1=Normal, 2=Padat) |

**Cara Kerja Crowding:**
```
final_score = ML_predict_proba × 0.3 + historical_baseline × 0.7 + weather_adjustment
```

- **ML** — predict_proba dari RandomForest, continuous score 0-1
- **Baseline** — rata-rata historis density per (corridor, hour), dipisah weekday vs weekend
- **Weather** — hujan +0.05-0.15 (boarding lebih lambat)

### 3. Routing Algorithm (Dijkstra)

```
cost = Σ (weight / confidence^power) + transfer_penalty_per_transfer
```

| Prioritas | Confidence Power | Transfer Penalty |
|---|---|---|
| Waktu Tercepat | 1.0 | 15 menit |
| Transfer Minimal | 1.0 | 60 menit |
| Rute Paling Stabil | 2.0 | 15 menit |

### 4. GTFS Integration

| Data | Fungsi |
|---|---|
| `frequencies.txt` | Headway per rute → waiting time = headway / 2 |
| `stops.txt` | Validasi koordinat halte |

### 5. Weather (BMKG API)

| Kondisi | ETA Multiplier | Speed |
|---|---|---|
| Cerah | 1.00× | 15.0 km/jam |
| Mendung | 1.05× | 14.3 km/jam |
| Hujan Ringan | 1.12× | 12.8 km/jam |
| Hujan Lebat | 1.25× | 10.5 km/jam |

---

## Cara Menjalankan

### Persyaratan

```bash
Python 3.10+
pip install streamlit pandas numpy matplotlib seaborn scikit-learn networkx joblib requests lightgbm xgboost
```

### Jalankan Aplikasi

```bash
cd /path/to/project
streamlit run streamlit_app.py
```

### Generate Ulang Config (jika ada data baru)

```bash
python generate_config.py
```

---

## Catatan Akademis

### Integrasi Notebook vs Aplikasi

Proyek ini mengikuti arsitektur **data science production** standar:

- **Notebook** (`.ipynb`) — untuk eksplorasi, analisis, dan dokumentasi. Source of truth untuk semua keputusan teknis.
- **Script Python** (`generate_config.py`) — versi executable dari notebook. Menghasilkan artifact yang dipakai aplikasi.
- **Streamlit App** (`streamlit_app.py`) — hanya sebagai layer visualisasi. Tidak mengandung business logic sendiri.

### Mengapa Ada Dua File (`.py` dan `.ipynb`)?

Dalam praktik data science industri:

| Format | Fungsi |
|---|---|
| `.ipynb` | Eksplorasi, visualisasi, dokumentasi, presentasi ke stakeholder |
| `.py` | Produksi, pipeline automation, scheduling, deployment |

Keduanya berisi analisis yang sama. `.py` digunakan untuk eksekusi berulang, `.ipynb` untuk presentasi hasil.

### Hybrid Approach: Menggabungkan ML dengan Domain Knowledge

Sistem menggunakan **Hybrid ML + Empirical Estimation**:

| Komponen | Metode | Justifikasi |
|---|---|---|
| Klasifikasi | RandomForest (ML) | F1 88% — terbukti akurat untuk data tabular |
| Bobot Waktu | Historical Average | Lebih stabil dari regresi ML; data terbatas untuk prediksi waktu |
| Crowding | ML + Baseline + Weather | ML untuk pola relatif, baseline untuk kepadatan absolut, weather untuk adjustment real-time |
| Waiting Time | GTFS Scheduled Headway | Data resmi operator, lebih akurat dari estimasi manual |

---

## Keterbatasan & Saran Pengembangan

### Keterbatasan Saat Ini

| Keterbatasan | Dampak | Penyebab |
|---|---|---|
| Data hanya 1 bulan (April 2023) | Tidak bisa prediksi musiman, libur nasional | Dataset terbatas |
| Graph dibangun dari inferensi trip historis | Edge tidak selalu mencerminkan urutan halte sebenarnya | Data urutan halte resmi tidak tersedia di CSV |
| GTFS hanya untuk headway, bukan untuk graph | Routing masih menggunakan graph inferensi | Integrasi parsial |
| Tidak ada data lalu lintas real-time | Congestion menggunakan estimasi rule-based | API lalu lintas berbayar |
| Waiting time adalah scheduled average | Tidak mencerminkan kondisi real-time | GTFS tidak memiliki data real-time |

### Saran Pengembangan (v4)

| Pengembangan | Manfaat |
|---|---|
| **Graph dari GTFS official stop sequence** | Routing akurat sesuai jalur resmi, tidak ada inferred edge |
| **Data multi-bulan** | Prediksi musiman, libur nasional, tren tahunan |
| **Model time-series (LSTM/Prophet)** | Prediksi crowding lebih akurat, bukan hanya rata-rata historis |
| **Integrasi Google Maps/Waze API** | Congestion real-time, ETA lebih presisi |
| **Realtime bus position (GTFS-RT)** | Waiting time aktual, bukan headway average |
| **A/B testing framework** | Validasi kualitas rekomendasi secara empiris |

### Catatan untuk Presentasi Akademik

> "Sistem dikembangkan dengan data historis Transjakarta April 2023 sebagai baseline operational profile. Graph routing dibangun dari rekonstruksi urutan halte berdasarkan data trip historis. Pengembangan selanjutnya mencakup pembangunan graph langsung dari data GTFS resmi untuk mendapatkan topology yang akurat secara operasional, serta ekspansi data multi-bulan untuk menangkap pola musiman."

---

## Struktur File

```
📁 project-root/
├── 📄 streamlit_app.py              # Aplikasi Streamlit (UI + routing)
├── 📄 generate_config.py            # Source of truth (analisis + export)
├── 📄 Optimasi_Rute_Transjakarta_   # Notebook dokumentasi
│     FINAL (1).ipynb
├── 📄 system_config.json            # Konfigurasi sistem (auto-generated)
├── 📄 model_clf_transjakarta.pkl    # Model RandomForest (F1 88%)
├── 📄 gtfs_headway.json             # Headway per rute (GTFS)
├── 📄 gtfs_waiting_config.json      # Waiting time per rute
├── 📄 dfTransjakarta.csv            # Dataset (36.556 trips)
├── 📄 SISTEM_ARCHITECTURE.md        # Dokumentasi arsitektur
├── 📄 system_config_report.md       # Report analisis
├── 📁 backup/                       # Backup file asli
└── 📁 __pycache__/                  # Cache Python
```

---

Dikembangkan sebagai proyek Data Science dan Optimasi Transportasi.  
Graph Routing + Machine Learning + Weather Integration + GTFS.
