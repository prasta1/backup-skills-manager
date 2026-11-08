# Wan 2.2 VAE Trap

## The Problem

The Wan 2.2 t2v model produces 16-channel latents, but the `wan2.2_vae.safetensors` file is a 48-channel-latent VAE and fails at VAEDecode with:

```
expected input[1, 16, ...] to have 48 channels, but got 16
```

The official blueprint pairs Wan 2.2 with the 16-channel `wan_2.1_vae.safetensors` (242 MB, from `Comfy-Org/Wan_2.2_ComfyUI_Repackaged/split_files/vae/`).

## The Solution

Use `wan_2.1_vae.safetensors` (16-channel) not `wan2.2_vae.safetensors` (48-channel).

## How to Verify

1. Download the VAE file
2. Check the safetensors header:
   ```python
   import torch
   state_dict = torch.load("wan_2.1_vae.safetensors", map_location='cpu')
   print(state_dict["conv2.bias"].shape)  # Should be [16]
   ```
3. If the shape is [16], it's the correct VAE. If it's [48], it's the wrong one.

## Reference

- `Comfy-Org/Wan_2.2_ComfyUI_Repackaged/split_files/vae/` (official repo)
- `wan_2.1_vae.safetensors` (242 MB, 16-channel)
- `wan2.2_vae.safetensors` (48-channel, wrong)

## Pitfall

Never trust the filename. Always verify the latent channel count by reading the safetensors header.
