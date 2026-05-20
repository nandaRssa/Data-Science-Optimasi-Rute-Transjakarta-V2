# System Configuration Report — Smart Transjakarta Route Optimizer

## Dataset Overview
- **Total Trips:** 36,556
- **Corridors:** 221
- **Unique Stops:** 3616
- **Period:** April 2023

## Speed Analysis
- Average Speed: 10.3 km/jam
- Median Speed: 8.0 km/jam
- Global Fallback Speed: 15.0 km/jam
- Corridors with speed data: 128
- Speed Range: 5.4 - 21.9 km/jam
- Effective Speed by Weather (applied to base corridor speed):
  - Cerah: 100%
  - Mendung: 95%
  - Hujan Ringan: 85%
  - Hujan Lebat: 70%

## Weather Impact
- Weather Multipliers:
  - Cerah: 1.0x
  - Mendung: 1.05x
  - Hujan Ringan: 1.12x
  - Hujan Lebat: 1.25x
- Travel Time Ratio (Hujan/Cerah): 1.25x

## Crowding Rules
- **Padat:** Weekdays 6:00-9:00 & 16:00-19:00
- **Normal:** Weekdays 10:00-15:00
- **Sepi:** After 20:00, weekends
- Peak/Non-Peak Volume Ratio: 3.2x

## ETA Formula
ETA = travel_time + waiting_time + transfer_time + congestion_delay + weather_adjustment
- Waiting Time: Sepi=3m, Normal=5m, Padat=8m
- Transfer Time: 5 menit per transfer
- Congestion: Peak +20%, Crowded +10%

## Top Corridors by Volume
| Corridor | Avg Time | Avg Stops | Avg Dist |
|---|---|---|---|
| Cibubur - Balai Kota | 72.1 mnt | 5.0 | 5.3 km |
| Ciputat - CSW | 75.9 mnt | 5.9 | 2.1 km |
| Harmoni - Jakarta Internationa | 72.1 mnt | 3.7 | 2.3 km |
| Pulo Gadung - Monas | 71.7 mnt | 6.4 | 3.4 km |
| Kampung Rambutan - Pondok Gede | 71.9 mnt | 14.4 | 1.6 km |
| Kalideres - Bundaran HI via Ve | 69.9 mnt | 4.6 | 4.3 km |
| Rusun Pondok Bambu - Walikota  | 73.8 mnt | 5.9 | 1.5 km |
| Kebayoran Lama - Tanah Abang | 73.1 mnt | 9.4 | 2.2 km |
| Rusun Rawa Bebek - Kodamar | 74.7 mnt | 7.6 | 2.6 km |
| BKN - Blok M | 73.6 mnt | 8.9 | 2.5 km |
