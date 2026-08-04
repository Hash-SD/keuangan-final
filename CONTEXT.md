# SILARAS SD — Konteks Domain

Glosarium ini menetapkan bahasa bersama untuk domain anggaran RAB, RPD/IKU, dan Nomenklatur pada SILARAS SD. Gunakan istilah kanonik berikut ketika membaca kode, menulis test, atau menjelaskan perubahan kepada AI.

## Dataset dan Sumber

**Dataset aktif**:
Bundel workbook Excel yang telah diunggah, divalidasi, dan berstatus `COMMITTED`; bundel inilah satu-satunya sumber resmi pipeline produksi.
_Avoid_: sample data, file sementara, dataset lama.

**Workbook RAB**:
Workbook Excel yang memuat rencana anggaran dan nominal item anggaran. Pada workbook yang memiliki sheet `RAB`, sheet tersebut menjadi sumber nominal utama.
_Avoid_: workbook detail sebagai sumber nominal utama.

**Workbook Nomenklatur**:
Workbook master yang memetakan hierarki kegiatan ke detail Nomenklatur dan kode IKU.
_Avoid_: tabel mapping biasa.

**Nomenklatur**:
Hierarki kegiatan yang menghubungkan kegiatan, KRO, RO, komponen, sub-komponen, detail kegiatan, dan IKU.
_Avoid_: hanya nama kegiatan.

**IKU**:
Indikator kinerja yang menerima alokasi item anggaran; satu item dapat dialokasikan ke satu atau beberapa IKU.
_Avoid_: akun, kegiatan.

**Item anggaran**:
Satu baris biaya yang memiliki identitas sumber, uraian, nominal, akun, dan konteks kegiatan.
_Avoid_: subtotal, total sheet, baris header.

## Lapisan Data

**Bronze**:
Representasi sel-per-sel workbook Excel yang mempertahankan nilai, formula, warna, format, merged cell, dan lineage sumber untuk audit.
_Avoid_: tabel transaksi final.

**Silver**:
Hasil parsing, klasifikasi, normalisasi, rekonsiliasi, dan mapping yang masih dapat memiliki baris review atau dukungan audit.
_Avoid_: data yang sudah pasti dipublikasikan.

**Gold**:
Data faktual yang lolos quality gate dan siap dipublikasikan ke PostgreSQL, Trino, dan Superset.
_Avoid_: semua hasil parsing.

**Detail-support**:
Sheet rincian akun yang dipertahankan untuk audit dan rekonsiliasi, tetapi tidak dijumlahkan ke Gold jika workbook memiliki sheet `RAB` utama.
_Avoid_: sumber kedua untuk menambah total Gold.

**Orphan item**:
Leaf item pada sheet `RAB` yang tidak tercakup formula parent terdekat dan karenanya dikeluarkan dari Gold secara default.
_Avoid_: item hilang tanpa alasan.

## Identitas dan Publikasi

**Dataset session ID**:
Identitas bundel upload yang mengikat file sumber, artefak, dan run agar data lintas sesi tidak tercampur.
_Avoid_: hanya nama file.

**Pipeline run ID**:
Identitas satu eksekusi transformasi untuk satu dataset session.
_Avoid_: DAG ID.

**Airflow DAG run ID**:
Identitas eksekusi orkestrator Airflow yang menjalankan task pipeline dan membawa konfigurasi dataset/run.
_Avoid_: pipeline run ID, walaupun keduanya berkorelasi.

**System truth**:
Snapshot status teragregasi yang membandingkan artefak data, quality gate, metrik, UAT, storage, dashboard, dan service runtime.
_Avoid_: status UI yang di-hardcode.

**Quality gate**:
Pemeriksaan blocking sebelum Gold dapat dipublikasikan; minimal mencakup kelengkapan, identitas dataset/run, grain unik, validitas angka, dan konsistensi weighted amount.
_Avoid_: validasi kosmetik.

**Review IKU**:
Antrean item Silver yang membutuhkan koreksi mapping IKU/akun sebelum pipeline dijalankan ulang untuk membangun Gold.
_Avoid_: perubahan langsung pada Gold.

