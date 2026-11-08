---
name: edge-impulse
description: Interact with an Edge Impulse project via the Studio and Ingestion APIs. Use when asked to upload data, list or relabel samples, trigger training, check job status, or export a deployment. Also use when the user asks anything about their Edge Impulse project.
---

Help the user interact with their Edge Impulse project using the Studio and Ingestion APIs.

## Preparation

Check for credentials in the environment before asking:

- `EI_API_KEY` — Edge Impulse API key (starts with `ei_`)
- `EI_PROJECT_ID` — numeric project ID

If either is missing, ask the user. They can find the API key in the project Dashboard under the **Keys** tab, and the project ID under **Project Info**.

## API reference

Base URL: https://studio.edgeimpulse.com/v1
Ingestion URL: https://ingestion.edgeimpulse.com
OpenAPI spec: https://studio.edgeimpulse.com/openapi.yml

Authentication header for all Studio API requests:

```text
x-api-key: <EI_API_KEY>
```

### Key endpoints

**Project**

```text
GET /api/{projectId}    project info
GET /api/               list all user projects
```

**Samples**

```text
GET    /api/{projectId}/raw-data                    list samples
GET    /api/{projectId}/raw-data/{sampleId}         get one sample
DELETE /api/{projectId}/raw-data/{sampleId}         delete a sample
POST   /api/{projectId}/raw-data/{sampleId}/rename  relabel a sample
```

Use `?category=training|testing|anomaly`, `?limit`, `?offset`, and `?labels` when listing samples.
Relabel body: `{ "newLabel": "label" }`

**Data upload (Ingestion API)**

```text
POST /api/training/data  upload training sample
POST /api/testing/data   upload testing sample
POST /api/anomaly/data   upload anomaly sample
```

Required headers: `x-api-key`, `x-label`, `x-file-name`.
Accepted bodies: Edge Impulse JSON, audio/WAV, image/JPEG, CSV.

Edge Impulse JSON format:

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

**Devices**

```text
GET  /api/{projectId}/devices
POST /api/{projectId}/device/{deviceId}/start-sampling
```

Start-sampling body: `{ "label": "...", "category": "training", "intervalMs": 10, "lengthMs": 5000, "sensor": "Inertial" }`

**Impulse**

```text
GET  /api/{projectId}/impulse    get current pipeline definition
POST /api/{projectId}/impulse    update pipeline
```

**Training**

```text
POST /api/{projectId}/jobs/train/{versionId}       start training job → returns jobId
GET  /api/{projectId}/jobs                         list jobs
GET  /api/{projectId}/jobs/{jobId}/status          job status
GET  /api/{projectId}/jobs/{jobId}/stdout/download job log (plain text, not JSON)
```

Jobs are async. Poll `/jobs/{jobId}/status` until `.job.finished` is true, then check `.job.finishedSuccessful`. On failure, fetch `/jobs/{jobId}/stdout/download` and show the relevant error lines. Users can also monitor progress at `https://studio.edgeimpulse.com/studio/<projectId>/jobs`.

**Deployment**

```text
GET  /api/deployment/targets
POST /api/{projectId}/deploy    start build — body: { "deployType": "zip"|"arduino"|"tflite"|"onnx"|... }
GET  /api/{projectId}/deploy    get artifact download URL
POST /api/{projectId}/jobs/build-ondevice-model
GET  /api/{projectId}/deployment/history
GET  /api/{projectId}/deployment/history/{deploymentVersion}/download
```

**Versions**

```text
GET  /api/{projectId}/versions    list snapshots
POST /api/{projectId}/versions    create snapshot
```

**EON Tuner**

```text
POST /api/{projectId}/tuner/start    start AutoML run
GET  /api/{projectId}/tuner/runs     list runs and results
```

**Testing**

```text
POST /api/{projectId}/jobs/classify    classify a sample
GET  /api/{projectId}/test-results     model test results
```

**Organizations (Enterprise)**

```text
GET  /api/organizations
GET  /api/organizations/{orgId}/data/datasets
POST /api/organizations/{orgId}/data/upload
```

### Response shape

Every response has a `success` field:

```json
{ "success": true, ... }
{ "success": false, "error": "message" }
```

Always check `success` before reading other fields. Raise a clear error if `success` is false.

## Python skeleton

```python
import os, requests

API_KEY=os.environ.get("EI_API_KEY") or input("API key: ")
PROJECT_ID = int(os.environ.get("EI_PROJECT_ID") or input("Project ID: "))
STUDIO = "https://studio.edgeimpulse.com/v1/api"
INGEST = "https://ingestion.edgeimpulse.com/api"

s = requests.Session()
s.headers.update({"x-api-key": API_KEY, "Accept": "application/json"})

def get(path, **params):
    r = s.get(f"{STUDIO}/{PROJECT_ID}{path}", params=params)
    r.raise_for_status()
    d = r.json()
    if not d.get("success"):
        raise RuntimeError(d.get("error", "unknown error"))
    return d

def post(path, body=None, base=STUDIO):
    r = s.post(f"{base}/{PROJECT_ID}{path}" if base == STUDIO else f"{base}{path}", json=body)
    r.raise_for_status()
    d = r.json()
    if not d.get("success"):
        raise RuntimeError(d.get("error", "unknown error"))
    return d
```

