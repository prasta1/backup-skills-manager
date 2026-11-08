# Photon Sidecar Crash Log Excerpt

Example of gateway logs showing the root cause:

```
ERROR hermes_plugins.photon_platform.adapter: [photon] sidecar exited unexpectedly (code -9) — triggering reconnect
ERROR gateway.run: Fatal photon adapter error (SIDECAR_CRASHED): Photon sidecar exited unexpectedly (code -9)
WARNING hermes_plugins.photon_platform.adapter: [photon] inbound stream dropped (/inbound returned 401); reconnecting in 16.0s
WARNING hermes_plugins.photon_platform.adapter: [photon] inbound stream dropped (/inbound returned 401); reconnecting in 30.0s
```

This pattern shows the gateway restarting every ~30 seconds due to the Photon sidecar repeatedly crashing and causing fatal errors.