from __future__ import annotations


def detect_sheet_type(sheet_name: str, dataset_kind: str = "rab") -> str:
    name = sheet_name.lower().strip()
    if dataset_kind == "nomenklatur":
        return "NOMENKLATUR"
    if "rekap" in name:
        return "REKAP"
    if "prioritas" in name or "usulan" in name or "proker" in name:
        return "PROGRAM_CONTEXT"
    if name in {"rab", "rpd", "contoh rpd"}:
        return "RAB_LIKE"
    if "master iku" in name:
        return "MASTER_IKU"
    if "master akun" in name or "ket_akun" in name:
        return "MASTER_AKUN"
    return "DETAIL_KEGIATAN"
