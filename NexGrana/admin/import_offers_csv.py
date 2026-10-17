"""Import authorized Mercado Livre CSV into draft Achados, via admin RLS.

Usage: python admin/import_offers_csv.py offers.csv --dry-run
       python admin/import_offers_csv.py offers.csv --commit
The Supabase URL/key and admin credentials come from environment variables.
No scrape, service-role key, or automatic publishing is used.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from cloud import DEFAULT_SUPABASE_KEY, DEFAULT_SUPABASE_URL
from services.admin_offers import build_offer_payload


def read_offers(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream)
        required={'title','url','category','expires_at'}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError('CSV precisa de title,url,category,expires_at')
        payloads=[]
        seen=set()
        for line,row in enumerate(reader,start=2):
            if not any(row.values()):continue
            try:
                # Imports are reviewed drafts. Publishing is a deliberate
                # per-item action in the authenticated admin panel.
                payload=build_offer_payload({**row,'enabled':False})
            except Exception as exc:
                raise ValueError(f'Linha {line}: {exc}') from exc
            if payload['url'] in seen:
                raise ValueError(f'Linha {line}: link duplicado neste arquivo')
            seen.add(payload['url'])
            payload['source']='owner_csv'
            payloads.append(payload)
        return payloads


def main(argv=None):
    parser=argparse.ArgumentParser(description='Validar/importar ofertas autorizadas em rascunho')
    parser.add_argument('csv_file')
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry-run',action='store_true')
    mode.add_argument('--commit',action='store_true')
    args=parser.parse_args(argv)
    rows=read_offers(args.csv_file)
    print(f'{len(rows)} oferta(s) válidas; todas em rascunho')
    for row in rows:print(f"- {row['title']} | {row['category']} | {row['expires_at']}")
    if args.dry_run:return 0
    from supabase import create_client
    email=os.getenv('NEXGRANA_ADMIN_EMAIL')
    password=os.getenv('NEXGRANA_ADMIN_PASSWORD')
    if not email or not password:raise ValueError('Configure NEXGRANA_ADMIN_EMAIL/PASSWORD no ambiente')
    client=create_client(os.getenv('NEXGRANA_SUPABASE_URL',DEFAULT_SUPABASE_URL),
                         os.getenv('NEXGRANA_SUPABASE_KEY',DEFAULT_SUPABASE_KEY))
    client.auth.sign_in_with_password({'email':email,'password':password})
    if client.rpc('is_app_admin').execute().data is not True:
        raise PermissionError('Conta não autorizada em app_admins')
    current=client.table('affiliate_offers').select('url').execute().data or []
    existing={row['url'] for row in current}
    created=0
    for row in rows:
        if row['url'] in existing:continue
        client.table('affiliate_offers').insert(row).execute()
        created+=1
    print(f'{created} novo(s) rascunho(s). Revise e publique no painel.')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
