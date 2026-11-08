# Verified macmon metrics (v0.8.2, macOS 27)

29 gauges, all prefixed `macmon_`. Exposed at `/metrics` (Prometheus format) and `/json` by `macmon serve`. Use `*_active_ratio` — the `*_usage_ratio` / `*_scaled_ratio` variants are marked DEPRECATED in the metric HELP text.

## GPU
- `macmon_gpu_freq_mhz`
- `macmon_gpu_active_ratio` (use this)
- `macmon_gpu_power_watts`
- `macmon_gpu_temp_celsius`
- `macmon_gpu_ram_power_watts`
- deprecated: `macmon_gpu_usage_ratio`, `macmon_gpu_scaled_ratio`

## CPU (P = performance cluster, E = efficiency cluster)
- `macmon_cpu_active_ratio` (combined, weighted by core count — use for overall load)
- `macmon_pcpu_freq_mhz`, `macmon_ecpu_freq_mhz`
- `macmon_pcpu_active_ratio`, `macmon_ecpu_active_ratio`
- deprecated: `macmon_cpu_usage_ratio`, `macmon_cpu_scaled_ratio`, `macmon_pcpu_usage_ratio`, `macmon_pcpu_scaled_ratio`, `macmon_ecpu_usage_ratio`, `macmon_ecpu_scaled_ratio`

## Power (watts)
- `macmon_sys_power_watts` (total system)
- `macmon_all_power_watts` (CPU+GPU+ANE combined)
- `macmon_cpu_power_watts`, `macmon_gpu_power_watts`, `macmon_ane_power_watts`, `macmon_ram_power_watts`

## Memory (bytes)
- `macmon_memory_ram_total_bytes`, `macmon_memory_ram_used_bytes`
- `macmon_memory_swap_total_bytes`, `macmon_memory_swap_used_bytes`

## Temperature (celsius)
- `macmon_cpu_temp_celsius`, `macmon_gpu_temp_celsius`

## Fan
- `macmon_fan_speed_rpm`
