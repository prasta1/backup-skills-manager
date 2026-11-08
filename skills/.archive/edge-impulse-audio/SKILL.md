---
name: edge-impulse-audio
description: Continuous audio and voice UI workflows on Edge Impulse.
category: mlops
---

# Edge Impulse Audio

Use this skill for speech-to-text, continuous audio classification, on-device voice UI, or microphone-to-screen inference on Edge Impulse. For general Studio API work, use `edge-impulse`. For keyword spotting on microcontrollers, use `edge-impulse-kws-setup`. This skill encodes audio-specific decisions: pipeline block choice, memory budget, deployment target, and vocabulary scope.

## First decision: fixed vocab or free-form ASR

Ask explicitly. Free-form ASR on embedded targets is large and RAM-heavy. If the use case is a radio-style readout with a constrained command set, prefer fixed vocabulary and treat ASR as structured audio classification.

- **Fixed vocab / command set**: smallest footprint, fastest inference, highest on-device success rate.
- **Free-form dictation**: realistic only when the device can host large TFLite/ONNX artifacts, or when you accept a pretrained encoder + external decoder pattern.

## Recommended pipeline

1. **Input**: audio block, not IMU or generic time series.
2. **DSP**: MFCC or spectral-analysis. Do not skip DSP on embedded targets; pretrained front-ends exist but need more RAM and more labeled samples.
3. **Learning block**: use the continuous-audio path. `speech_keyword` is for trigger-word spotting, not transcript readout.

## Memory-cost warning

On-device ASR is materially bigger than KWS. Before training, set a hard budget for RAM/Flash and choose accordingly:

- **TFLite float32**: simplest path, larger artifact.
- **EON / int8 TFLite**: tighter footprint, more preprocessing-sensitive.
- **C/C++ library**: full integration control, usually highest engineering cost.

Do not promise KWS artifact size for an ASR workload.

## Deployment strategy

- **Prototype in browser**: `wasm-browser-simd` for fast iteration.
- **On-device target**: choose C/C++ library or TFLite based on the radio’s MPU memory class. EON-compiled TFLite is usually the best tradeoff on embedded Linux-class hardware.
- **Inference integration**: connect model output directly to display text or command routing. Add NLU only if vocab ambiguity forces it.

## Radio-style use case pattern

For microphone-to-screen radio behavior:
- Define classes for commands plus station-related tokens.
- Output should drive a constraint list, not open-ended transcript generation if you can avoid it.
- Keep latency short; continuous listening must stay lightweight.

## API-verification habit

When validating Edge Impulse credentials:
- A 403 on `/api` or `/{projectId}/impulse` does not necessarily mean the key is invalid. It can mean the key’s project scope is wrong.
- Run one focused probe per scope first: project info, impulse, raw-data, jobs, deployment targets. If all return access-denied, stop retrying and ask the user to confirm the key-to-project mapping in the Dashboard.

## References

- `references/asr-embed-ai.md` — choosing TFLite versus EON versus C library for audio inference
- `references/radio-display-pattern.md` — command-routing pattern for microphone-to-screen radios
