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
- **Chart Detail**: candlestick + MA20/50/200, Bollinger Bands, Volume, RSI,
  MACD untuk satu saham, lengkap dengan estimasi stop loss & take profit
  berbasis ATR.
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
saat berjalan. Format ticker IDX di Yahoo Finance selalu diakhiri `.JK`,
contoh: `BBCA.JK`, `TLKM.JK`.

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
