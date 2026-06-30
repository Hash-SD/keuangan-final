from __future__ import annotations

import difflib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


VALID_ACCOUNT_PREFIXES = ("51", "52", "53", "57")
REVIEW_IKU_LABEL = "Perlu review IKU"
REVIEW_ACCOUNT_LABEL = "Perlu review akun"
IKU_SUGGESTED_REVIEW_FLAG = "IKU_SUGGESTED_REVIEW"
OVERRIDE_PATH = Path("outputs/reports/iku_review_overrides.json")
ACCOUNT_NAME_BY_CODE = {
    "521111": "Belanja Keperluan Perkantoran",
    "521211": "Belanja Bahan",
    "521213": "Belanja Honor Output Kegiatan",
    "521219": "Belanja Barang Non Operasional",
    "521811": "Belanja Barang Persediaan",
    "521832": "Belanja Barang Persediaan Lainnya",
    "522141": "Belanja Sewa",
    "522151": "Belanja Jasa Profesi",
    "522191": "Belanja Jasa Lainnya",
    "524111": "Belanja Perjalanan Dinas",
}

ACCOUNT_CONTEXT_RULES: list[tuple[str, str, str]] = [
    (r"iklan|video profil|pemeliharaan web|pemeiharaan web|desain web|website|media sosial", "522191", "Belanja Jasa Lainnya"),
    (
        r"sg\s*\d+|kuliah tamu|sertifikasi|pelatihan|pengarah|penanggungjawab|ketua pelaksana|wakil ketua|anggota|\bjam\b",
        "522151",
        "Belanja Jasa Profesi",
    ),
    (
        r"perjalanan dinas|uang harian|transport|tiket|penginapan|hotel|boarding|kunjungan|lapangan|perjalanan",
        "524111",
        "Belanja Perjalanan Dinas",
    ),
    (r"sewa|rental|bus|kendaraan|gedung|ruang", "522141", "Belanja Sewa"),
    (r"narasumber|honorarium|honor|jasa profesi|praktisi|pembicara|moderator", "522151", "Belanja Jasa Profesi"),
    (
        r"konsumsi|makan|snack|bahan|atk|materai|spanduk|cetak|fotokopi|kimia|praktikum|plakat|banner|baterai|container box|galon|gula|kopi|teh|tinta|tissue|pena|kertas|note book|stella|rapat|paket meeting",
        "521211",
        "Belanja Bahan",
    ),
    (r"software|lisensi|aplikasi|website|domain|hosting", "521111", "Belanja Keperluan Perkantoran"),
    (r"barang non operasional|peralatan|inventaris", "521219", "Belanja Barang Non Operasional"),
]


def is_valid_account_code(value: object) -> bool:
    if value is None or pd.isna(value):
        return False
    match = re.search(r"\b(\d{6})\b", str(value))
    if not match:
        return False
    code = match.group(1)
    if not code.startswith(VALID_ACCOUNT_PREFIXES):
        return False
    return not code.endswith("000") or code in ACCOUNT_NAME_BY_CODE


def extract_valid_account(value: object) -> tuple[str | None, str | None]:
    if value is None or pd.isna(value):
        return None, None
    text = str(value).strip()
    match = re.search(r"\b(\d{6})\b", text)
    if not match:
        return None, None
    code = match.group(1)
    if not is_valid_account_code(code):
        return None, None
    name = re.sub(rf"\b{code}\b\s*[-:]?", "", text).strip(" -:|")
    return code, clean_display_text(name) or None


def has_explicit_invalid_account_code(row: pd.Series) -> bool:
    for field in ("akun", "kode_akun", "nama_akun"):
        value = row.get(field)
        if value is None or pd.isna(value):
            continue
        for code in re.findall(r"\b\d{6}\b", str(value)):
            if not is_valid_account_code(code):
                return True
    return False


