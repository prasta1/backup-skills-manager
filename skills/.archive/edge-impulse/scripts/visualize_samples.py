#!/usr/bin/env python3
"""
Edge Impulse Data Visualization Script

This script fetches samples from an Edge Impulse project and creates visualizations
of the sensor data. To use this script, you need to:
1. Set your Edge Impulse API key as EI_API_KEY environment variable
2. Set your project ID as EI_PROJECT_ID environment variable
3. Install required packages: pip install requests matplotlib

Usage:
    export EI_API_KEY=***    export EI_PROJECT_ID="your_project_id"
    python3 visualize_samples.py
"""

import os
import requests
import base64
import csv
import io
import matplotlib.pyplot as plt
import sys

def main():
    # Get credentials from environment
    EI_API_KEY=os.environ.get('EI_API_KEY')
    EI_PROJECT_ID = os.environ.get('EI_PROJECT_ID')
    
    if not EI_API_KEY or not EI_PROJECT_ID:
        print("Error: Please set EI_API_KEY and EI_PROJECT_ID environment variables")
        print("Get your API key from: https://studio.edgeimpulse.com -> your project -> Keys")
        print("Get your project ID from: https://studio.edgeimpulse.com -> your project -> Project Info")
        sys.exit(1)
    
    headers = {'x-api-key': EI_API_KEY}
    base_url = f'https://studio.edgeimpulse.com/v1/api/{EI_PROJECT_ID}'
    
    # Get project info to verify
    print("Fetching project info...")
    resp = requests.get(base_url, headers=headers)
    if resp.status_code != 200:
        print(f"Failed to get project info: {resp.status_code} {resp.text}")
        print("Check your API key and project ID")
        sys.exit(1)
    
    project_info = resp.json()
    if not project_info.get('success'):
        print(f"API error: {project_info}")
        sys.exit(1)
    
    project_name = project_info.get('result', {}).get('name', 'Unknown Project')
    print(f"Project: {project_name}")
    
    # Get a few samples
    print("\nFetching samples (limit=10)...")
    params = {'limit': 10, 'category': 'training'}  # Get training data
    resp = requests.get(f'{base_url}/raw-data', headers=headers, params=params)
    
    if resp.status_code != 200:
        print(f"Failed to get samples: {resp.status_code} {resp.text}")
        sys.exit(1)
    
    samples_resp = resp.json()
    if not samples_resp.get('success'):
        print(f"API error: {samples_resp.get('error', 'Unknown error')}")
        sys.exit(1)
    
    samples = samples_resp.get('result', [])
    if not samples:
        print("No samples found in the project")
        sys.exit(0)
    
    print(f"Found {len(samples)} samples")
    
    # Process samples for visualization
    samples_to_plot = []
    max_samples_to_plot = min(3, len(samples))  # Plot up to 3 samples
    
    for i, sample in enumerate(samples[:max_samples_to_plot]):
        sample_id = sample.get('sampleId') or sample.get('_id') or sample.get('id')
        sample_label = sample.get('label', '(no label)')
        sample_category = sample.get('category', 'unknown')
        print(f"\nProcessing sample {i+1}/{max_samples_to_plot}: {sample_id} (label: {sample_label}, category: {sample_category})")
        
        # Fetch the raw data for this sample
        sample_resp = requests.get(f'{base_url}/raw-data/{sample_id}', headers=headers)
        if sample_resp.status_code != 200:
            print(f"  Failed to fetch sample data: {sample_resp.status_code} {sample_resp.text}")
            continue
        
        sample_data = sample_resp.json()
        if not sample_data.get('success'):
            print(f"  API error: {sample_data.get('error', 'Unknown error')}")
            continue
        
        result = sample_data.get('result', {})
        file_b64 = result.get('file')
        if not file_b64:
            print("  No file data in sample")
            continue
        
        try:
            csv_bytes = base64.b64decode(file_b64)
            csv_text = csv_bytes.decode('utf-8')
        except Exception as e:
            print(f"  Failed to decode CSV: {e}")
            continue
        
        # Parse CSV
        f = io.StringIO(csv_text)
        reader = csv.DictReader(f)
        rows = list(reader)
        if not rows:
            print("  CSV has no rows")
            continue
        
        print(f"  CSV has {len(rows)} rows, columns: {reader.fieldnames}")
        
        # Determine which columns to plot: we want the sensor columns
        expected_cols = ['ax', 'ay', 'az', 'gx', 'gy', 'gz']
        available_cols = [col for col in expected_cols if col in reader.fieldnames]
        
        if not available_cols:
            print("  No standard sensor columns found (ax, ay, az, gx, gy, gz)")
            # Try to find any numeric columns
            for col in reader.fieldnames:
                if col not in ['label', 'timestamp']:
                    try:
                        float(rows[0][col])
                        available_cols.append(col)
                    except:
                        pass
        
        if not available_cols:
            print("  No numeric columns found to plot")
            continue
        
        # Prepare data for plotting
        x = list(range(len(rows)))  # sample index
        data = {}
        for col in available_cols:
            try:
                data[col] = [float(row[col]) for row in rows]
            except (ValueError, KeyError) as e:
                print(f"  Warning: Could not process column {col}: {e}")
                continue
        
        if not data:
            print("  No valid numeric data to plot")
            continue
        
        samples_to_plot.append({
            'id': sample_id,
            'label': sample_label,
            'category': sample_category,
            'x': x,
            'data': data,
            'columns': list(data.keys())
        })
    
    if not samples_to_plot:
        print("No samples could be processed for plotting")
        sys.exit(0)
    
    # Create plots
    print(f"\nCreating visualizations for {len(samples_to_plot)} sample(s)...")
    
    for sample in samples_to_plot:
        plt.figure(figsize=(12, 8))
        
        # Separate accelerometer and gyroscope data if available
        acc_cols = [c for c in sample['columns'] if c in ['ax', 'ay', 'az']]
        gyro_cols = [c for c in sample['columns'] if c in ['gx', 'gy', 'gz']]
        other_cols = [c for c in sample['columns'] if c not in ['ax', 'ay', 'az', 'gx', 'gy', 'gz']]
        
        if acc_cols and gyro_cols:
            # Two subplots: accelerometer and gyroscope
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
            
            for col in acc_cols:
                ax1.plot(sample['x'], sample['data'][col], label=col, linewidth=1)
            ax1.set_ylabel('Acceleration (m/s²)', fontsize=10)
            ax1.set_title(f"Sample {sample['id']} - Accelerometer\nLabel: {sample['label']} | Category: {sample['category']}", fontsize=12)
            ax1.legend(loc='upper right', fontsize=9)
            ax1.grid(True, alpha=0.3)
            
            for col in gyro_cols:
                ax2.plot(sample['x'], sample['data'][col], label=col, linewidth=1)
            ax2.set_ylabel('Angular Velocity (°/s)', fontsize=10)
            ax2.set_xlabel('Sample Index', fontsize=10)
            ax2.set_title(f"Sample {sample['id']} - Gyroscope", fontsize=12)
            ax2.legend(loc='upper right', fontsize=9)
            ax2.grid(True, alpha=0.3)
            
        else:
            # Single plot for all available columns
            for col in sample['columns']:
                plt.plot(sample['x'], sample['data'][col], label=col, linewidth=1)
            plt.xlabel('Sample Index', fontsize=10)
            plt.ylabel('Value', fontsize=10)
            plt.title(f"Sample {sample['id']}\nLabel: {sample['label']} | Category: {sample['category']}", fontsize=12)
            plt.legend(loc='upper right', fontsize=9)
            plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        filename = f'/tmp/ei_sample_{sample["id"]}.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  Saved: {filename}")
        print(f"  MEDIA:{filename}")

if __name__ == '__main__':
    main()