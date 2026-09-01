# IDX Stock Screener & Technical Signal Dashboard

Aplikasi web (Streamlit) untuk membantu keputusan jual/beli saham IDX
berdasarkan analisis teknikal otomatis, memakai data harga dari **yfinance**.

> ⚠️ **Disclaimer**: Ini alat bantu analisis teknikal, bukan nasihat
> keuangan/investasi. Skor & sinyal dihasilkan dari aturan matematis
> (indikator teknikal) yang bisa salah. Selalu verifikasi harga real-time di
> aplikasi sekuritas Anda sebelum eksekusi order, dan gunakan manajemen
> risiko (stop loss, position sizing) sendiri.

## Fitur

- **Stock Screener**: memberi skor (-100 s/d 100) dan sinyal
  (Strong Buy / Buy / Hold / Sell / Strong Sell) untuk daftar saham yang
  Anda tentukan, berdasarkan harga penutupan terakhir.
- **Risk : Reward otomatis**: Stop Loss & Take Profit dihitung dari support/
  resistance terdekat (bukan sekadar kelipatan ATR tetap), sehingga rasio
  R:R benar-benar berbeda-beda sesuai struktur harga tiap saham.
- **Chart Detail**: candlestick + MA20/50/200, Bollinger Bands, Volume, RSI,
  MACD untuk satu saham, lengkap dengan estimasi stop loss, take profit,
  dan risk:reward berbasis ATR.
- **Foreign / Bandar Flow**: modul upload CSV untuk memvisualisasikan net
  foreign flow (data ini tidak tersedia gratis di yfinance — lihat catatan
  di bawah).

## Instalasi & Menjalankan

```bash
# 1. (opsional) buat virtual environment
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 2. install dependencies
pip install -r requirements.txt

# 3. jalankan aplikasi
streamlit run app.py
```

Browser akan otomatis terbuka di `http://localhost:8501`.

## Deploy Online (Gratis)

1. Push folder ini ke repository GitHub.
2. Buka [share.streamlit.io](https://share.streamlit.io), hubungkan ke repo,
   pilih `app.py` sebagai entry point.
3. Aplikasi akan dapat diakses via URL publik, bisa dibuka dari HP.

## Kustomisasi Daftar Saham

Edit `DEFAULT_TICKERS` di `app.py`, atau langsung ubah lewat sidebar aplikasi
saat berjalan. Anda **boleh menulis ticker tanpa `.JK`** (mis. cukup `BBCA`),
aplikasi akan otomatis menambahkan suffix `.JK` yang dibutuhkan Yahoo Finance
untuk saham IDX.

### Grup Ticker Cepat

Selain daftar manual, sidebar punya multiselect **"Tambah cepat dari grup
ticker"** berisi preset sektor & grup afiliasi:

- Perbankan, Energi & Tambang, Konsumer, Properti, Teknologi & Digital
- Grup Bakrie, Grup Prajogo Pangestu / Barito

Ticker dari grup yang dipilih otomatis digabung dengan daftar manual
(duplikat dihilangkan). Daftar ini didefinisikan di `TICKER_GROUPS` dalam
`app.py` dan bisa Anda edit/tambah sendiri. Catatan: keanggotaan grup
konglomerasi bisa berubah sewaktu-waktu (aksi korporasi, divestasi), jadi
cek ulang keakuratannya secara berkala.

## Kenapa Data Historis Minimal 1 Tahun?

Indikator seperti MA50 dan MA200 butuh minimal 50-200 hari data historis
untuk bisa dihitung; kalau data terlalu pendek (mis. 1 minggu/1 bulan),
sinyal scoring tidak bisa dihasilkan sama sekali. Karena itu aplikasi ini
**selalu mengambil data 1 tahun penuh di belakang layar** untuk perhitungan
indikator, terlepas dari periode yang Anda pilih untuk *tampilan* chart.

Selector **"Periode tampilan chart"** di sidebar hanya memperbesar (zoom)
rentang hari yang terlihat di grafik (1 minggu s/d 1 tahun) — tidak
memengaruhi keakuratan indikator maupun sinyal.

## Tentang Foreign Flow / Bandarmology

Data net foreign buy/sell dan broker summary **tidak tersedia gratis** lewat
yfinance atau API publik lain yang stabil untuk IDX. Sumber yang biasa
dipakai trader:

- Website resmi **IDX** (idx.co.id) — laporan perdagangan harian
- **Stockbit**, **RTI Business**, atau aplikasi sekuritas Anda — biasanya
  punya fitur ekspor data broker summary / foreign flow

Ekspor data tersebut ke CSV (kolom minimal: `date`, dan `netforeignvalue`
atau `foreignbuy`+`foreignsell`, opsional `ticker`), lalu upload di tab
**Foreign/Bandar Flow** pada aplikasi ini untuk divisualisasikan bersama
sinyal teknikal.

## Metodologi Skor (ringkas)

Skor dibentuk dari 6 komponen: trend (MA50/MA200), golden/death cross
MA20-MA50, RSI(14), momentum MACD, rasio volume vs rata-rata 20 hari
(proxy akumulasi/distribusi), dan posisi harga relatif terhadap Bollinger
Band. Detail lengkap ada di tab **Panduan** dalam aplikasi.

## Batasan

- Data yfinance untuk saham IDX kadang delay/terlambat update — jangan
  jadikan satu-satunya acuan real-time.
- Sinyal volume di sini **bukan** bandarmology asli (broker summary),
  hanya proxy sederhana dari lonjakan volume.
- Aplikasi ini tidak melakukan eksekusi order — hanya menyajikan analisis.