def clean_display_text(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    parts = [part.strip() for part in re.split(r"\|", str(value)) if part and part.strip()]
    if not parts:
        parts = [str(value).strip()]
    cleaned: list[str] = []
    for part in parts:
        text = re.sub(r"\s+", " ", part).strip(" -:;")
        if not text:
            continue
        if text.upper() in {"#REF!", "N/A", "NA", "NAN", "NONE"}:
            continue
        if re.fullmatch(r"\d+(?:[.,]\d+)?", text):
            continue
        if re.fullmatch(r"Prioritas\s+\d+", text, flags=re.I):
            continue
        cleaned.append(text)
    if not cleaned:
        return None
    result = " - ".join(dict.fromkeys(cleaned))
    result = re.sub(r"\s+", " ", result).strip(" -:;")
    return result or None


def clean_activity(value: object, fallback: object = None) -> str | None:
    text = clean_display_text(value) or clean_display_text(fallback)
    if not text:
        return None
    text = re.sub(r"\b(\d{3,4}(?:\.[A-Z0-9]+)+\.[A-Z]{2})\.\d{6}\b", r"\1", text)
    text = re.sub(r"^Kegiatan\s*-\s*", "", text, flags=re.I)
    parts = [part.strip() for part in re.split(r"\s*-\s*", text) if part.strip()]
    if len(parts) >= 3 and re.search(r"\b\d{3,4}\.[A-Z0-9.]+", parts[0]):
        text = f"{parts[0]} - {parts[1]}"
    text = re.sub(r"\b\d{7,}\b", "", text)
    text = re.sub(r"\s+", " ", text).strip(" -:;")
    return text or None


def clean_account_name(value: object) -> str | None:
    text = clean_display_text(value)
    if not text:
        return None
    text = re.sub(r"^Kegiatan\s*-\s*", "", text, flags=re.I).strip()
    belanja_match = re.search(r"\b(Belanja\b.*)$", text, flags=re.I)
    if belanja_match:
        text = belanja_match.group(1)
    text = re.sub(r"^\d{3,4}(?:\.[A-Z0-9]+)+\s*[-.]?\s*", "", text)
    text = re.sub(r"\b\d{3,4}(?:\.[A-Z0-9]+)+\b", "", text)
    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r"\s+", " ", text).strip(" -:;")
    return text or None


def clean_account_label(row: pd.Series) -> tuple[str | None, str | None, str]:
    code, name = extract_valid_account(row.get("akun"))
    if not code:
        code, name = extract_valid_account(row.get("kode_akun"))
    if not code and is_valid_account_code(row.get("nama_akun")):
        code, name = extract_valid_account(row.get("nama_akun"))
    if code:
        name = clean_account_name(name) or clean_account_name(row.get("nama_akun")) or name
        name = ACCOUNT_NAME_BY_CODE.get(code, name)
        label = f"{code} - {name}" if name else code
        return code, name, label
    if has_explicit_invalid_account_code(row):
        return None, None, REVIEW_ACCOUNT_LABEL
    inferred = infer_account_from_context(row)
    if inferred:
        code, name = inferred
        return code, name, f"{code} - {name}"
    return None, None, REVIEW_ACCOUNT_LABEL


def infer_account_from_context(row: pd.Series) -> tuple[str, str] | None:
    source_text = " ".join(
        str(value)
        for value in [
            row.get("uraian_detail"),
            row.get("kegiatan"),
            row.get("cluster_kegiatan"),
            row.get("source_sheet"),
            row.get("akun"),
            row.get("nama_akun"),
        ]
        if value is not None and not pd.isna(value)
    ).lower()
    source_text = re.sub(r"\s+", " ", source_text)
    for pattern, code, name in ACCOUNT_CONTEXT_RULES:
        if re.search(pattern, source_text, flags=re.I):
            return code, name
    return None


