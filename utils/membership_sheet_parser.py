"""
Parser de la columna CUOTA ADEUDADA del Excel de secretaría.

Reglas de negocio:
- El mes indicado es el PRIMER mes adeudado; meses anteriores están pagos.
- Si el texto contiene "al día" / "al dia", el profesional está al día (EXEMPT_AL_DIA).
- Si contiene marcadores de fallecimiento, queda BLOCKED.
- Si no se puede interpretar con confianza, queda AMBIGUOUS.
"""

import re
import unicodedata
from datetime import date
from typing import List, Optional

from models.membership_constants import (
    MEMBERSHIP_STATUS_UP_TO_DATE,
    MEMBERSHIP_STATUS_IN_DEBT,
    MEMBERSHIP_STATUS_EXEMPT_AL_DIA,
    MEMBERSHIP_STATUS_BLOCKED,
    MEMBERSHIP_STATUS_AMBIGUOUS,
)

MONTH_MAP = {
    'enero': 1, 'ene': 1,
    'febrero': 2, 'feb': 2,
    'marzo': 3, 'mar': 3,
    'abril': 4, 'abr': 4,
    'mayo': 5, 'may': 5,
    'junio': 6, 'jun': 6,
    'julio': 7, 'jul': 7,
    'agosto': 8, 'ago': 8,
    'septiembre': 9, 'setiembre': 9, 'sept': 9, 'sep': 9,
    'octubre': 10, 'oct': 10,
    'noviembre': 11, 'nov': 11,
    'diciembre': 12, 'dic': 12,
}

_MONTH_PATTERN_PART = '|'.join(sorted(MONTH_MAP.keys(), key=len, reverse=True))
MONTH_NAMES_PATTERN = re.compile(rf'\b({_MONTH_PATTERN_PART})\b', re.IGNORECASE)
MONTH_YEAR_PATTERN = re.compile(
    rf'\b({_MONTH_PATTERN_PART})\b\s*[\s\-\(/\.]*(\d{{2,4}})',
    re.IGNORECASE,
)


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize('NFD', value)
    return ''.join(ch for ch in normalized if unicodedata.category(ch) != 'Mn')


def normalize_text(value) -> str:
    if value is None:
        return ''
    text = strip_accents(str(value).lower().strip())
    text = text.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
    text = re.sub(r'\s+', ' ', text)
    return text


def parse_year(year_str: str) -> int:
    year = int(year_str)
    if year < 100:
        return 2000 + year if year <= 30 else 1900 + year
    return year


def extract_month_year_pairs(text_normalized: str) -> List[date]:
    pairs: List[date] = []
    for match in MONTH_YEAR_PATTERN.finditer(text_normalized):
        month_key = match.group(1).lower()
        month_num = MONTH_MAP.get(month_key)
        if not month_num:
            continue
        year = parse_year(match.group(2))
        pairs.append(date(year, month_num, 1))
    return pairs


def parse_quota_adeudada(raw_text, reference_date: Optional[date] = None) -> dict:
    """
    Interpreta el texto crudo de CUOTA ADEUDADA y devuelve estado normalizado.
    """
    reference_date = reference_date or date.today()
    current_month_start = date(reference_date.year, reference_date.month, 1)

    if raw_text is None or not str(raw_text).strip():
        return {
            'status': MEMBERSHIP_STATUS_AMBIGUOUS,
            'first_unpaid_month': None,
            'blocked_reason': None,
            'parse_notes': 'empty_quota_field',
        }

    text = normalize_text(raw_text)

    if re.search(r'fallecid', text):
        return {
            'status': MEMBERSHIP_STATUS_BLOCKED,
            'first_unpaid_month': None,
            'blocked_reason': 'deceased',
            'parse_notes': 'deceased_marker',
        }

    if 'al dia' in text:
        return {
            'status': MEMBERSHIP_STATUS_EXEMPT_AL_DIA,
            'first_unpaid_month': None,
            'blocked_reason': None,
            'parse_notes': 'explicit_al_dia',
        }

    month_years = extract_month_year_pairs(text)
    if not month_years:
        return {
            'status': MEMBERSHIP_STATUS_AMBIGUOUS,
            'first_unpaid_month': None,
            'blocked_reason': None,
            'parse_notes': 'no_month_year_found',
        }

    first_unpaid_month = month_years[0]

    if first_unpaid_month > current_month_start:
        status = MEMBERSHIP_STATUS_UP_TO_DATE
    else:
        status = MEMBERSHIP_STATUS_IN_DEBT

    return {
        'status': status,
        'first_unpaid_month': first_unpaid_month,
        'blocked_reason': None,
        'parse_notes': f'first_debt_month_{first_unpaid_month.isoformat()}',
    }


def detect_column_map(header_row: List[str]) -> dict:
    """Detecta índices de columnas por encabezado."""
    column_map = {}
    for idx, cell in enumerate(header_row):
        norm = normalize_text(cell)
        if not norm:
            continue
        if norm == 'mat':
            column_map['mat'] = idx
        elif 'cuota' in norm and 'adeudada' in norm:
            column_map['cuota'] = idx
        elif norm == 'apellido':
            column_map['apellido'] = idx
        elif norm == 'nombre':
            column_map['nombre'] = idx
        elif 'observacion' in norm:
            column_map['observacion'] = idx
        elif norm.isdigit() and 'index' not in column_map:
            column_map['index'] = idx

    if 'mat' in column_map and 'cuota' in column_map:
        cuota_idx = column_map['cuota']
        if 'sede' not in column_map and cuota_idx + 1 < len(header_row):
            column_map['sede'] = cuota_idx + 1
        if 'observacion' not in column_map and cuota_idx + 2 < len(header_row):
            column_map['observacion'] = cuota_idx + 2

    return column_map


def find_header_row(rows: List[List[str]]) -> tuple:
    """Busca la fila de encabezado que contiene MAT y CUOTA ADEUDADA."""
    for row_idx, row in enumerate(rows):
        column_map = detect_column_map(row)
        if 'mat' in column_map and 'cuota' in column_map:
            return row_idx, column_map
    return -1, {}


def get_row_cell(row: List[str], key: str, column_map: dict, default=None):
    idx = column_map.get(key)
    if idx is None or idx >= len(row):
        return default
    value = row[idx]
    if value is None:
        return default
    value = str(value).strip()
    return value if value else default


def title_case_name(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return ' '.join(part.capitalize() for part in value.strip().split())
