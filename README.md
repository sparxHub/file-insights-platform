# Media Files Insights Platform

A production‑ready system for **resumable uploads** (video, images or any large binary) that automatically triggers **AI workflows** to extract insights from the content once the file lands in S3.

[![Tests](https://github.com/<USERNAME>/file-insights-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/<USERNAME>/file-insights-platform/actions)

---

## ✨ Features

* **Chunked & resumable uploads** – multipart S3, up to 5 GB  
* **Presigned URLs** – clients upload **directly** to S3; the API never touches the bytes  
* **Hexagonal architecture** – clean separation of adapters / services / controllers  
* **JWT Auth** – simple bearer token middleware  
* **AI insight pipeline** – SQS‑backed Lambda workers to analyse media content  
* **Fully‑typed Python 3.11** with Pydantic v2, mypy and boto3‑stubs  
* **Offline tests** – AWS calls mocked, async‑native tests run in CI

---

## 🗂️ Repository layout

```text
file-insights-platform/
├── apps/
│   ├── api/
│   │   └── app/
│   │       ├── main.py
│   │       ├── core/
│   │       │   └── config.py
│   │       ├── models/
│   │       │   ├── upload.py
│   │       │   └── user.py
│   │       ├── adapters/
│   │       │   ├── s3_adapter.py
│   │       │   └── dynamodb_adapter.py
│   │       ├── services/
│   │       │   └── upload_service.py
│   │       ├── middleware/
│   │       │   └── auth.py
│   │       ├── controllers/
│   │       │   └── upload_controller.py
│   │       └── api/
│   │           └── routes/
│   │               ├── auth_routes.py
│   │               └── upload_routes.py
│   └── web/                         # React console (stub)
├── infrastructure/
│   └── cloudformation/
│       └── file-insights-stack.yaml
├── tests/
│   ├── conftest.py
│   └── apps/
│       └── api/
│           ├── auth/
│           │   └── test_auth_routes.py
│           └── uploads/
│               └── test_upload_routes.py
├── .github/
│   └── workflows/
│       └── ci.yml
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

## 📦 Quick‑start (local)

```bash
# 1 clone & install deps
git clone https://github.com/<USERNAME>/file-insights-platform.git
cd file-insights-platform
pdm install

# 2 configure
cp .env.example .env

# 3 run API
pdm run uvicorn apps.api.app.main:app --reload
open http://localhost:8000/docs
```

---

## 🧪 Tests

```bash
pdm run pytest -q
```

All tests stub AWS adapters; no cloud credentials are required.

---

## 🛠️ Environment variables

| Variable | Description |
|----------|-------------|
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | IAM user/role keys |
| `AWS_REGION` | Default `us-east-1` |
| `S3_BUCKET_NAME` | Upload bucket |
| `DYNAMODB_UPLOADS_TABLE` | Metadata table |
| `JWT_SECRET_KEY` | HS256 signing secret |
| … | See `.env.example` |

---

## 🏗️ Deployment & CI

* **CI/CD** – `.github/workflows/ci.yml` runs lint + tests on every push.  
* **Infrastructure** – deploy `infrastructure/cloudformation/file-insights-stack.yaml` (S3, DynamoDB, SQS, IAM).  
* **Docker** – `Dockerfile` builds a slim image; push to ECR or run on ECS/Fargate.

---

## License

MIT
