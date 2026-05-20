# 🚌 Narasi Demo — Smart Transjakarta Route Optimizer
> **Durasi:** 5–7 menit | **Fokus:** Praktek langsung + Penjelasan hasil

---

## 🎬 PEMBUKAAN (±30 detik)

> *[Buka http://localhost:8501]*

"Kami akan mendemonstrasikan **Smart Transjakarta Route Optimizer** — sistem optimasi rute berbasis **Graph Routing, Machine Learning, BMKG real-time, dan data jadwal GTFS Transjakarta**."

"Semua data dilatih dari **36.556 perjalanan Transjakarta April 2023**."

---

## 🖥️ STATUS SISTEM (±20 detik)

> *[Tunjuk tiga indikator di header]*

"Tiga indikator menunjukkan sistem siap: **● Graf Dimuat, ● Model ML Aktif, ● API Cuaca Terhubung**."

---

## 🗺️ DEMO UTAMA — Input Rute (±1 menit)

> *[Isi form Perencana Rute]*

**Setting yang dipakai:**
- **Halte Asal:** Blok M
- **Halte Tujuan:** Kota
- **Jam Keberangkatan:** 08:00 *(jam sibuk pagi)*
- **Prioritas Optimasi:** Waktu Tercepat
- **Cuaca:** aktifkan toggle **Cuaca BMKG** *(atau pilih Hujan Ringan untuk efek lebih dramatis)*

"Sistem menjalankan algoritma **Dijkstra** pada graf 3.616 halte dengan bobot berdasarkan waktu tempuh historis."

---

## 📈 PENJELASAN HASIL (±2 menit)

> *[Scroll ke Hasil Rute]*

### Lima Kartu Metrik
Tunjuk satu per satu dan jelaskan:

| Kartu | Yang perlu dijelaskan |
|---|---|
| **Total ETA** | "Ini total estimasi waktu — perhatikan badge **Akurat** atau **Estimasi Kasar**" |
| **Total Jarak** | "Dihitung dari koordinat GPS tiap halte (Haversine)" |
| **Jumlah Halte** | "Berapa halte yang dilalui sepanjang rute" |
| **Transfer** | "Berapa kali ganti koridor" |
| **Tingkat Kepadatan** | "Hasil prediksi ML: Sepi / Normal / Padat" |

---

## ⏱️ RINCIAN ETA (±1 menit)

> *[Tunjuk panel Rincian Waktu & Pie Chart]*

"ETA bukan angka ajaib — ini terdiri dari **5 komponen**:"

```
Total ETA = Waktu Tempuh + Waktu Menunggu + Waktu Transfer + Tundaan Macet + Penyesuaian Cuaca
```

**Poin highlight:**
- **Waktu Menunggu** → diambil dari **data GTFS resmi** per koridor, bukan angka flat. Blok M - Kota: ~10 menit. Tertulis juga sumbernya: *"sumber: GTFS (koridor: ...)"*
- **Tundaan Macet** → otomatis +20% jika jam 08:00 dan bukan akhir pekan
- **Penyesuaian Cuaca** → jika hujan, ETA naik hingga 25%

---

## 🚦 KONDISI PERJALANAN (±30 detik)

> *[Tunjuk bagian Analisis Kondisi]*

"Ada 4 kondisi yang terdeteksi: **Status Waktu, Kepadatan, Cuaca, Kecepatan Rata-rata.**"

"Kepadatan dihitung secara hybrid: **30% ML + 70% baseline historis + bobot cuaca** — lebih stabil dan bisa dijelaskan."

---

## 🔄 TRANSFER (jika ada)

> *[Tunjuk Titik Transfer jika rute punya transfer]*

"Setiap titik transfer ditampilkan eksplisit — di halte mana, dari koridor apa ke koridor apa."

---

## 🔬 PENUTUP — 5 Keunggulan (±45 detik)

> *[Sambil scroll up atau tutup dengan slide]*

1. **Graf Rute Berlapis** — Sequential + Inferred edges, 98% terhubung
2. **ML RandomForest** — 200 trees, F1-macro 88%, 5-fold CV
3. **Hybrid Crowding** — ML + baseline historis + cuaca, explainable
4. **BMKG Real-time** — cuaca prakiraan per jam keberangkatan
5. **GTFS Transjakarta** — waiting time nyata per koridor, 253 rute

---

> **"Terima kasih. Kami siap menjawab pertanyaan."**

---
*Data: April 2023 | Model: RandomForest 145MB | Graf: 3.616 halte*
