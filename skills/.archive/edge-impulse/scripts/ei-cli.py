#!/usr/bin/env python3
"""
ei-cli: A programmatic CLI alternative to Edge Impulse Studio web UI.
Provides convenient commands for project management, data upload, and visualization.
"""

import argparse
import json
import os
import sys
import time
import base64
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: requests not installed. Run: pip install requests")
    sys.exit(1)

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

API_BASE = "https://studio.edgeimpulse.com/v1"
INGESTION_BASE = "https://ingestion.edgeimpulse.com"
CONFIG_FILE = Path.home() / '.config' / 'ei-cli' / 'config.json'


def load_config():
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def save_config(config):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def get_api_key():
    return load_config().get('api_key') or os.environ.get('EI_API_KEY')


def api_get(endpoint, api_key):
    response = requests.get(f"{API_BASE}{endpoint}", headers={'x-api-key': api_key})
    response.raise_for_status()
    return response.json()


def api_post(endpoint, api_key, json_data=None):
    response = requests.post(f"{API_BASE}{endpoint}",
                             headers={'x-api-key': api_key, 'content-type': 'application/json'},
                             json=json_data)
    if response.status_code >= 400:
        raise Exception(f"API error {response.status_code}: {response.text[:300]}")
    return response.json()


def cmd_login(args):
    config = load_config()
    config['api_key'] = args.api_key
    save_config(config)
    print(f"✓ API key saved")


def cmd_projects(args):
    api_key = get_api_key()
    user = api_get('/api/user', api_key)
    projects = user.get('projects', [])
    for p in projects:
        print(f"{p['id']:<12} {p['name'][:35]:<35} {p.get('project_type', 'N/A'):<20}")


def cmd_samples(args):
    api_key = get_api_key()
    project_id = args.project or load_config().get('default_project')
    
    if args.action == 'list':
        query = f"?limit={args.limit or 50}"
        if args.category:
            query += f"&category={args.category}"
        if args.label:
            query += f"&label={args.label}"
        response = api_get(f'/api/{project_id}/raw-data{query}', api_key)
        samples = response.get('samples', [])
        for s in samples:
            print(f"{s['id']:<12} {s.get('label', 'N/A')[:20]:<20} {s.get('category', 'N/A'):<12}")
    
    elif args.action == 'visualize':
        if not plt:
            print("Error: matplotlib not installed. Run: pip install matplotlib")
            return
        sample_id = args.sample_id
        sample = api_get(f'/api/{project_id}/raw-data/{sample_id}', api_key)
        if not sample.get('file'):
            print("Error: No file data in sample")
            return
        csv_data = base64.b64decode(sample['file']).decode('utf-8')
        lines = csv_data.strip().split('\n')
        headers = lines[0].split(',')
        fig, axes = plt.subplots(len(headers)-1, 1, figsize=(10, 4*len(headers)), sharex=True)
        if len(headers) == 2:
            axes = [axes]
        for i, header in enumerate(headers[1:]):
            values = [float(line.split(',')[i+1]) for line in lines[1:] if line]
            axes[i].plot(values, linewidth=0.5)
            axes[i].set_ylabel(header)
        axes[-1].set_xlabel('Sample Index')
        out_path = Path(args.output or f'sample_{sample_id}.png')
        plt.tight_layout()
        plt.savefig(out_path, dpi=100)
        print(f"✓ Saved: {out_path}")


def cmd_data(args):
    api_key = get_api_key()
    project_id = args.project or load_config().get('default_project')
    file_path = Path(args.file)
    print(f"Uploading {file_path.name}...")
    with open(file_path, 'rb') as f:
        response = requests.post(f"{INGESTION_BASE}/api/training/files",
                                 headers={'x-api-key': api_key},
                                 files={'file': (file_path.name, f)})
    if response.ok:
        print("✓ Upload successful")
    else:
        print(f"✗ Upload failed: {response.status_code}")


def cmd_jobs(args):
    api_key = get_api_key()
    job_id = args.job_id.lstrip('job-')
    if args.watch:
        print(f"Watching job {job_id}...")
        while True:
            response = api_get(f'/api/jobs/{job_id}/status', api_key)
            status = response.get('status', 'unknown')
            print(f"\r[{time.strftime('%H:%M:%S')}] {status}", end='', flush=True)
            if status.lower() in ['finished', 'failed', 'completed']:
                print(f"\n✓ Job {status}")
                break
            time.sleep(3)
    else:
        response = api_get(f'/api/jobs/{job_id}/status', api_key)
        print(f"Job {job_id}: {response.get('status', 'unknown')}")


def cmd_config(args):
    config = load_config()
    config['default_project'] = args.project_id
    save_config(config)
    print(f"✓ Default project: {args.project_id}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ei-cli: Edge Impulse Studio CLI')
    subparsers = parser.add_subparsers(dest='command')
    
    login_sp = subparsers.add_parser('login')
    login_sp.add_argument('--api-key', required=True)
    
    proj_sp = subparsers.add_parser('projects')
    proj_sp.add_argument('action', choices=['list'])
    
    samples_sp = subparsers.add_parser('samples')
    samples_sp.add_argument('action', choices=['list', 'visualize'])
    samples_sp.add_argument('--project')
    samples_sp.add_argument('--category')
    samples_sp.add_argument('--label')
    samples_sp.add_argument('--limit', type=int)
    samples_sp.add_argument('--sample-id')
    samples_sp.add_argument('--output', '-o')
    
    data_sp = subparsers.add_parser('data')
    data_sp.add_argument('action', choices=['upload'])
    data_sp.add_argument('file')
    data_sp.add_argument('--project')
    
    jobs_sp = subparsers.add_parser('jobs')
    jobs_sp.add_argument('job_id')
    jobs_sp.add_argument('--watch', '-w', action='store_true')
    
    cfg_sp = subparsers.add_parser('config')
    cfg_sp.add_argument('action', choices=['set-default'])
    cfg_sp.add_argument('project_id')
    
    args = parser.parse_args()
    
    if args.command == 'login': cmd_login(args)
    elif args.command == 'projects': cmd_projects(args)
    elif args.command == 'samples': cmd_samples(args)
    elif args.command == 'data': cmd_data(args)
    elif args.command == 'jobs': cmd_jobs(args)
    elif args.command == 'config': cmd_config(args)