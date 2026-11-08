# Edge Impulse API Reference Summary

## Base URLs
- **Studio API**: `https://studio.edgeimpulse.com/v1/api`
- **Ingestion API**: `https://ingestion.edgeimpulse.com/api`
- **OpenAPI Spec**: `https://studio.edgeimpulse.com/openapi.yml`

## Authentication
All Studio API requests require:
```
x-api-key: <EI_API_KEY>
```

## Key Endpoints

### Project Management
- `GET /api/{projectId}` - Get project info
- `GET /api/` - List all user projects

### Samples (Data)
- `GET /api/{projectId}/raw-data` - List samples
  - Query params: `?category=training|testing|anomaly&label=label&limit=100&offset=0`
- `GET /api/{projectId}/raw-data/{sampleId}` - Get specific sample
- `DELETE /api/{projectId}/raw-data/{sampleId}` - Delete sample
- `POST /api/{projectId}/raw-data/{sampleId}/rename` - Rename sample label
  - Body: `{"newLabel": "new_label_name"}`

### Data Upload (Ingestion API)
- `POST /api/training/data` - Upload training sample
- `POST /api/testing/data` - Upload testing sample  
- `POST /api/anomaly/data` - Upload anomaly sample
  - Required headers: `x-api-key`, `x-label`, `x-file-name`
  - Accepted formats: Edge Impulse JSON, audio/WAV, image/JPEG, CSV

### Edge Impulse JSON Format
```json
{
  "protected": { "ver": "v1", "alg": "none", "iat": 1735689600 },
  "signature": "empty",
  "payload": {
    "device_name": "device",
    "device_type": "TYPE",
    "interval_ms": 10,
    "sensors": [{ "name": "accX", "units": "m/s2" }],
    "values": [[0.1], [0.2]]
  }
}
```

### Devices
- `GET /api/{projectId}/devices` - List devices
- `POST /api/{projectId}/device/{deviceId}/start-sampling` - Start data collection
  - Body: `{"label": "...", "category": "training", "intervalMs": 10, "lengthMs": 5000, "sensor": "Inertial"}`

### Impulse (Model Pipeline)
- `GET /api/{projectId}/impulse` - Get current pipeline
- `POST /api/{projectId}/impulse` - Update pipeline

### Training Jobs
- `POST /api/{projectId}/jobs/train/{versionId}` - Start training job (returns jobId)
- `GET /api/{projectId}/jobs` - List all jobs
- `GET /api/{projectId}/jobs/{jobId}/status` - Get job status
- `GET /api/{projectId}/jobs/{jobId}/stdout/download` - Download job logs (plain text)

### Deployment
- `GET /api/deployment/targets` - Get deployment targets
- `POST /api/{projectId}/deploy` - Start build
  - Body: `{"deployType": "zip"|"arduino"|"tflite"|"onnx"|...}`
- `GET /api/{projectId}/deploy` - Get artifact download URL
- `POST /api/{projectId}/jobs/build-ondevice-model` - Build on-device model
- `GET /api/{projectId}/deployment/history` - Get deployment history
- `GET /api/{projectId}/deployment/history/{deploymentVersion}/download` - Download deployment

### Versioning
- `GET /api/{projectId}/versions` - List snapshots
- `POST /api/{projectId}/versions` - Create snapshot

### EON Tuner (AutoML)
- `POST /api/{projectId}/tuner/start` - Start AutoML run
- `GET /api/{projectId}/tuner/runs` - List runs and results

### Testing
- `POST /api/{projectId}/jobs/classify` - Classify a sample
- `GET /api/{projectId}/test-results` - Get model test results

### Organizations (Enterprise)
- `GET /api/organizations` - List organizations
- `GET /api/organizations/{orgId}/data/datasets` - Get organization datasets
- `POST /api/organizations/{orgId}/data/upload` - Upload data to organization

## Response Format
All responses include a `success` field:
```json
{ "success": true, ... }
{ "success": false, "error": "message" }
```

Always check `success` before processing other fields.

## Error Handling
When `success` is false, the `error` field contains a descriptive message.
For job failures, always download and inspect the job logs:
`GET /api/{projectId}/jobs/{jobId}/stdout/download`

## Rate Limits & Best Practices
- Implement exponential backoff for rate-limited requests
- Use pagination (`limit` and `offset`) for large sample lists
- Always validate API responses before processing
- Monitor job status with reasonable polling intervals (5-10 seconds)