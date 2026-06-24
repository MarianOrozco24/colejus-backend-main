import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from utils.membership_sheet_parser import parse_quota_adeudada, normalize_text

URL = (
    'https://docs.google.com/spreadsheets/d/'
    '1Gwwy0nOJ5dDpOkUJH7Urig4j7LtHT-34L76B8B-ZXr4/export'
    '?format=csv&gid=191760753'
)

r = requests.get(URL, timeout=30)
print('HTTP status:', r.status_code)
print('bytes:', len(r.content))

for enc in ['utf-8', 'latin-1']:
    text = r.content.decode(enc)
    lines = text.splitlines()
    print(f'\n=== encoding: {enc} ===')
    print('total lines:', len(lines))
    sample = next((l for l in lines if '7741' in l), '')
    print('sample row:', sample[:120])
    if 'agosto 2017' in sample:
        part = sample.split('agosto 2017')[1][:40]
        print('after agosto 2017:', part)
        cuota = 'agosto 2017' + sample.split('agosto 2017')[1].split(',')[0]
        print('cuota field approx:', cuota)
        print('normalized:', normalize_text(cuota))
        print('parsed status:', parse_quota_adeudada(cuota)['status'])
