"""Tests del parser de cuotas del Excel de secretaría."""

import unittest
from datetime import date

from utils.membership_sheet_parser import parse_quota_adeudada, normalize_text
from utils.tuition_utils import normalize_tuition
from models.membership_constants import (
    MEMBERSHIP_STATUS_UP_TO_DATE,
    MEMBERSHIP_STATUS_IN_DEBT,
    MEMBERSHIP_STATUS_EXEMPT_AL_DIA,
    MEMBERSHIP_STATUS_BLOCKED,
    MEMBERSHIP_STATUS_AMBIGUOUS,
)

REFERENCE = date(2026, 6, 22)


class TestMembershipSheetParser(unittest.TestCase):
    def test_debt_current_month_behind(self):
        result = parse_quota_adeudada('Abril 2026', reference_date=REFERENCE)
        self.assertEqual(result['status'], MEMBERSHIP_STATUS_IN_DEBT)
        self.assertEqual(result['first_unpaid_month'], date(2026, 4, 1))

    def test_up_to_date_future_month(self):
        result = parse_quota_adeudada('Julio 2026', reference_date=REFERENCE)
        self.assertEqual(result['status'], MEMBERSHIP_STATUS_UP_TO_DATE)
        self.assertEqual(result['first_unpaid_month'], date(2026, 7, 1))

    def test_up_to_date_far_future(self):
        result = parse_quota_adeudada('Enero 2027', reference_date=REFERENCE)
        self.assertEqual(result['status'], MEMBERSHIP_STATUS_UP_TO_DATE)

    def test_explicit_al_dia_with_old_month(self):
        result = parse_quota_adeudada(
            'agosto 2017 (al día- suspensión matrícula)',
            reference_date=REFERENCE,
        )
        self.assertEqual(result['status'], MEMBERSHIP_STATUS_EXEMPT_AL_DIA)

    def test_explicit_al_dia_hyphen(self):
        result = parse_quota_adeudada('noviembre 2010-al día', reference_date=REFERENCE)
        self.assertEqual(result['status'], MEMBERSHIP_STATUS_EXEMPT_AL_DIA)

    def test_explicit_al_dia_two_digit_year(self):
        result = parse_quota_adeudada('mayo 09-al día', reference_date=REFERENCE)
        self.assertEqual(result['status'], MEMBERSHIP_STATUS_EXEMPT_AL_DIA)

    def test_deceased_blocked(self):
        result = parse_quota_adeudada('agosto 2013 (fallecido)', reference_date=REFERENCE)
        self.assertEqual(result['status'], MEMBERSHIP_STATUS_BLOCKED)
        self.assertEqual(result['blocked_reason'], 'deceased')

    def test_uppercase_month(self):
        result = parse_quota_adeudada('JULIO 2026', reference_date=REFERENCE)
        self.assertEqual(result['status'], MEMBERSHIP_STATUS_UP_TO_DATE)

    def test_march_2026_with_al_dia_note(self):
        result = parse_quota_adeudada(
            'Marzo 2026(al día - susp- mat- incompatibilidad)',
            reference_date=REFERENCE,
        )
        self.assertEqual(result['status'], MEMBERSHIP_STATUS_EXEMPT_AL_DIA)

    def test_empty_ambiguous(self):
        result = parse_quota_adeudada('', reference_date=REFERENCE)
        self.assertEqual(result['status'], MEMBERSHIP_STATUS_AMBIGUOUS)

    def test_no_year_ambiguous(self):
        result = parse_quota_adeudada('marzo', reference_date=REFERENCE)
        self.assertEqual(result['status'], MEMBERSHIP_STATUS_AMBIGUOUS)

    def test_old_debt(self):
        result = parse_quota_adeudada('noviembre 2009', reference_date=REFERENCE)
        self.assertEqual(result['status'], MEMBERSHIP_STATUS_IN_DEBT)


class TestTuitionNormalization(unittest.TestCase):
    def test_with_dots(self):
        self.assertEqual(normalize_tuition('12.946'), '12946')

    def test_plain_number(self):
        self.assertEqual(normalize_tuition('7741'), '7741')

    def test_month_in_mat_rejected(self):
        self.assertIsNone(normalize_tuition('marzo 1994'))

    def test_al_dia_in_mat_rejected(self):
        self.assertIsNone(normalize_tuition('mayo 2010- al día'))

    def test_empty_rejected(self):
        self.assertIsNone(normalize_tuition(''))


if __name__ == '__main__':
    unittest.main()