def public_quality_flag(quality_flags: list[str], has_code: bool, has_iku: bool) -> str:
    flags = [flag for flag in dict.fromkeys(quality_flags) if flag and flag != "OK"]
    blocking = [flag for flag in flags if flag not in {"IKU_SUGGESTED_REVIEW"}]
    if has_code and has_iku and not blocking:
        return "OK"
    if has_code and has_iku:
        return "VALIDATED_WITH_RULE"
    return "REVIEW_QUEUE"


def public_mapping_status(match: NomenMatch, has_code: bool, override: dict[str, object] | None) -> str:
    if override and override.get("iku_codes"):
        return "reviewed_override"
    if has_code and match.iku_codes:
        if match.method in {"source_iku", "keyword_nomenklatur_rule", "token_overlap", "fuzzy_text"}:
            return "mapped_from_nomenklatur"
        return "mapped_by_context_rule"
    return "review_queue"


def normalize_match_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = clean_display_text(value) or ""
    text = text.lower()
    text = re.sub(r"\b\d+(?:\.\w+)*\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    stopwords = {
        "dan",
        "atau",
        "the",
        "di",
        "ke",
        "dari",
        "untuk",
        "program",
        "studi",
        "sains",
        "data",
        "fakultas",
        "kegiatan",
        "pelaksanaan",
        "belanja",
    }
    tokens = [token for token in text.split() if len(token) > 2 and token not in stopwords]
    return " ".join(tokens)


def split_iku_codes(value: object) -> list[str]:
    if value is None or pd.isna(value):
        return []
    codes = re.findall(r"\bIK\s*\d+(?:\.\d+)?\b", str(value), flags=re.I)
    result: list[str] = []
    for code in codes:
        normalized = re.sub(r"\s+", " ", code.upper()).replace("IK ", "IK ")
        if normalized not in result:
            result.append(normalized)
    return result


@dataclass(frozen=True)
class NomenMatch:
    detail_id: str | None
    detail_kegiatan: str | None
    nomenklatur_path: str | None
    iku_codes: str | None
    score: float
    method: str
    review_required: bool = False


def _build_nomen_candidates(nomenklatur: pd.DataFrame, bridge: pd.DataFrame) -> list[dict[str, object]]:
    if nomenklatur.empty:
        return []
    iku_by_detail: dict[str, list[str]] = {}
    if not bridge.empty and {"detail_id", "iku_kode"}.issubset(bridge.columns):
        for detail_id, group in bridge.groupby("detail_id", dropna=False):
            codes = []
            for value in group["iku_kode"].dropna():
                for code in split_iku_codes(value):
                    if code not in codes:
                        codes.append(code)
            iku_by_detail[str(detail_id)] = codes
    candidates: list[dict[str, object]] = []
    for _, row in nomenklatur.iterrows():
        detail_id = str(row.get("detail_id") or "")
        fields = [
            row.get("detail_kegiatan"),
            row.get("sub_komponen_nomenklatur"),
            row.get("komponen_nomenklatur"),
            row.get("ro_nomenklatur"),
            row.get("nomenklatur_path"),
        ]
        normalized = normalize_match_text(" ".join(str(field) for field in fields if pd.notna(field)))
        codes = iku_by_detail.get(detail_id) or split_iku_codes(row.get("iku_raw"))
        if normalized and codes:
            candidates.append(
                {
                    "detail_id": detail_id,
                    "detail_kegiatan": clean_display_text(row.get("detail_kegiatan")),
                    "sub_komponen_nomenklatur": clean_display_text(row.get("sub_komponen_nomenklatur")),
                    "nomenklatur_path": clean_display_text(row.get("nomenklatur_path")),
                    "normalized": normalized,
                    "tokens": set(normalized.split()),
                    "iku_codes": codes,
                }
            )
    return candidates


