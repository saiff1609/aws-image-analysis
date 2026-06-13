# Serverless AI Image Analysis Pipeline

Fully serverless image analysis on AWS. Users upload an image through a browser — Rekognition detects objects and returns labeled results with confidence scores. Zero servers managed, zero idle compute.

![App Demo](screenshots/01-app-demo.png)

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

Frontend served via **CloudFront → S3 static bucket** over HTTPS.  
**CloudWatch** monitors Lambda errors. **SNS** sends email alerts on failure.  
**S3 Lifecycle** auto-deletes uploads after 10 days.

---

## Flow

User opens the web app served over CloudFront. They select an image and hit upload.

Before the image goes anywhere, the browser asks API Gateway for a pre-signed URL — a temporary, scoped link that allows a direct upload straight to S3. Lambda generates this and returns it instantly. The image never passes through Lambda or API Gateway, which keeps uploads fast and sidesteps API Gateway's 10MB payload limit.

The browser uploads the image directly to S3 using that signed URL. The moment the object lands in the bucket, S3 fires an event that automatically triggers the processing Lambda — no polling, no manual invocation needed on the backend.

That Lambda calls Amazon Rekognition, which scans the image and returns detected objects with confidence scores. The results — image ID, S3 URL, labels, confidence, and status — are written to DynamoDB.

The frontend then polls `/getLabels` with the image key, retrying every 1.5 seconds until the record appears in DynamoDB. Lambda reads the item and returns the label data to the UI, which renders it as cards with confidence progress bars.


---

## AWS Services

| Service | Role |
|---------|------|
| S3 (uploads) | Stores images · triggers Lambda on upload · lifecycle deletes after 10 days |
| S3 (static) | Hosts frontend website |
| CloudFront | Global HTTPS delivery of frontend |
| API Gateway | HTTP API — routes frontend requests to Lambda |
| Lambda ×3 | `getPresignedUrl` · `lambda-receives-img` · `getLabels` |
| Rekognition | AI label detection with confidence scores |
| DynamoDB | Stores `imageid` · `image_url` · `labels` · `confidence` · `status` |
| CloudWatch | Monitors Lambda error rate |
| SNS | Email alert on Lambda failure |
| IAM | Scoped execution roles per Lambda — no hardcoded credentials |

---

## Stack

<p>
  <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/amazonwebservices/amazonwebservices-original-wordmark.svg" height="45" alt="AWS"/>
  &nbsp;
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.svg" height="45" alt="Python"/>
  &nbsp;
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/javascript/javascript-original.svg" height="45" alt="JavaScript"/>
</p>

---

## Repo Structure

```
serverless-ai-image-analysis/
│
├── README.md
│
├── lambda/
│   ├── getPresignedUrl.py        # Generates S3 pre-signed upload URL
│   ├── lambda-receives-img.py    # S3 trigger → Rekognition → DynamoDB
│   └── getLabels.py              # Reads DynamoDB, returns labels to frontend
│
├── frontend/
│   ├── index.html                # Web UI
│   └── script.js                 # Upload flow, polling, label rendering
│
├── s3-policies/
│   └── cors-policy.json          # S3 bucket CORS config
│
├── screenshots/
│   ├── 01-app-demo.png           # in README
│
└── docs/
    ├── 03-lambda-functions.png
    ├── 04-api-gateway-routes.png
    ├── 05-dynamodb-item.png
    ├── 06-s3-uploads.png
    ├── 07-cloudwatch-logs.png
    ├── 08-sns-alert.png
    └── 09-network-devtools.png
```

---

## Challenges

**API Gateway — ERR_NAME_NOT_RESOLVED**

After fixing the endpoint typo and redeploying, the frontend was still hitting `ERR_NAME_NOT_RESOLVED` — the browser couldn't resolve the API domain at all. Turned out the `script.js` on CloudFront still had the wrong API ID from an earlier version of the setup. The deployed file and the local file had diverged. Confirmed by opening the CloudFront URL for `script.js` directly in the browser — it was serving the old version. Fixed by re-uploading the correct file to S3 and running a CloudFront cache invalidation.

**CloudFront Caching**

CloudFront aggressively caches static files. Updating `script.js` on S3 doesn't automatically update what CloudFront serves — you have to explicitly create an invalidation (`/*` or `/script.js`) and wait for it to complete. Without this step, users keep getting the old cached file regardless of what's on S3. This also meant hard-reloading the browser (`Ctrl+Shift+R`) after the invalidation to clear the local browser cache on top of CloudFront.

**Pre-signed URL Upload Pattern**

Routing image uploads through Lambda would immediately hit API Gateway's 10MB payload limit and add unnecessary latency. Pre-signed URLs solve this cleanly — Lambda generates a temporary, scoped S3 URL and returns it to the browser, which then uploads the file directly to S3. Lambda never touches the file bytes. This is the standard production pattern for serverless file uploads and scales without any changes.

**DynamoDB Decimal Serialization**

Rekognition returns confidence scores as Python `float` values. DynamoDB rejects native floats — it requires `Decimal`. Had to explicitly convert on write using `Decimal(str(label['Confidence']))`, then convert back to `float` on read before JSON serialization, otherwise the Lambda response would throw a `TypeError`. A small but breaking detail if missed.

---

## What I Learned

- How event-driven architecture behaves end-to-end in a real deployment — S3 events, async Lambda triggers, DynamoDB reads — not just theory
- Pre-signed URLs as a pattern for secure, scalable uploads that bypass application servers entirely
- CloudFront caching is aggressive — updating a file on S3 means nothing until you invalidate and the browser cache is also cleared
- A wrong API ID or endpoint name surfaces as a CORS error or DNS failure, not a helpful 404 — always verify the exact URL being called in DevTools before touching infrastructure config
- IAM execution roles replace credential management entirely in serverless — no `.env` files, no hardcoded secrets
- CloudWatch + SNS as a lightweight but production-ready alerting pattern that works out of the box
- DynamoDB type constraints (no native float) and how serialization issues can silently break Lambda responses
