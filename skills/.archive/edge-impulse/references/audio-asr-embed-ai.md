# ASR on Embedded Edge Impulse Targets

## TFLite float32

- Simplest path.
- Usually runs on embedded Linux-class devices.
- Largest RAM/Flash among the usual deployment formats.

## EON / int8 TFLite

- Tighter footprint.
- More sensitive to audio preprocessing drift.
- Prefer when host memory is the actual bottleneck.

## C/C++ library

- Best integration control.
- Builds can target broader MCU families.
- Highest engineering cost for display/audio threading.

## Pitfalls

- Do not compare KWS model size to ASR model size. ASR use cases need materially more memory.
- Short utterances are much cheaper than continuous models. If the radio only acts on commands, structure training around discrete segments.
- Continuous transcription is far more expensive than keyword spotting. If full transcript is not required, constrain to command + station tokens.