## Instructions

1. Understand the task from the user's request.
2. Write Python using the skeleton above, or use curl/shell commands for one-off requests.
3. Run the code and show results clearly.
4. For long-running jobs: poll `GET /api/{projectId}/jobs/{jobId}/status` until `.job.finished` is true. If `.job.finishedSuccessful` is false, fetch `GET /api/{projectId}/jobs/{jobId}/stdout/download` (plain text, not JSON) and show the relevant error lines. Always inform the user they can also monitor progress at `https://studio.edgeimpulse.com/studio/<projectId>/jobs`.
5. For unknown endpoints, fetch https://studio.edgeimpulse.com/openapi.yml and find the right path.
6. **For data visualization**: When users want to visualize sensor data from samples:
   - Use `GET /api/{projectId}/raw-data/{sampleId}` to get sample metadata
   - The actual sensor data is base64-encoded CSV in `result.file`
   - Decode the base64 string to get CSV text
   - Parse CSV with columns like `timestamp`, `ax`, `ay`, `az`, `gx`, `gy`, `gz`, `label`
   - Plot sensor columns (accelerometer/gyroscope) against sample index or timestamp

See all 191 lines

The edge-impulse skill is one large skill covering the Edge Impulse Studio and Ingestion API surface. As your usage grows, consider splitting it into more focused skills (or companion skills) such as upload-ei-data, label-ei-data, train-ei-model, and deploy-impulse so each one loads less context and triggers more precisely.

## Amplitude Analytics (absorbed from amplitude-analytics)

When validating Edge Impulse customer health (Trinity validation) or pulling customer usage data for health assessment, use Amplitude Analytics. Event and property names are project-specific — discover them before filtering. Never guess an event name: a query built on a hallucinated event returns a plausible-looking empty result, which silently reads as "this account is dead."

### Quick Setup
Store `AMPLITUDE_API_KEY`, `AMPLITUDE_SECRET_KEY`, and `AMPLITUDE_PROJECT_ID` in a local env/secret store. Use direct REST API calls with basic auth from those env vars.

### Event Discovery First
Always discover the actual event vocabulary before querying:
```bash
curl -u "$AMPLITUDE_API_KEY:$AMPLITUDE_SECRET_KEY" \
  "https://amplitude.com/api/2/events?limit=100"
```

Or use the bundled discovery script:
```bash
python3 scripts/amplitude_discover.py
```

### Trinity Validation Queries
- **Data Ingestion**: Look for upload/transfer events
- **Model Training**: Look for training/job events
- **Deployment**: Look for deploy/deployment events

### Window Defaults (Per SOUL.md Section 4)
- Trailing 30 days for current activity
- Trailing 90 days for trend comparison
- "Stalled": leg was active, now silent for full window
- Always name the window used in reports

### Common Analysis Patterns

**Product Usage Health Score:**
```bash
curl -u "$AMPLITUDE_API_KEY:$AMPLITUDE_SECRET_KEY" \
  "https://amplitude.com/api/2/export?start=$(date -d '30 days ago' +%Y%m%dT%H)&end=$(date +%Y%m%dT%H)"
```

**Cohort Analysis for Expansion Signals:**
- Query: active users by feature over time
- Look for: increasing usage patterns = upsell readiness
- Query: power user behaviors = product adoption champions

**Churn Risk Indicators:**
- Query: declining weekly active days
- Query: reduced feature engagement
- Query: spike in support-related events

### Customer Success Queries

**Account Usage Deep Dive:**
```bash
# Events for specific user/company ID
# Group by: event_type, daily_active_users, retention
# Timeframe: last 60 days, compare to previous period
```

**Feature Adoption Tracking:**
- Track: new feature usage by existing customers
- Correlate: feature adoption with deal stage progression
- Identify: customers using >80% of features = expansion targets

### Integration with HubSpot
- Use HubSpot company_id as Amplitude user property
- Join: Amplitude usage data + HubSpot deal stages
- Automate: health scores → HubSpot custom properties

### Scripts
- `scripts/amplitude_discover.py` — Discover available Amplitude events for the project (absorbed from amplitude-analytics)
- `scripts/amplitude_setup.sh` — One-time Amplitude API credential setup (absorbed from amplitude-analytics)

## Reference Files

