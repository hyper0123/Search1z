#!/usr/bin/env python3
import os
import argparse
import requests
import base64
from urllib.parse import quote_plus

# --- CREDENCIALES ---
ZOOMEYE_API_KEY = os.environ.get('ZOOMEYE_API_KEY')
ZOOMEYE_USERNAME = os.environ.get('ZOOMEYE_USERNAME')
ZOOMEYE_PASSWORD = os.environ.get('ZOOMEYE_PASSWORD')
FOFA_EMAIL = os.environ.get('FOFA_EMAIL')
FOFA_KEY = os.environ.get('FOFA_KEY')

# Parámetros de búsqueda\QUERY = 'Astra Control Panel'
ZOOMEYE_PAGES = 3


def get_zoomeye_headers():
    if ZOOMEYE_API_KEY:
        print('[DEBUG] Usando API-KEY de ZoomEye')
        return {'API-KEY': ZOOMEYE_API_KEY}

    # Flujo JWT si no hay APIKEY
    response = requests.post(
        'https://api.zoomeye.org/user/login',
        json={
            'username': ZOOMEYE_USERNAME,
            'password': ZOOMEYE_PASSWORD
        }
    )
    print(f"[DEBUG] Login JWT status: {response.status_code}")
    response.raise_for_status()
    token = response.json().get('access_token')
    return {'Authorization': f'JWT {token}'}


def fetch_zoomeye_hosts(country: str):
    headers = get_zoomeye_headers()
    hosts = []
    query_str = f'app:"{QUERY}" country:{country}'

    for page in range(1, ZOOMEYE_PAGES + 1):
        params = {'query': query_str, 'page': page}
        r = requests.get(
            'https://api.zoomeye.org/host/search',
            headers=headers,
            params=params
        )
        if r.status_code != 200:
            print(f'[!] ZoomEye HTTP {r.status_code} on page {page}')
            break

        data = r.json()
        for m in data.get('matches', []):
            ip = m.get('ip')
            port = m.get('portinfo', {}).get('port')
            if ip and port:
                hosts.append(f'http://{ip}:{port}/playlist.m3u')

    print(f'[+] ZoomEye found {len(hosts)} URLs')
    return hosts


def fetch_fofa_hosts(country: str):
    raw_q = f'{QUERY} && country="{country}"'
    b64 = base64.b64encode(raw_q.encode()).decode()
    params = {
        'email': FOFA_EMAIL,
        'key': FOFA_KEY,
        'qbase64': b64,
        'page': 1,
        'size': 100
    }
    r = requests.get('https://fofa.info/api/v1/search/all', params=params)
    r.raise_for_status()
    results = r.json().get('results', [])

    hosts = []
    for ip, port in results:
        if ip and port:
            hosts.append(f'http://{ip}:{port}/playlist.m3u')

    print(f'[+] FOFA found {len(hosts)} URLs')
    return hosts


def list_hosts(country: str, source: str):
    if source == 'zoomeye':
        hosts = fetch_zoomeye_hosts(country)
    else:
        hosts = fetch_fofa_hosts(country)

    out_dir = f'lists/{source}'
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f'hosts_{country}.txt')

    with open(path, 'w', encoding='utf-8') as f:
        f.write("\n".join(hosts))

    print(f'[+] Lista de {len(hosts)} URLs guardada en {path}')


def download_playlists(country: str, source: str):
    in_path = os.path.join('lists', source, f'hosts_{country}.txt')
    if not os.path.isfile(in_path):
        print(f'Error: {in_path} no existe')
        return

    with open(in_path, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]

    out_dir = f'downloads/{source}'
    os.makedirs(out_dir, exist_ok=True)

    for idx, url in enumerate(urls, start=1):
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200 and r.text.strip():
                fname = f'{idx}_{country}.m3u'
                with open(os.path.join(out_dir, fname), 'w', encoding='utf-8'):
                    f.write(r.text)
                print(f'[+] Descargado y guardado {fname}')
            else:
                print(f'[-] Falló {url} (status {r.status_code})')
        except Exception as e:
            print(f'[-] Error descargando {url}: {e}')


def main():
    parser = argparse.ArgumentParser(description='Lista y descarga playlists M3U')
    parser.add_argument('--country', required=True, help='Código de país, ej. AR')
    parser.add_argument(
        '--action',
        choices=['list', 'download'],
        required=True,
        help='"list": generar lista de URLs; "download": bajar playlists'
    )
    parser.add_argument(
        '--source',
        choices=['zoomeye', 'fofa'],
        required=True,
        help='Fuente: zoomeye o fofa'
    )
    args = parser.parse_args()

    country = args.country.upper()
    if args.action == 'list':
        list_hosts(country, args.source)
    else:
        download_playlists(country, args.source)

if __name__ == '__main__':
    main()

