"""Utilidades para normalizar matrículas y resolver profesionales."""

from typing import Optional

from sqlalchemy import func

from utils.membership_sheet_parser import normalize_text, MONTH_NAMES_PATTERN


def normalize_tuition(raw) -> Optional[str]:
    """
    Convierte una matrícula cruda del Excel a formato canónico (solo dígitos).
    Retorna None si el valor no parece una matrícula válida.
    """
    if raw is None:
        return None

    raw_str = str(raw).strip()
    if not raw_str:
        return None

    text_norm = normalize_text(raw_str)

    if MONTH_NAMES_PATTERN.search(text_norm):
        return None

    if 'al dia' in text_norm:
        return None

    digits = ''.join(ch for ch in raw_str if ch.isdigit())
    if len(digits) < 3 or len(digits) > 6:
        return None

    return digits


def tuition_display_from_raw(raw) -> Optional[str]:
    if raw is None:
        return None
    raw_str = str(raw).strip()
    return raw_str if raw_str else None


def find_professional_by_tuition(tuition_normalized: str):
    """Busca un profesional por matrícula normalizada."""
    from models import ProfessionalModel

    if not tuition_normalized:
        return None

    return ProfessionalModel.query.filter(
        func.replace(func.replace(ProfessionalModel.tuition, ' ', ''), '.', '') == tuition_normalized,
        ProfessionalModel.deleted_at == None,
    ).first()


def link_membership_status_uuids(status_record, tuition_normalized: str):
    """Vincula lawyer_membership_status con professionals/users por UUID."""
    professional = find_professional_by_tuition(tuition_normalized)
    if professional:
        status_record.uuid_professional = professional.uuid
        status_record.uuid_user = professional.uuid_user
    return status_record
