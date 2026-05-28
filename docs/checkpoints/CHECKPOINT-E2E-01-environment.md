# CHECKPOINT-E2E-01 - Environment

Tanggal: 2026-05-28
Status: PASS dengan catatan nonfatal

## Versi Tool

```text
Python 3.11.9
pip 24.0 sebelum upgrade
Docker version 28.4.0, build d8eb465
Docker Compose version v2.39.2-desktop.1
git version 2.51.0.windows.1
```

## Dependency Python

Perintah dijalankan:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip show flask
python -m pip show flask-cors
```

Hasil:

- `pip` berhasil di-upgrade ke `26.1.1`.
- Dependency dari `requirements.txt` tersedia.
- `Flask` tersedia versi `3.1.3`.
- `flask-cors` tersedia versi `6.0.2`.
- `werkzeug` tersedia melalui dependency Flask.

## Catatan

Ada warning nonfatal:

```text
The scripts pip.exe, pip3.11.exe and pip3.exe are installed in ...\Python311\Scripts which is not on PATH.
```

Validasi tetap menggunakan `python -m pip`, sehingga warning PATH ini tidak memblokir eksekusi pipeline.

## Acceptance

- Python tersedia: PASS.
- Docker tersedia: PASS.
- Docker Compose tersedia: PASS.
- Git tersedia: PASS.
- Dependency Python terinstall: PASS.
- Dependency backend Flask tersedia: PASS.
- Tidak ada error dependency fatal: PASS.

## Catatan Lanjut

Checkpoint berikutnya: `CHECKPOINT-E2E-02-docker-services.md`.
