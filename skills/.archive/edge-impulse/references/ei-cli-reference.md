# ei-cli Reference

## Installation & Setup

```bash
pip install requests matplotlib
python3 scripts/ei-cli.py login --api-key ei_your_key
```

## Command Reference

### login
```
ei-cli login --api-key KEY
```
Saves API key to `~/.config/ei-cli/config.json`. Can also use `EI_API_KEY` env var.

### projects
```
ei-cli projects list
```
Lists all projects with ID, name, and type.

### samples
```
ei-cli samples list [--project ID] [--label LABEL] [--category training|testing|anomaly] [--limit N]
ei-cli samples visualize --sample-id SAMPLE_ID -o output.png
```

The visualize command:
1. Fetches sample metadata via `GET /api/{projectId}/raw-data/{sampleId}`
2. Decodes base64-encoded CSV from `result.file`
3. Creates multi-panel plot showing each sensor axis
4. Saves as PNG

### data
```
ei-cli data upload FILE [--project ID]
```
Uploads file to Ingestion API endpoint `/api/training/files`.
Supported formats: CSV, JSON, CBOR, WAV, JPG, PNG, MP4.

### jobs
```
ei-cli jobs watch JOB-ID
ei-cli jobs STATUS JOB-ID
```
Monitors async job progress. Training jobs poll `/api/jobs/{jobId}/status`.

## Environment Variables
- `EI_API_KEY` - API key (alternative to config file)

## Config File
`~/.config/ei-cli/config.json`:
```json
{
  "api_key": "ei_...",
  "default_project": "123456"
}
```