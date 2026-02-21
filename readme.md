# Serverless AI Image Analysis Pipeline

Fully serverless image analysis on AWS. Users upload an image through a browser — Rekognition detects objects and returns labeled results. Zero servers managed, zero idle compute.

---

## Architecture

```
Browser
  │
  ├──[1] GET /getPresignedUrl ──► API Gateway ──► Lambda ──► S3 (returns signed URL)
  │
  ├──[2] PUT image ──────────────────────────────────────────► S3 (img-uploads-buck)
  │                                                                │
  │                                                         S3 Event Trigger
  │                                                                │
  │                                                                ▼
  │                                                            Lambda
  │                                                                │
  │                                                                ├──► Rekognition (detect labels)
  │                                                                │
  │                                                                └──► DynamoDB (store results)
  │
  └──[3] GET /getLabels ─────────► API Gateway ──► Lambda ──► DynamoDB (return labels to UI)
```

Frontend is served via **CloudFront → S3 static bucket** over HTTPS.
**CloudWatch** monitors Lambda errors. **SNS** sends email alerts on failure.
**S3 Lifecycle** auto-deletes uploads after 10 days.

---

## Flow

**1. Pre-signed URL** — Browser requests a temporary signed upload URL from API Gateway. Lambda generates it and returns it. The image never passes through Lambda or API Gateway — this bypasses the 10MB payload limit and keeps uploads fast.

**2. Direct Upload** — Browser uploads the image straight to S3 using the signed URL. On upload, S3 automatically triggers the processing Lambda.

**3. AI Processing** — Lambda calls Rekognition which returns detected labels with confidence scores. Results are written to DynamoDB against the image ID.

**4. Fetch Results** — Browser calls `/getLabels` with the image key. Lambda reads from DynamoDB and returns the labels to the UI for display.

---

## AWS Services

| Service | Role |
|---------|------|
| S3 (uploads) | Stores images · triggers Lambda on upload · lifecycle auto-deletes after 10 days |
| S3 (static) | Hosts frontend website |
| CloudFront | Global HTTPS delivery of frontend |
| API Gateway | HTTP API — routes frontend requests to Lambda |
| Lambda (×3) | getPresignedUrl · lambda-receives-img · getLabels |
| Rekognition | AI label detection with confidence scores |
| DynamoDB | Stores imageid · image_url · labels · confidence · status |
| CloudWatch | Monitors Lambda error rate |
| SNS | Email alert on Lambda failure |
| IAM | Scoped execution roles per Lambda — no hardcoded credentials |

---

## Stack

<p>
  <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/amazonwebservices/amazonwebservices-original-wordmark.svg" height="45" alt="AWS"/>
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.svg" height="45" alt="Python"/>
</p>

---

## Challenges

**CORS** — Spent significant time debugging cross-origin errors between the frontend and API Gateway. Required correct CORS headers configured on both API Gateway routes and Lambda responses, and `OPTIONS` method handling for preflight requests.

**Lambda Response Headers** — Rekognition calls were succeeding but the frontend wasn't receiving data correctly due to missing or malformed headers in Lambda responses. Had to explicitly set `Content-Type` and CORS headers in every Lambda return.

---

## What I Learned

- How event-driven architecture actually behaves end-to-end in a real deployment — not just theory
- Pre-signed URLs as a pattern for secure, scalable file uploads without routing through application servers
- CORS is not just a frontend problem — it has to be handled at the API Gateway level and inside Lambda responses
- How IAM execution roles replace credential management entirely in serverless environments
- CloudWatch + SNS as a lightweight but production-ready alerting pattern