#!/usr/bin/env python3
import os
import argparse
import requests
from urllib.parse import quote_plus
from collections import defaultdict

# --- CREDENCIALES ---
# ZoomEye: APIKEY ó USER/PASS (para JWT)
ZOOMEYE_API_KEY  = os.environ.get('ZOOMEYE_API_KEY')
ZOOMEYE_USERNAME = os.environ.get('ZOOMEYE_USERNAME')
ZOOMEYE_PASSWORD = os.environ.get('ZOOMEYE_PASSWORD')
# FOFA: EMAIL + KEY
FOFA_EMAIL = os.environ.get('FOFA_EMAIL')
FOFA_KEY   = os.environ.get('FOFA_KEY')

# Parámetros de búsqueda
QUERY = 'Astra Control Panel'
# Número de páginas a escanear en ZoomEye
ZOOMEYE_PAGES = 3
# FOFA retorna hasta 100 por page
def search_zoomeye(country: str, pages: int = ZOOMEYE_PAGES):
    """Retorna lista de "ip:port" de ZoomEye filtrado por país."""
    # Construimos headers
    if ZOOMEYE_API_KEY:
        headers = {'API-KEY': ZOOMEYE_API_KEY}
    else:
        # obtén JWT
        login = requests.post(
            'https://api.zoomeye.org/user/login',
            json={'username': ZOOMEYE_USERNAME, 'password': ZOOMEYE_PASSWORD}
        )
        login.raise_for_status()
        token = login.json()['access_token']
        headers = {'Authorization': f'JWT {token}'}

    hosts = []
    for page in range(1, pages + 1):
        params = {'query': f'{QUERY} country:{country}', 'page': page}
        resp = requests.get('https://api.zoomeye.org/host/search', headers=headers, params=params)
        if resp.status_code != 200:
            break
        data = resp.json()
        for item in data.get('matches', []):
            ip = item.get('ip')
            port = item.get('portinfo', {}).get('port')
            if ip and port:
                hosts.append(f'{ip}:{port}')
    return hosts


def search_fofa(country: str):
    """Retorna lista de "ip:port" de FOFA filtrado por país."""
    qbase = quote_plus(f'{QUERY} && country="{country}"')
    url = 'https://fofa.info/api/v1/search/all'
    params = {
        'email': FOFA_EMAIL,
        'key': FOFA_KEY,
        'qbase64': qbase,
        'page': 1,
        'size': 100
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    results = resp.json().get('results', [])
    return [f"{r[0]}:{r[1]}" for r in results if r[0] and r[1]]


def fetch_and_save(hosts: list, country: str, source: str):
    """Descarga playlist y guarda archivos numerados."""
    out_dir = f'playlists/{source}'
    os.makedirs(out_dir, exist_ok=True)
    count = 0
    for host in hosts:
        count += 1
        url = f'http://{host}/playlist.m3u'
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200 and r.text.strip():
                fname = f'{count}_{country}.m3u'
                path = os.path.join(out_dir, fname)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(r.text)
                print(f'[+] {source}: Guardado {fname}')
            else:
                print(f'[-] {source}: No válido {host} (status {r.status_code})')
        except Exception as e:
            print(f'[-] {source}: Error {host}: {e}')


def main():
    parser = argparse.ArgumentParser(description='Escanea y descarga playlists M3U')
    parser.add_argument('--country', required=True, help='Código de país (ej. AR, PE)')
    parser.add_argument('--source', choices=['zoomeye', 'fofa', 'both'], default='both')
    args = parser.parse_args()

    country = args.country.upper()
    if args.source in ['zoomeye', 'both']:
        zy_hosts = search_zoomeye(country)
        fetch_and_save(zy_hosts, country, 'zoomeye')
    if args.source in ['fofa', 'both']:
        fofa_hosts = search_fofa(country)
        fetch_and_save(fofa_hosts, country, 'fofa')

if __name__ == '__main__':
    main()

