#!/usr/bin/env python3
"""
Verify VAE files for Wan 2.2 t2v compatibility.

Usage:
    python3 verify-vaes.py <path-to-vaefile>
"""
import sys
import torch

if len(sys.argv) != 2:
    print("Usage: python3 verify-vaes.py <path-to-vaefile>")
    sys.exit(1)

vaefile = sys.argv[1]

try:
    print(f"Verifying {vaefile}...")
    state_dict = torch.load(vaefile, map_location='cpu')
    
    # Check conv2.bias shape
    if 'conv2.bias' in state_dict:
        shape = state_dict['conv2.bias'].shape
        if shape[0] == 16:
            print(f"✓ Correct: {vaefile} has 16-channel VAE")
        else:
            print(f"✗ Wrong: {vaefile} has {shape[0]}-channel VAE (expected 16)")
    else:
        print(f"✗ Missing: {vaefile} has no 'conv2.bias' key")
    
except Exception as e:
    print(f"Error loading {vaefile}: {e}")
    sys.exit(1)

sys.exit(0)