def _best_nomen_match(row: pd.Series, candidates: list[dict[str, object]]) -> NomenMatch:
    existing_codes = split_iku_codes(row.get("iku"))
    if existing_codes:
        return NomenMatch(None, None, clean_display_text(row.get("nomenklatur_path")), "; ".join(existing_codes), 1.0, "source_iku")
    keyword_match = _keyword_nomen_match(row, candidates)
    if keyword_match.iku_codes:
        return keyword_match
    source_text = " ".join(
        str(value)
        for value in [row.get("kegiatan"), row.get("cluster_kegiatan"), row.get("nomenklatur_path"), row.get("uraian_detail")]
        if value is not None and not pd.isna(value)
    )
    normalized = normalize_match_text(source_text)
    if not normalized or not candidates:
        return NomenMatch(None, None, clean_display_text(row.get("nomenklatur_path")), None, 0.0, "not_matched")
    source_tokens = set(normalized.split())
    best: tuple[float, dict[str, object] | None, str, int] = (0.0, None, "not_matched", 0)
    for candidate in candidates:
        target = str(candidate["normalized"])
        target_tokens = candidate["tokens"]
        shared_tokens = len(source_tokens & target_tokens)
        overlap = shared_tokens / max(len(source_tokens | target_tokens), 1)
        ratio = difflib.SequenceMatcher(None, normalized, target).ratio()
        score = max(overlap, ratio * 0.85)
        method = "token_overlap" if overlap >= ratio * 0.85 else "fuzzy_text"
        if score > best[0]:
            best = (score, candidate, method, shared_tokens)
    score, candidate, method, shared_tokens = best
    high_confidence = (method == "token_overlap" and score >= 0.30 and shared_tokens >= 2) or (method == "fuzzy_text" and score >= 0.50 and shared_tokens >= 2)
    if candidate is None or not high_confidence:
        return NomenMatch(None, None, clean_display_text(row.get("nomenklatur_path")), None, score, "not_matched")
    return NomenMatch(
        str(candidate.get("detail_id") or "") or None,
        candidate.get("detail_kegiatan"),
        candidate.get("nomenklatur_path"),
        "; ".join(candidate.get("iku_codes") or []),
        score,
        method,
    )


def _keyword_nomen_match(row: pd.Series, candidates: list[dict[str, object]]) -> NomenMatch:
    source_text = " ".join(
        str(value)
        for value in [row.get("kegiatan"), row.get("cluster_kegiatan"), row.get("uraian_detail"), row.get("source_sheet")]
        if value is not None and not pd.isna(value)
    ).lower()
    if not source_text or not candidates:
        return NomenMatch(None, None, clean_display_text(row.get("nomenklatur_path")), None, 0.0, "not_matched")

    rules: list[tuple[str, str, float, bool]] = [
        (r"kurikulum|obe|rps|buku ajar|modul ajar", "fgd kurikulum", 0.96, False),
        (r"akreditasi|laminfokom|ami|audit mutu", "workshop strategi akreditasi unggul", 0.92, True),
        (r"sertifikasi kompetensi|pelatihan dan sertifikasi|biaya sertifikasi", "kegiatan sertifikasi", 0.95, False),
        (r"kuliah lapangan|kunjungan industri", "praktik lapangan", 0.90, True),
        (r"studium generale|kuliah tamu|praktisi mengajar", "kuliah tamu praktisi mengajar", 0.90, True),
        (r"sekolah binaan|desa binaan|pengabdian masyarakat", "kegiatan desa binaan dan pengabdian masyarakat", 0.88, True),
        (r"satria|softskill|soft skill|kompetensi mahasiswa", "dukungan kompetensi akademik dan non akademik", 0.84, True),
        (r"operasional fakultas|operasional kantor|operasional program studi|perkantoran|pks ps sains data|\bpks\b", "operasional perkantoran", 0.88, True),
        (r"logbook|perwalian|bimbingan akademik|konseling", "kegiatan monitoring dan bimbingan akademik", 0.86, True),
        (r"lisensi|software|dropbox|zoom|website|web|video profil|media sosial", "digitalisasi pembelajaran", 0.84, True),
        (r"dies natalis", "dies natalis", 0.86, True),
        (r"praktikum|laboratorium|lab", "praktik lapangan", 0.86, True),
        (r"pmb|penerimaan mahasiswa baru", "pelaksanaan penerimaan mahasiswa baru", 0.92, False),
        (r"publikasi|penelitian|hibah penelitian|pengabdian", "kegiatan hibah penelitian kompetitif internal", 0.82, True),
    ]
    normalized_candidates = []
    for candidate in candidates:
        haystack = normalize_match_text(
            " ".join(
                str(value)
                for value in [
                    candidate.get("detail_kegiatan"),
                    candidate.get("sub_komponen_nomenklatur"),
                    candidate.get("nomenklatur_path"),
                ]
                if value
            )
        )
        normalized_candidates.append((candidate, haystack))

    for source_pattern, target_text, score, review_required in rules:
        if not re.search(source_pattern, source_text, flags=re.I):
            continue
        target_norm = normalize_match_text(target_text)
        for candidate, haystack in normalized_candidates:
            if target_norm and target_norm in haystack:
                return NomenMatch(
                    str(candidate.get("detail_id") or "") or None,
                    candidate.get("detail_kegiatan"),
                    candidate.get("nomenklatur_path"),
                    "; ".join(candidate.get("iku_codes") or []),
                    score,
                    "keyword_nomenklatur_rule",
                    review_required,
                )
    context_match = _activity_context_fallback(row, candidates)
    if context_match.iku_codes:
        return context_match
    return _default_operational_suggestion(row, candidates)


