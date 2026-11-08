import requests, json

API_KEY = "ei_61b005e13e7443fa17d062d34dde59e29ef382d69ffe0817"
PROJECT_ID = 1065371
STUDIO = "https://studio.edgeimpulse.com/v1/api"
HEADERS = {"x-api-key": API_KEY, "Accept": "application/json"}

# Create new impulse for KWS pipeline
impulse = {
  "inputBlocks": [
    {
      "id": 1,
      "type": "time-series",
      "name": "Time series",
      "title": "Time series",
      "axes": ["accX"]
    }
  ],
  "dspBlocks": [
    {
      "id": 2,
      "type": "mfcc",
      "name": "MFCC features",
      "title": "MFCC Features",
      "axes": ["accX"],
      "implementationVersion": 1
    }
  ],
  "learnBlocks": [
    {
      "id": 3,
      "type": "keras-transfer-kws",
      "name": "KWS Classifier",
      "title": "Keyword Spotting Classifier",
      "dsp": [2],
      "implementationVersion": 1
    }
  ]
}

r = requests.post(f"{STUDIO}/{PROJECT_ID}/impulse", headers=HEADERS, json=impulse)
print("Impulse creation result:")
print(json.dumps(r.json(), indent=2))