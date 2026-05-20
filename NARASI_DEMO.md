# 🚌 Narasi Demonstrasi Aplikasi
# Smart Transjakarta Route Optimizer

> **Untuk:** Presentasi / Demo Proyek Data Science  
> **Durasi estimasi:** 7–10 menit  
> **Audiens:** Dosen, tim penguji, atau rekan kelompok

---

## 🎬 PEMBUKAAN (±30 detik)

> *[Buka aplikasi di browser, tampilkan halaman utama]*

"Selamat pagi/siang/sore. Kami dari Kelompok 23 akan mendemonstrasikan aplikasi **Smart Transjakarta Route Optimizer** — sebuah sistem optimasi rute transportasi publik yang memadukan tiga teknologi utama: **Graph Routing**, **Machine Learning**, dan **integrasi data cuaca real-time dari BMKG**."

"Aplikasi ini dibangun menggunakan Streamlit dan sepenuhnya ditenagai oleh analisis data historis Transjakarta bulan April 2023 — mencakup lebih dari **ratusan ribu data perjalanan penumpang**."

---

## 🖥️ BAGIAN 1 — Tampilan Utama & Status Sistem (±1 menit)

> *[Arahkan kursor ke bagian header dan status]*

"Saat pertama kali dibuka, aplikasi langsung menampilkan **header informatif** berisi jam real-time dan tanggal hari ini."

"Di bawahnya terdapat tiga indikator status sistem:"

- **✅ Graph Loaded** — menandakan graf rute Transjakarta berhasil dibangun dari data historis
- **✅ ML Model Active** — model Machine Learning klasifikasi kepadatan sudah siap digunakan
- **✅ Weather API Connected** — koneksi ke API cuaca BMKG aktif

---

## 📊 BAGIAN 2 — Sidebar: Statistik Sistem (±1 menit)

> *[Buka sidebar di kiri layar]*

"Di sidebar sebelah kiri, kita bisa melihat **statistik lengkap sistem** yang dibangun:"

- **Total Stops** — jumlah halte unik yang terdaftar dalam graf
- **Total Edges** — koneksi antar halte yang mewakili segmen perjalanan
- **Total Corridors** — jumlah koridor Transjakarta yang tercakup

"Yang menarik adalah **Topology Quality** — sistem menghitung seberapa baik konektivitas grafnya. Kita bisa lihat berapa persen node yang terhubung dalam satu komponen terbesar, serta berapa halte yang menjadi **Transfer Hub** — titik pergantian antar koridor."

"Di bagian bawah ada ringkasan dataset: jumlah trip, periode data, dan rata-rata waktu tempuh."

---

## 🗺️ BAGIAN 3 — Route Planner: Input Perjalanan (±2 menit)

> *[Arahkan ke bagian Route Planner di tengah halaman]*

"Inti dari aplikasi ini adalah **Route Planner**. Mari kita coba simulasi perjalanan nyata."

### Langkah 1 — Pilih Halte

> *[Pilih Origin: **Blok M**, Destination: **Kota**]*

"Saya pilih rute dari **Blok M** menuju **Kota** — salah satu rute tersibuk Transjakarta yang melintasi pusat kota Jakarta."

### Langkah 2 — Atur Parameter Perjalanan

> *[Atur slider dan toggle]*

"Di bagian **Travel Settings**, kita bisa mengatur tiga parameter penting:"

1. **Weekend/Holiday Toggle** — mengaktifkan mode akhir pekan yang memengaruhi pola kemacetan
2. **Departure Hour** — jam keberangkatan. Saya set jam **08:00** untuk mensimulasikan jam sibuk pagi hari
3. **Optimization Priority** — ada tiga pilihan:
   - *Waktu Tercepat*: Dijkstra meminimalkan total ETA
   - *Minimal Transfer*: menghindari pergantian koridor sebanyak mungkin
   - *Rute Paling Stabil*: memprioritaskan jalur dengan data historis real, menghindari edge inferensi

### Langkah 3 — Kondisi Cuaca

> *[Tunjukkan toggle BMKG dan pilihan manual]*

"Untuk cuaca, sistem menyediakan dua mode:"
- **Mode BMKG Real-time**: sistem otomatis mengambil prakiraan cuaca dari API BMKG untuk hari ini, besok, atau lusa
- **Mode Manual**: pengguna bisa memilih sendiri kondisi cuaca — Cerah, Mendung, Hujan Ringan, atau Hujan Lebat

"Kondisi cuaca ini bukan sekadar dekorasi — hujan lebat dapat **menambah ETA hingga 25%** karena penurunan kecepatan operasional bus."

---

## 📈 BAGIAN 4 — Hasil Rute & ETA (±2 menit)

> *[Scroll ke bawah ke bagian Hasil Rute setelah rute ditemukan]*