def _activity_context_fallback(row: pd.Series, candidates: list[dict[str, object]]) -> NomenMatch:
    activity = str(row.get("kegiatan") or row.get("cluster_kegiatan") or "").lower()
    fallback_targets: list[tuple[str, str, float]] = [
        ("60.g", "praktik lapangan", 0.78),
        ("60.h", "kuliah tamu praktisi mengajar", 0.78),
        ("60.i", "fgd kurikulum", 0.74),
        ("60.j", "operasional perkantoran", 0.74),
    ]
    normalized_candidates = [
        (
            candidate,
            normalize_match_text(
                " ".join(
                    str(value)
                    for value in [
                        candidate.get("detail_kegiatan"),
                        candidate.get("sub_komponen_nomenklatur"),
                        candidate.get("nomenklatur_path"),
                    ]
                    if value
                )
            ),
        )
        for candidate in candidates
    ]
    for marker, target_text, score in fallback_targets:
        if marker not in activity:
            continue
        target_norm = normalize_match_text(target_text)
        for candidate, haystack in normalized_candidates:
            if target_norm and target_norm in haystack:
                return NomenMatch(
                    str(candidate.get("detail_id") or "") or None,
                    candidate.get("detail_kegiatan"),
                    candidate.get("nomenklatur_path"),
                    "; ".join(candidate.get("iku_codes") or []),
                    score,
                    "activity_context_suggestion",
                    True,
                )
    return NomenMatch(None, None, clean_display_text(row.get("nomenklatur_path")), None, 0.0, "not_matched")


def _default_operational_suggestion(row: pd.Series, candidates: list[dict[str, object]]) -> NomenMatch:
    if not candidates:
        return NomenMatch(None, None, clean_display_text(row.get("nomenklatur_path")), None, 0.0, "not_matched")
    target_norm = normalize_match_text("operasional perkantoran")
    for candidate in candidates:
        haystack = normalize_match_text(
            " ".join(
                str(value)
                for value in [
                    candidate.get("detail_kegiatan"),
                    candidate.get("sub_komponen_nomenklatur"),
                    candidate.get("nomenklatur_path"),
                ]
                if value
            )
        )
        if target_norm in haystack:
            return NomenMatch(
                str(candidate.get("detail_id") or "") or None,
                candidate.get("detail_kegiatan"),
                candidate.get("nomenklatur_path"),
                "; ".join(candidate.get("iku_codes") or []),
                0.60,
                "default_operational_suggestion",
                True,
            )
    return NomenMatch(None, None, clean_display_text(row.get("nomenklatur_path")), None, 0.0, "not_matched")