- `references/customer-data.md` — Documents the customer data files (`ei_customers`, `ei_contacts`) and their location, plus related HubSpot CRM exports and CS operations context.
- `references/source.md` — Source documentation
- `references/ei-cli-reference.md` — CLI tool reference
- `references/api-reference.md` — API endpoint reference
- `references/cs-amplitude-setup.md` — Amplitude API setup for Edge Impulse Trinity validation
- `references/amplitude-discover-events.md` — Amplitude API setup and event discovery guide (absorbed from amplitude-analytics)

## Install the skill

Save the file above to one of the paths below. Skills can be installed globally (available across all projects) or per project. Refer to your agent's documentation if you use a tool not listed here.

Agent	| Global (all projects)	| Per project
------|----------------------|------------
Claude Code	| ~/.claude/skills/edge-impulse/SKILL.md	| .claude/skills/edge-impulse/SKILL.md
OpenAI Codex	| ~/.agents/skills/edge-impulse/SKILL.md	| .agents/skills/edge-impulse/SKILL.md
GitHub Copilot	| ~/.copilot/skills/edge-impulse/SKILL.md or ~/.agents/skills/edge-impulse/SKILL.md	| .github/skills/edge-impulse/SKILL.md
Antigravity (previously Gemini CLI)	| ~/.gemini/skills/edge-impulse/SKILL.md	| .agents/skills/edge-impulse/SKILL.md

## Use the skill

Ask your agent to work with your Edge Impulse project. The agent loads the skill automatically when your prompt matches, or you can invoke it explicitly with `/edge-impulse`:

/edge-impulse list all training samples labeled "unknown" and delete them

/edge-impulse upload every .wav file in ./data as testing samples with label "noise"

/edge-impulse start a training job and wait for it to finish, then show accuracy

/edge-impulse export a C++ library deployment and save it to ./build

To see a selection of example prompts, take a look at our Prompt library.

Claude Code running the /edge-impulse skill

## Set your credentials

Set environment variables so your agent never needs to ask for credentials:

export EI_API_KEY="ei_....port EI_PROJECT_ID="12345"

Find your API key under Dashboard → Keys and your project ID under Project Info in Edge Impulse Studio.

Adding an Edge Impulse API key and project ID with the /edge-impulse skill in Claude Code

## Optimize the skill for your workflow

If you find yourself making the same API calls repeatedly — listing samples, checking job status, fetching project info — ask the agent to add those patterns directly to the skill file so it can handle them faster next time:

Read ~/.claude/skills/edge-impulse/SKILL.md and add a section at the bottom with a ready-made Python snippet for listing all training samples grouped by label, since I use this at the start of every session.

Look at my last few Edge Impulse pulses and update ~/.claude/skills/edge-impulse/SKILL.md with any patterns I use frequently that aren't already covered.

The skill file is just markdown — anything you add becomes part of the agent's persistent context for every future session.

Keep SKILL.md under 500 lines. Move detailed reference material — long endpoint tables, full request/response examples, language-specific snippets — into separate files in the skill directory (such as reference.md or examples.md) and link to them from SKILL.md. Supporting files load only when the agent decides it needs them, so the main skill stays focused and cheap to load.

## Tooling

### CLI Companion Tool

For users who prefer command-line interaction over writing Python scripts, the skill includes `scripts/ei-cli.py` - a standalone CLI tool that wraps the Edge Impulse APIs:

```bash
# Install dependencies
pip install requests matplotlib

# Configure
python3 scripts/ei-cli.py login --api-key ei_your_key
python3 scripts/ei-cli.py projects list

# List samples with filters
python3 scripts/ei-cli.py samples list --project 123456 --label walking

# Visualize sample data (generates PNG)
python3 scripts/ei-cli.py samples visualize --project 123456 --sample-id 789012 -o sample.png

# Upload data
python3 scripts/ei-cli.py data upload data.csv --project 123456

# Monitor jobs
python3 scripts/ei-cli.py jobs watch job-123456
```

The CLI saves configuration to `~/.config/ei-cli/config.json` and supports `EI_API_KEY` environment variable. See `references/ei-cli-reference.md` for full command documentation.

### Python Visualization Script

The `scripts/visualize_samples.py` script fetches all training samples and generates multi-panel plots showing accelerometer and gyroscope data over sample indices.

## Tips

Ask for error handling. The Edge Impulse API returns { "success": false, "error": "..." } on failure. Ask the agent to check this field in every response.

Reference the OpenAPI spec for edge cases. For endpoints not covered by the skill, direct the agent to https://studio.edgeimpulse.com/openapi.yml for the full schema.

For data visualization tasks, you can use the `scripts/visualize_samples.py` script included in this skill. This script handles the full workflow of authenticating with Edge Impulse, fetching sample data, decoding the CSV, and generating plots of sensor readings.

## Next steps

Follow the end-to-end Motion recognition tutorial to take a project from data collection through deployment using only natural language commands

Create a companion skill for your target hardware so the agent can write application code alongside the API calls

Browse the prompt library for ready-to-use prompts covering every stage of an Edge Impulse project

Browse Studio API endpoints for the full endpoint reference