"Setelah klik proses, sistem menjalankan algoritma **Dijkstra** pada graf berarah Transjakarta dan menampilkan hasil lengkap."

### Kartu Metrik Utama

"Ada lima kartu ringkasan:"

| Metrik | Penjelasan |
|---|---|
| **Total ETA** | Estimasi waktu total perjalanan (menit) |
| **Total Jarak** | Jarak tempuh berdasarkan koordinat GPS (km) |
| **Jumlah Halte** | Berapa halte yang dilewati |
| **Transfer** | Berapa kali ganti koridor |
| **Tingkat Kepadatan** | Sepi / Normal / Padat — hasil prediksi ML |

"Perhatikan badge di Total ETA — bisa **Akurat** atau **Estimasi Kasar**, tergantung kompleksitas rute dan kondisi perjalanan."

---

## ⏱️ BAGIAN 5 — Rincian Waktu & Pie Chart (±1 menit)

> *[Tunjukkan bagian Rincian Waktu]*

"Keunggulan sistem kami adalah **transparansi perhitungan ETA**. Total ETA bukan angka ajaib — melainkan hasil penjumlahan lima komponen:"

```
Total ETA = Waktu Tempuh + Waktu Menunggu + Waktu Transfer + Tundaan Macet + Penyesuaian Cuaca
```

"Di sebelah kanan, pie chart menunjukkan **proporsi masing-masing komponen** secara visual. Ini membantu penumpang memahami mengapa perjalanan bisa lebih lama dari ekspektasi."

"Di bawahnya ada **progress bar komposisi ETA** — representasi horizontal yang lebih intuitif."

---

## 🚦 BAGIAN 6 — Analisis Kondisi Perjalanan (±1 menit)

> *[Scroll ke Analisis Kondisi Perjalanan]*

"Bagian ini menampilkan empat kondisi real-time yang memengaruhi perjalanan:"

1. **Status Waktu** — apakah ini jam sibuk (merah) atau luar jam sibuk (hijau)
2. **Kepadatan** — hasil hybrid: **70% Machine Learning + 30% baseline historis + bobot cuaca**
3. **Cuaca** — kondisi yang dipilih/diambil dari BMKG
4. **Kecepatan Rata-rata** — estimasi kecepatan operasional bus di rute tersebut

"Di bawahnya ada **Wawasan Kepadatan** — penjelasan kontekstual mengapa bus di rute ini diprediksi sepi/normal/padat pada jam tersebut, berdasarkan pola historis."

---

## 🔄 BAGIAN 7 — Titik Transfer & Faktor ETA (±30 detik)

> *[Tunjukkan bagian Transfer Points jika ada]*

"Jika rute memerlukan pergantian koridor, sistem menampilkan **setiap titik transfer** secara eksplisit — di halte mana, dari koridor apa ke koridor apa, dan berapa menit estimasi waktu transfernya."

"Terakhir, grafik **Faktor yang Mempengaruhi ETA** menunjukkan bobot relatif setiap faktor:"
- Jumlah halte: 35%
- Jam sibuk: 25%
- Koridor: 20%
- Cuaca: 12%
- Kepadatan: 8%

---

## 🔬 PENUTUP — Keunggulan Teknis (±1 menit)

> *[Bisa sambil scroll up ke atas atau tampilkan slide presentasi]*

"Sebelum kami tutup, ada beberapa keunggulan teknis yang ingin kami highlight:"

### 1. Graf Rute Berlapis
Sistem membangun graf berarah dengan **tiga jenis edge**:
- **Sequential** — edge langsung antar halte bersebelahan dalam koridor (kepercayaan 100%)
- **Inferred** — edge antara halte yang tidak bersebelahan dalam koridor yang sama (kepercayaan 60%)
- Edge dengan **capping** agar waktu tempuh tidak tidak realistis

### 2. Klasifikasi Kepadatan Berbasis ML
Model **Random Forest** dilatih dengan 200 estimator menggunakan data historis April 2023. Evaluasi menggunakan **5-fold cross-validation** dengan metrik F1-macro.

### 3. Hybrid Crowding Score
Prediksi kepadatan bukan hanya dari ML, tapi **dipadukan** dengan baseline historis dan kondisi cuaca — menghasilkan skor yang lebih robust dan explainable.

### 4. Integrasi BMKG Real-time
Cuaca diambil langsung dari API resmi BMKG berdasarkan kode wilayah Jakarta Pusat, disesuaikan dengan jam keberangkatan yang dipilih pengguna.

---

> **"Terima kasih. Kami membuka sesi tanya jawab."**

---

*Catatan: Aplikasi menggunakan data historis April 2023. Prediksi kepadatan dan ETA didasarkan pada pola historis tersebut dan tidak memperhitungkan perubahan musiman atau kejadian tak terduga.*