def _load_review_overrides() -> dict[str, dict[str, object]]:
    if not OVERRIDE_PATH.exists():
        return {}
    try:
        payload = json.loads(OVERRIDE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    overrides = payload.get("overrides", payload) if isinstance(payload, dict) else {}
    if not isinstance(overrides, dict):
        return {}
    return {str(key): value for key, value in overrides.items() if isinstance(value, dict)}


def clean_and_enrich_budget_items(items: pd.DataFrame, nomenklatur: pd.DataFrame, bridge: pd.DataFrame) -> pd.DataFrame:
    if items.empty:
        return items.copy()
    result = items.copy()
    candidates = _build_nomen_candidates(nomenklatur, bridge)
    overrides = _load_review_overrides()
    enriched_rows: list[dict[str, object]] = []
    for _, row in result.iterrows():
        code, name, account_label = clean_account_label(row)
        activity = clean_activity(row.get("kegiatan"), row.get("uraian_detail")) or "Perlu review kegiatan"
        cluster = clean_activity(row.get("cluster_kegiatan"), activity) or activity
        detail = clean_display_text(row.get("uraian_detail"))
        original_account_name = clean_account_name(row.get("nama_akun")) or clean_account_name(row.get("akun"))
        match = _best_nomen_match(row, candidates)
        override = overrides.get(str(row.get("item_id") or ""))
        if override and override.get("iku_codes"):
            match = NomenMatch(
                str(override.get("detail_id") or "") or None,
                clean_display_text(override.get("detail_kegiatan")) or clean_display_text(override.get("nama_iku")),
                clean_display_text(override.get("nomenklatur_path")) or clean_display_text(row.get("nomenklatur_path")),
                "; ".join(split_iku_codes(override.get("iku_codes"))) or str(override.get("iku_codes")),
                1.0,
                "manual_review_override",
                False,
            )
        iku_codes = match.iku_codes
        mapping_notes = []
        if match.method != "not_matched":
            mapping_notes.append(f"iku:{match.method}:{match.score:.2f}")
        if not code:
            mapping_notes.append("account:review")
        quality_flags = []
        existing_quality = str(row.get("data_quality_flag") or "")
        if existing_quality and existing_quality != "OK":
            quality_flags.extend(flag for flag in existing_quality.split(";") if flag)
        if not code and "MISSING_ACCOUNT" not in quality_flags:
            quality_flags.append("MISSING_ACCOUNT")
        if not iku_codes:
            quality_flags.append("IKU_REVIEW_REQUIRED")
        if activity == "Perlu review kegiatan":
            quality_flags.append("MISSING_ACTIVITY")
        public_flag = public_quality_flag(quality_flags, bool(code), bool(iku_codes))
        public_status = public_mapping_status(match, bool(code), override)
        clean_row = row.to_dict()
        clean_row.update(
            {
                "kegiatan": activity,
                "cluster_kegiatan": cluster,
                "akun": account_label,
                "kode_akun": code,
                "nama_akun": name,
                "nama_akun_asli": original_account_name,
                "iku": iku_codes,
                "kode_iku": iku_codes,
                "nama_iku": match.detail_kegiatan,
                "nomenklatur_detail_id": match.detail_id,
                "nomenklatur_path": match.nomenklatur_path or clean_display_text(row.get("nomenklatur_path")),
                "uraian_detail": detail,
                "mapping_status": public_status,
                "mapping_method": ";".join(mapping_notes) if mapping_notes else row.get("mapping_method"),
                "data_quality_flag": public_flag,
            }
        )
        enriched_rows.append(clean_row)
    return pd.DataFrame(enriched_rows)
