# SwitchKit — Lead Capture Automation
# Claude Code Prompt v2.0 (DynamoDB + FastAPI)
# Paste this entire file into Claude Code as the first message in a new session.

---

## CONTEXT

I'm building SwitchKit (exitroutes.com) — a $199 data migration service for pest control
operators trying to leave FieldRoutes/PestRoutes. The landing page is built. This session
builds the automated lead capture backend.

Pest control operators publicly complain about FieldRoutes on Capterra, G2, SoftwareAdvice,
GetApp, and Reddit. I want to scrape those complaints automatically, score them by urgency,
store them in DynamoDB, and expose them via a FastAPI backend so I can build an outreach
UI on top later.

---

## STACK

- **Runtime:** Python 3.11+
- **API framework:** FastAPI + Uvicorn
- **Database:** AWS DynamoDB (single-table design)
- **AWS SDK:** boto3
- **Scraping:** requests + BeautifulSoup4
- **Validation:** Pydantic v2
- **Config:** pydantic-settings + python-dotenv
- **Testing:** pytest + moto (DynamoDB mock — no real AWS needed for tests)
- **Deploy target:** AWS Lambda via Mangum, or EC2 — design for both

---

## FILE STRUCTURE

```
exitroutes-leads/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app, middleware, router registration
│   ├── config.py                # Settings, keywords, scraper URLs
│   ├── models.py                # Pydantic request/response models
│   ├── auth.py                  # API key dependency
│   ├── db/
│   │   ├── __init__.py
│   │   ├── dynamo.py            # DynamoClient class, all CRUD
│   │   └── schema.py            # Key builders, GSI constants, table creation
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── base.py              # Abstract base scraper
│   │   ├── capterra.py
│   │   ├── g2.py
│   │   ├── softwareadvice.py
│   │   ├── getapp.py
│   │   └── reddit.py
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── review_parser.py     # Pain scoring, fingerprinting, field extraction
│   │   └── reddit_parser.py
│   ├── enricher.py              # Business name → website + phone lookup
│   ├── deduplicator.py          # Fuzzy dedup beyond fingerprint constraint
│   └── routers/
│       ├── __init__.py
│       ├── leads.py             # /leads CRUD + export
│       ├── scrape.py            # /scrape trigger + run history
│       └── stats.py             # /stats pipeline summary
├── tests/
│   ├── conftest.py              # moto fixtures, sample lead factory
│   ├── test_parser.py
│   ├── test_dynamo.py
│   ├── test_leads_api.py
│   ├── test_scrape_api.py
│   └── fixtures/
│       ├── capterra_page.html   # Saved HTML for scraper tests
│       ├── g2_page.html
│       └── reddit_response.json
├── requirements.txt
├── .env.example
├── Makefile
└── README.md
```

---

## DYNAMODB DESIGN

File: `app/db/schema.py`

### Single table: `switchkit-leads`

**Primary key:** PK (string) + SK (string)
**Billing:** PAY_PER_REQUEST (no capacity planning at MVP scale)

### Item types and key patterns

```python
# Lead/contact item
PK  = "LEAD#{lead_id}"
SK  = "LEAD#{lead_id}"

# Scrape run item
PK  = "RUN#{run_id}"
SK  = "RUN#{run_id}"

# Stats singleton
PK  = "STATS"
SK  = "STATS"
```

### Global Secondary Indexes

All GSIs project ALL attributes (no projection limits at MVP scale).

```
GSI1 — query by source, sorted by pain score desc
  GSI1PK = "SOURCE#{source}"               e.g. "SOURCE#capterra"
  GSI1SK = "PAIN#{pain_score:02d}#{created_at_iso}"

GSI2 — query by outreach status, sorted by pain score desc
  GSI2PK = "STATUS#{outreach_status}"      e.g. "STATUS#new"
  GSI2SK = "PAIN#{pain_score:02d}#{created_at_iso}"

GSI3 — query hot leads (switching signal), sorted by pain score desc
  GSI3PK = "SWITCHING#{true|false}"
  GSI3SK = "PAIN#{pain_score:02d}#{created_at_iso}"

GSI4 — dedup lookup by fingerprint
  GSI4PK = "FP#{fingerprint}"
  GSI4SK = "FP#{fingerprint}"
```

Pain score is zero-padded to 2 digits so string sort = numeric sort desc
(use "PAIN#09" not "PAIN#9"). Since DynamoDB sorts ascending, callers should
ScanIndexForward=False to get highest pain scores first.

### Key builder helpers

```python
def lead_pk(lead_id: str) -> str:
    return f"LEAD#{lead_id}"

def source_gsi1pk(source: str) -> str:
    return f"SOURCE#{source}"

def pain_sk(pain_score: int, created_at: str) -> str:
    return f"PAIN#{pain_score:02d}#{created_at}"

def status_gsi2pk(status: str) -> str:
    return f"STATUS#{status}"

def switching_gsi3pk(value: bool) -> str:
    return f"SWITCHING#{str(value).lower()}"

def fingerprint_gsi4pk(fp: str) -> str:
    return f"FP#{fp}"
```

### Full lead item shape

```python
{
    # DynamoDB keys
    "PK":     "LEAD#uuid4",
    "SK":     "LEAD#uuid4",
    "GSI1PK": "SOURCE#capterra",
    "GSI1SK": "PAIN#09#2026-04-01T10:30:00Z",
    "GSI2PK": "STATUS#new",
    "GSI2SK": "PAIN#09#2026-04-01T10:30:00Z",
    "GSI3PK": "SWITCHING#true",
    "GSI3SK": "PAIN#09#2026-04-01T10:30:00Z",
    "GSI4PK": "FP#md5hash",
    "GSI4SK": "FP#md5hash",
    "Type":   "LEAD",

    # Identity
    "lead_id":     "uuid4-string",
    "fingerprint": "md5-hash",

    # Source
    "source":     "capterra",
    "source_url": "https://www.capterra.com/...",
    "source_id":  "platform-review-id",
    "scraped_at": "2026-04-01T10:30:00Z",

    # Business (from review)
    "business_name":  "Termite Lawn and Pest Inc",
    "reviewer_name":  "Dallas Q.",
    "reviewer_role":  "Owner",
    "company_size":   "2-10 employees",

    # Contact (from enrichment — may be null)
    "website": "https://terminitelawnandpest.com",
    "phone":   "(407) 555-1234",
    "email":   None,
    "city":    "Orlando",
    "state":   "FL",

    # Pain signals
    "rating":                 1,
    "pain_score":             9,
    "mentions_switching":     True,
    "mentions_data_hostage":  True,
    "mentions_support":       False,
    "mentions_pricing":       True,
    "raw_complaint":          "They want $500 for an incomplete backup...",
    "full_review_text":       "...",

    # Outreach tracking
    "outreach_status": "new",       # new | contacted | replied | converted | not_interested
    "outreach_method": None,        # email | phone | facebook | linkedin
    "outreach_date":   None,
    "outreach_notes":  None,
    "follow_up_date":  None,

    # Timestamps
    "created_at": "2026-04-01T10:30:00Z",
    "updated_at": "2026-04-01T10:30:00Z",
}
```

### Table creation helper

```python
def create_table_if_not_exists(dynamo_resource, table_name: str) -> None:
    """
    Creates the switchkit-leads table with all 4 GSIs.
    Idempotent — safe to call on startup.
    Used for local dev and CI (moto).
    """
    existing = [t.name for t in dynamo_resource.tables.all()]
    if table_name in existing:
        return

    dynamo_resource.create_table(
        TableName=table_name,
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[
            {"AttributeName": "PK",     "AttributeType": "S"},
            {"AttributeName": "SK",     "AttributeType": "S"},
            {"AttributeName": "GSI1PK", "AttributeType": "S"},
            {"AttributeName": "GSI1SK", "AttributeType": "S"},
            {"AttributeName": "GSI2PK", "AttributeType": "S"},
            {"AttributeName": "GSI2SK", "AttributeType": "S"},
            {"AttributeName": "GSI3PK", "AttributeType": "S"},
            {"AttributeName": "GSI3SK", "AttributeType": "S"},
            {"AttributeName": "GSI4PK", "AttributeType": "S"},
            {"AttributeName": "GSI4SK", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "GSI1-source-pain",
                "KeySchema": [
                    {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "GSI2-status-pain",
                "KeySchema": [
                    {"AttributeName": "GSI2PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI2SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "GSI3-switching-pain",
                "KeySchema": [
                    {"AttributeName": "GSI3PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI3SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "GSI4-fingerprint",
                "KeySchema": [
                    {"AttributeName": "GSI4PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI4SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
    )
```

---

## DYNAMODB CLIENT

File: `app/db/dynamo.py`

```python
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from datetime import datetime, timezone
import uuid, json, base64, logging
from app.db.schema import (
    lead_pk, source_gsi1pk, pain_sk, status_gsi2pk,
    switching_gsi3pk, fingerprint_gsi4pk, create_table_if_not_exists
)
from app.config import settings

logger = logging.getLogger(__name__)

class DynamoClient:
    def __init__(self):
        kwargs = {"region_name": settings.AWS_REGION}
        if settings.DYNAMO_ENDPOINT_URL:
            kwargs["endpoint_url"] = settings.DYNAMO_ENDPOINT_URL
        self.resource = boto3.resource("dynamodb", **kwargs)
        create_table_if_not_exists(self.resource, settings.DYNAMO_TABLE_NAME)
        self.table = self.resource.Table(settings.DYNAMO_TABLE_NAME)
```

### Method specs:

**`put_lead(item: dict) -> str | None`**

Build all GSI keys from item fields, then attempt a conditional PutItem.
First check fingerprint uniqueness via GSI4 query. If duplicate, return None.
If new, put item and return `lead_id`.

```python
def put_lead(self, item: dict) -> str | None:
    # 1. Check fingerprint uniqueness
    existing = self.get_lead_by_fingerprint(item["fingerprint"])
    if existing:
        return None

    lead_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    pain = item["pain_score"]
    source = item["source"]
    status = item.get("outreach_status", "new")
    switching = item.get("mentions_switching", False)
    fp = item["fingerprint"]

    full_item = {
        **item,
        "PK":     lead_pk(lead_id),
        "SK":     lead_pk(lead_id),
        "GSI1PK": source_gsi1pk(source),
        "GSI1SK": pain_sk(pain, now),
        "GSI2PK": status_gsi2pk(status),
        "GSI2SK": pain_sk(pain, now),
        "GSI3PK": switching_gsi3pk(switching),
        "GSI3SK": pain_sk(pain, now),
        "GSI4PK": fingerprint_gsi4pk(fp),
        "GSI4SK": fingerprint_gsi4pk(fp),
        "Type":       "LEAD",
        "lead_id":    lead_id,
        "created_at": now,
        "updated_at": now,
        "outreach_status": status,
    }

    self.table.put_item(Item=full_item)
    self._increment_stats(source, switching)
    return lead_id
```

**`get_lead(lead_id: str) -> dict | None`**

GetItem by PK/SK. Return None if not found.

**`update_lead(lead_id: str, updates: dict) -> dict`**

Build UpdateExpression dynamically. Always set `updated_at`.

If `outreach_status` changes, also update GSI2PK/GSI2SK to reflect new status.
Note: In DynamoDB you cannot update GSI keys directly without rewriting the item.
For MVP, handle this by doing a delete + put when status changes (or use
`update_item` which CAN update GSI key attributes).

Actually: DynamoDB `update_item` DOES support updating GSI key attributes.
Build the UpdateExpression to include new GSI2PK/GSI2SK values when status changes.

Return the updated item.

**`get_lead_by_fingerprint(fingerprint: str) -> dict | None`**

Query GSI4 with `GSI4PK = "FP#{fingerprint}"`. Return first result or None.

**`list_leads(source=None, status=None, switching_only=False, min_pain=0, limit=50, last_key=None) -> dict`**

Route to the right GSI:
- `switching_only=True` → GSI3 with `GSI3PK = "SWITCHING#true"`
- `source` provided → GSI1 with `GSI1PK = "SOURCE#{source}"`
- `status` provided → GSI2 with `GSI2PK = "STATUS#{status}"`
- Nothing → GSI2 with `GSI2PK = "STATUS#new"` (sensible default)

Always `ScanIndexForward=False` to get highest pain scores first.

Apply `min_pain` as a FilterExpression: `Attr("pain_score").gte(min_pain)`.

Handle pagination:
- Decode `last_key` from base64 JSON if provided
- Include `ExclusiveStartKey` in query if present
- Encode `LastEvaluatedKey` from response to base64 JSON for return

```python
def _encode_cursor(self, key: dict) -> str:
    return base64.b64encode(json.dumps(key).encode()).decode()

def _decode_cursor(self, cursor: str) -> dict:
    return json.loads(base64.b64decode(cursor.encode()).decode())
```

Return: `{"items": [...], "count": int, "last_evaluated_key": str | None}`

**`put_scrape_run(source: str) -> str`**

Create a scrape run item. Return run_id.

```python
def put_scrape_run(self, source: str) -> str:
    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    self.table.put_item(Item={
        "PK": f"RUN#{run_id}",
        "SK": f"RUN#{run_id}",
        "Type": "SCRAPE_RUN",
        "run_id": run_id,
        "source": source,
        "status": "running",
        "leads_found": 0,
        "leads_new": 0,
        "leads_duplicate": 0,
        "started_at": now,
        "completed_at": None,
        "error": None,
    })
    return run_id
```

**`complete_scrape_run(run_id: str, stats: dict) -> None`**

Update run item with final stats, status, and completed_at timestamp.

**`get_scrape_run(run_id: str) -> dict | None`**

GetItem by PK/SK.

**`list_scrape_runs(source: str = None, limit: int = 20) -> list[dict]`**

Scan with FilterExpression `Type = "SCRAPE_RUN"` and optional source filter.
Sort by `started_at` DESC in Python after fetching (acceptable at MVP volume).

**`get_stats() -> dict`**

GetItem `PK="STATS", SK="STATS"`. Return the stats dict, or defaults if not found.

**`_increment_stats(source: str, is_switching: bool) -> None`**

Atomic counter updates using `UpdateExpression="ADD #total :one, #src :one"`.
Increment: `total_leads`, `leads_{source}`, `leads_new`, and if switching: `switching_count`.

Use `update_item` with `ADD` action. Create the STATS item if it doesn't exist
using `attribute_not_exists(PK)` condition + a separate `put_item` fallback.

---

## PYDANTIC MODELS

File: `app/models.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

SourceType  = Literal["capterra", "g2", "softwareadvice", "getapp", "reddit"]
StatusType  = Literal["new", "contacted", "replied", "converted", "not_interested"]
MethodType  = Literal["email", "phone", "facebook", "linkedin"]

class LeadResponse(BaseModel):
    lead_id: str
    source: SourceType
    pain_score: int
    rating: Optional[int] = None
    reviewer_name: Optional[str] = None
    reviewer_role: Optional[str] = None
    company_size: Optional[str] = None
    business_name: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    mentions_switching: bool
    mentions_data_hostage: bool
    mentions_support: bool
    mentions_pricing: bool
    raw_complaint: Optional[str] = None
    full_review_text: Optional[str] = None
    outreach_status: StatusType
    outreach_method: Optional[MethodType] = None
    outreach_date: Optional[str] = None
    outreach_notes: Optional[str] = None
    follow_up_date: Optional[str] = None
    source_url: Optional[str] = None
    scraped_at: str
    created_at: str
    updated_at: str

class LeadListResponse(BaseModel):
    items: list[LeadResponse]
    count: int
    last_evaluated_key: Optional[str] = None  # base64-encoded cursor

class LeadUpdate(BaseModel):
    outreach_status: Optional[StatusType] = None
    outreach_method: Optional[MethodType] = None
    outreach_notes: Optional[str] = None
    follow_up_date: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None

class ScrapeRequest(BaseModel):
    source: Literal["capterra", "g2", "softwareadvice", "getapp", "reddit", "all"]
    max_pages: Optional[int] = Field(None, ge=1, le=20)

class ScrapeRunResponse(BaseModel):
    run_id: str
    source: str
    status: str
    leads_found: int
    leads_new: int
    leads_duplicate: int
    started_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None

class StatsResponse(BaseModel):
    total_leads: int
    by_status: dict[str, int]
    by_source: dict[str, int]
    pain_distribution: dict[str, int]  # "9-10", "7-8", "5-6", "3-4"
    switching_count: int
    data_hostage_count: int
    owner_role_count: int
    enriched_count: int
    converted_count: int
```

---

## AUTH

File: `app/auth.py`

```python
from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from app.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def require_api_key(api_key: str = Security(api_key_header)):
    if not api_key or api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key",
        )
```

Apply to write endpoints only: `POST /scrape/run`, `PATCH /leads/{id}`,
`POST /leads/{id}/enrich`. Read endpoints are open.

---

## FASTAPI APP

File: `app/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from app.routers import leads, scrape, stats
from app.config import settings

app = FastAPI(
    title="SwitchKit Lead Capture API",
    description="Automated lead pipeline for exitroutes.com",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(leads.router,  prefix="/leads",  tags=["leads"])
app.include_router(scrape.router, prefix="/scrape", tags=["scrape"])
app.include_router(stats.router,  prefix="/stats",  tags=["stats"])

@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "service": "switchkit-leads", "version": "2.0.0"}

# Lambda handler (ignored when running locally with uvicorn)
handler = Mangum(app)
```

---

## API ENDPOINTS

### Leads router — `app/routers/leads.py`

#### `GET /leads`

Query params:
- `source: SourceType | None` — filter by platform
- `status: StatusType` — default `"new"`
- `min_pain: int` — default `0`, range `0–10`
- `switching_only: bool` — default `False`
- `limit: int` — default `50`, max `200`
- `cursor: str | None` — pagination cursor from previous response

Response: `LeadListResponse`

Sorted by `pain_score` DESC. If `switching_only=True`, takes priority over other filters.

#### `GET /leads/{lead_id}`

Response: `LeadResponse` (all fields including `full_review_text`)
Raises 404 if not found.

#### `PATCH /leads/{lead_id}`

Requires API key.
Body: `LeadUpdate` (all fields optional)
Response: Updated `LeadResponse`

Use case: Steven has called a lead and marks them as contacted with a note.

#### `POST /leads/{lead_id}/enrich`

Requires API key.
Triggers enrichment for one lead. Looks up `business_name` → finds website + phone.
Updates the lead item in DynamoDB.
Returns updated `LeadResponse`.
Returns 400 if `business_name` is null (can't enrich without it).

#### `GET /leads/export/csv`

Note: define this route BEFORE `/{lead_id}` in the router to avoid path conflict.

Query params: same as `GET /leads`
Response: `StreamingResponse` with `text/csv` content type and
`Content-Disposition: attachment; filename="switchkit-leads-{date}.csv"` header.

Columns (in order):
```
lead_id, pain_score, source, rating, reviewer_name, reviewer_role, company_size,
business_name, website, phone, email, city, state,
mentions_switching, mentions_data_hostage, mentions_support, mentions_pricing,
raw_complaint, source_url, outreach_status, outreach_method, outreach_notes,
follow_up_date, scraped_at, created_at, suggested_script
```

`suggested_script` logic:
```python
def get_suggested_script(lead: dict) -> str:
    if lead.get("mentions_data_hostage"):
        return "Email script A — data hostage angle"
    if lead.get("mentions_switching") and lead.get("phone"):
        return "Call first — switcher with phone on file"
    if lead.get("mentions_switching"):
        return "Email script B — switching intent"
    if lead.get("mentions_pricing"):
        return "Email script C — pricing frustration"
    return "Email script D — general dissatisfaction"
```

---

### Scrape router — `app/routers/scrape.py`

#### `POST /scrape/run`

Requires API key.
Body: `ScrapeRequest`

**Scraping is slow (2–10 minutes). Run in background.**

```python
from fastapi import BackgroundTasks

@router.post("/run", status_code=202)
async def trigger_scrape(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
    db: DynamoClient = Depends(get_db),
    _: None = Depends(require_api_key),
):
    run_id = db.put_scrape_run(request.source)
    background_tasks.add_task(
        execute_scrape, run_id, request.source, request.max_pages, db
    )
    return {"run_id": run_id, "status": "running",
            "message": f"Scrape started for source: {request.source}",
            "poll_url": f"/scrape/runs/{run_id}"}
```

`execute_scrape` function: instantiate the right scraper(s), call `run()`, update the run record.

#### `GET /scrape/runs`

Query param: `source: str | None`, `limit: int = 20`
Response: list of `ScrapeRunResponse`, sorted by `started_at` DESC

#### `GET /scrape/runs/{run_id}`

Response: `ScrapeRunResponse`
Use case: poll after triggering a scrape to check completion.

---

### Stats router — `app/routers/stats.py`

#### `GET /stats`

Response: `StatsResponse`

Fetch the STATS item from DynamoDB. For fields not in the stats item
(like `pain_distribution`), run a lightweight scan with projection.
Cache the result for 60 seconds in memory (simple `time.time()` check) to avoid
hammering DynamoDB on repeated calls.

---

## DEPENDENCY INJECTION

Use FastAPI `Depends` for the DynamoDB client:

```python
# app/db/dynamo.py
_client: DynamoClient | None = None

def get_db() -> DynamoClient:
    global _client
    if _client is None:
        _client = DynamoClient()
    return _client
```

Use in routers: `db: DynamoClient = Depends(get_db)`

---

## CONFIG

File: `app/config.py`

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # AWS
    AWS_REGION: str = "us-east-1"
    DYNAMO_TABLE_NAME: str = "switchkit-leads"
    DYNAMO_ENDPOINT_URL: str | None = None  # "http://localhost:8000" for local DynamoDB

    # API security
    API_KEY: str = "dev-key-change-in-production"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "https://exitroutes.com"]

    # Scraper behavior
    SCRAPE_DELAY_SECONDS: float = 3.0
    MAX_RETRIES: int = 2
    MIN_PAIN_SCORE: int = 3  # Don't store leads below this threshold

    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = {"env_file": ".env"}

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()

# ─── Keyword config ───────────────────────────────────────────────────────────

HOT_KEYWORDS = [
    "data hostage", "holding our data", "can't switch", "impossible to leave",
    "leaving fieldroutes", "leaving pestroutes", "switching from", "cancel",
    "canceling", "cancellation", "data export", "data backup", "incomplete backup",
    "$500", "500 dollars", "data migration", "get my data out", "can't get out",
    "trapped", "locked in", "switching to gorilladesk", "switching to jobber",
]

WARM_KEYWORDS = [
    "support", "no one answers", "no response", "switching", "looking for alternative",
    "alternative to", "replace", "better option", "leaving", "frustrated",
    "disappointed", "expensive", "price increase", "not worth it",
]

PAIN_WEIGHTS = {
    "rating_1_star":          4,
    "rating_2_star":          2,
    "rating_3_star":          1,
    "mentions_data_hostage":  4,
    "mentions_switching":     3,
    "mentions_support":       1,
    "mentions_pricing":       1,
    "reviewer_is_owner":      2,
}

REVIEW_SOURCES = {
    "capterra": {
        "base_url":       "https://www.capterra.com/p/146076/FieldRoutes/reviews/",
        "max_pages":      15,
        "delay_seconds":  3,
    },
    "g2": {
        "base_url":       "https://www.g2.com/products/fieldroutes-a-servicetitan-company/reviews",
        "max_pages":      10,
        "delay_seconds":  4,
    },
    "softwareadvice": {
        "base_url":       "https://www.softwareadvice.com/field-service/pestroutes-profile/reviews/",
        "max_pages":      10,
        "delay_seconds":  3,
    },
    "getapp": {
        "base_url":       "https://www.getapp.com/industries-software/a/pestroutes/reviews/",
        "max_pages":      8,
        "delay_seconds":  3,
    },
}

REDDIT_TARGETS = [
    {
        "subreddit":    "pestcontrol",
        "search_terms": ["FieldRoutes", "PestRoutes", "software", "switching"],
    },
    {
        "subreddit":    "smallbusiness",
        "search_terms": ["FieldRoutes", "PestRoutes", "pest control software"],
    },
    {
        "subreddit":    "lawncare",
        "search_terms": ["FieldRoutes", "PestRoutes"],
    },
]
```

---

## BASE SCRAPER

File: `app/scrapers/base.py`

```python
from abc import ABC, abstractmethod
import time, random, logging, requests
from app.db.dynamo import DynamoClient
from app.config import settings

class BaseScraper(ABC):
    source_name: str = ""

    def __init__(self, db: DynamoClient):
        self.db = db
        self.logger = logging.getLogger(f"scraper.{self.source_name}")
        self.session = requests.Session()
        self.session.headers.update(self._random_user_agent())

    @abstractmethod
    def scrape(self, max_pages: int = None) -> list[dict]:
        """Fetch raw data. Return list of raw dicts."""
        pass

    @abstractmethod
    def parse_raw(self, raw: dict) -> dict | None:
        """Parse raw dict → contacts schema dict. Return None to skip."""
        pass

    def run(self, run_id: str, max_pages: int = None) -> dict:
        """Full scrape → parse → store cycle. Updates run record throughout."""
        stats = {"leads_found": 0, "leads_new": 0, "leads_duplicate": 0}
        try:
            raw_leads = self.scrape(max_pages=max_pages)
            stats["leads_found"] = len(raw_leads)

            for raw in raw_leads:
                parsed = self.parse_raw(raw)
                if not parsed:
                    continue
                result = self.db.put_lead(parsed)
                if result:
                    stats["leads_new"] += 1
                else:
                    stats["leads_duplicate"] += 1

            self.db.complete_scrape_run(run_id, {**stats, "status": "completed"})
        except Exception as e:
            self.logger.error(f"Scrape failed: {e}", exc_info=True)
            self.db.complete_scrape_run(run_id, {
                **stats, "status": "failed", "error": str(e)
            })
            raise

        self.logger.info(
            f"{self.source_name}: found={stats['leads_found']} "
            f"new={stats['leads_new']} dup={stats['leads_duplicate']}"
        )
        return stats

    def polite_delay(self, base: float = None):
        delay = base or settings.SCRAPE_DELAY_SECONDS
        time.sleep(delay + random.uniform(0.5, 2.0))

    def safe_get(self, url: str, **kwargs) -> requests.Response | None:
        """GET with retry on 429. Returns None on 403/persistent failure."""
        for attempt in range(settings.MAX_RETRIES):
            try:
                resp = self.session.get(url, timeout=15, **kwargs)
                if resp.status_code == 200:
                    return resp
                if resp.status_code == 429:
                    wait = 30 * (attempt + 1)
                    self.logger.warning(f"Rate limited. Waiting {wait}s...")
                    time.sleep(wait)
                    continue
                if resp.status_code == 403:
                    self.logger.warning(f"403 Forbidden on {url}. Skipping.")
                    return None
                self.logger.warning(f"HTTP {resp.status_code} on {url}")
                return None
            except requests.RequestException as e:
                self.logger.error(f"Request error: {e}")
                time.sleep(5)
        return None

    @staticmethod
    def _random_user_agent() -> dict:
        agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        ]
        import random
        return {"User-Agent": random.choice(agents)}
```

---

## INDIVIDUAL SCRAPERS

### Capterra — `app/scrapers/capterra.py`

Use `requests` + `BeautifulSoup4`. Paginate via `?page=N`.

Fields to extract from each review:
- `reviewer_name` — first name + last initial (e.g. "Dallas Q.")
- `reviewer_role` — job title shown on review card
- `company_size` — "2-10 employees" metadata
- `rating` — integer 1–5 (count filled stars or parse aria-label)
- `review_date` — date string, convert to ISO
- `cons_text` — the "Cons" section text
- `pros_text` — the "Pros" section text
- `switching_reason` — "Reasons for switching to FieldRoutes" if present
- `source_url` — URL of the page (not individual review permalink)
- `source_id` — any unique ID found in HTML (data attribute or anchor)

Stop paginating when a page returns no reviews.

Only pass reviews to `parse_raw` if: rating ≤ 3 OR cons_text/review_text
contains any HOT_KEYWORDS or WARM_KEYWORDS (check lowercased).

### G2 — `app/scrapers/g2.py`

Same structure. G2's review page has:
- "What do you like best?" = pros
- "What do you dislike?" = cons
- "Recommendations to others" = optional extra context

G2 uses heavier JS rendering. Try the HTML endpoint first.
Fallback: try `https://www.g2.com/products/fieldroutes-a-servicetitan-company/reviews.json?page=N`
which often returns JSON even when the HTML page blocks.

If the JSON endpoint works, parse the JSON directly (no BS4 needed for that path).

### SoftwareAdvice — `app/scrapers/softwareadvice.py`

Same parent company as Capterra (Gartner). Very similar HTML structure.
Extra field: "Used the software for: X years" — extract this as `tenure`.
Long tenure + low rating = higher pain signal. Add 1 point to pain score if tenure > 1 year.

### GetApp — `app/scrapers/getapp.py`

Same parent as Capterra. Similar HTML.
Extra field: "Value for money" sub-rating (1–5). Extract as `value_rating`.
Low value_rating + pricing complaint = confirmed pricing frustration.

### Reddit — `app/scrapers/reddit.py`

Use the public Reddit JSON API — no auth required for public posts.

```
GET https://www.reddit.com/r/{subreddit}/search.json
    ?q={query}&restrict_sr=1&sort=new&limit=100&t=year
```

For each result (both posts and their top comments):
- Extract: `post_id`, `title`, `selftext`, `author`, `subreddit`,
  `url`, `created_utc`, `score`, `num_comments`
- Also fetch top comments for high-scoring posts:
  `GET https://www.reddit.com/r/{sub}/comments/{post_id}.json`

Add `User-Agent: "python:exitroutes-leads:v1.0 (by /u/your_reddit_username)"`
Reddit's API requires a descriptive User-Agent.

Filter: keep only items where title + selftext contains HOT_KEYWORDS or WARM_KEYWORDS.
`business_name` will be null for Reddit leads. `reviewer_name` = Reddit username.

---

## REVIEW PARSER

File: `app/parsers/review_parser.py`

```python
import hashlib, re
from datetime import datetime, timezone
from app.config import HOT_KEYWORDS, WARM_KEYWORDS, PAIN_WEIGHTS, settings

class ReviewParser:

    def calculate_pain_score(self, data: dict) -> int:
        score = 0
        rating = data.get("rating") or 5

        if rating == 1:   score += PAIN_WEIGHTS["rating_1_star"]
        elif rating == 2: score += PAIN_WEIGHTS["rating_2_star"]
        elif rating == 3: score += PAIN_WEIGHTS["rating_3_star"]

        text = " ".join(filter(None, [
            data.get("cons_text", ""),
            data.get("full_review_text", ""),
            data.get("switching_reason", ""),
        ])).lower()

        if any(k in text for k in [
            "data hostage", "holding our data", "impossible to leave",
            "can't switch", "data export", "incomplete backup", "$500",
        ]):
            score += PAIN_WEIGHTS["mentions_data_hostage"]

        if any(k in text for k in [
            "switching to", "switching from", "cancel", "leaving", "switching",
        ]):
            score += PAIN_WEIGHTS["mentions_switching"]

        if any(k in text for k in [
            "no support", "no one answers", "support is terrible",
            "can't get help", "no response",
        ]):
            score += PAIN_WEIGHTS["mentions_support"]

        if any(k in text for k in [
            "price", "expensive", "cost", "pricing", "price increase",
        ]):
            score += PAIN_WEIGHTS["mentions_pricing"]

        role = (data.get("reviewer_role") or "").lower()
        if any(r in role for r in ["owner", "operator", "ceo", "president", "founder"]):
            score += PAIN_WEIGHTS["reviewer_is_owner"]

        return min(score, 10)

    def detect_signals(self, data: dict) -> dict:
        text = " ".join(filter(None, [
            data.get("cons_text", ""),
            data.get("full_review_text", ""),
        ])).lower()

        return {
            "mentions_data_hostage": any(k in text for k in [
                "data hostage", "holding our data", "impossible to leave",
                "data export", "incomplete backup", "$500", "500 dollars",
            ]),
            "mentions_switching": any(k in text for k in [
                "switching to", "switching from", "cancel", "leaving",
                "switch to", "switch from", "gorilladesk", "jobber",
            ]),
            "mentions_support": any(k in text for k in [
                "no support", "no one answers", "support is terrible",
                "can't get help", "no response", "never calls back",
            ]),
            "mentions_pricing": any(k in text for k in [
                "price", "expensive", "cost", "pricing", "price increase",
                "overpriced", "too much",
            ]),
        }

    def extract_key_sentences(self, text: str, max_sentences: int = 3) -> str:
        """Return the top N most complaint-relevant sentences."""
        if not text:
            return ""
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        all_keywords = HOT_KEYWORDS + WARM_KEYWORDS

        def sentence_score(s: str) -> int:
            s_lower = s.lower()
            return sum(1 for kw in all_keywords if kw in s_lower)

        ranked = sorted(sentences, key=sentence_score, reverse=True)
        top = [s for s in ranked[:max_sentences] if sentence_score(s) > 0]
        return " ".join(top) if top else sentences[0] if sentences else ""

    def generate_fingerprint(
        self, source: str, reviewer_name: str, business_name: str = None
    ) -> str:
        parts = [source, (reviewer_name or "").lower().strip()]
        if business_name:
            parts.append(business_name.lower().strip())
        return hashlib.md5("|".join(parts).encode()).hexdigest()

    def parse(self, raw: dict, source: str) -> dict | None:
        """
        Convert raw scraper output → contacts schema dict.
        Returns None if pain_score < MIN_PAIN_SCORE.
        """
        pain_score = self.calculate_pain_score(raw)
        if pain_score < settings.MIN_PAIN_SCORE:
            return None

        signals  = self.detect_signals(raw)
        raw_text = raw.get("cons_text") or raw.get("full_review_text") or ""
        fp       = self.generate_fingerprint(
            source,
            raw.get("reviewer_name", ""),
            raw.get("business_name"),
        )

        return {
            "source":            source,
            "source_url":        raw.get("source_url"),
            "source_id":         raw.get("source_id"),
            "scraped_at":        datetime.now(timezone.utc).isoformat(),
            "business_name":     raw.get("business_name"),
            "reviewer_name":     raw.get("reviewer_name"),
            "reviewer_role":     raw.get("reviewer_role"),
            "company_size":      raw.get("company_size"),
            "rating":            raw.get("rating"),
            "pain_score":        pain_score,
            "raw_complaint":     self.extract_key_sentences(raw_text),
            "full_review_text":  raw_text,
            "fingerprint":       fp,
            "outreach_status":   "new",
            **signals,
        }
```

---

## ENRICHER

File: `app/enricher.py`

```python
import re, logging
import requests
from bs4 import BeautifulSoup
from googlesearch import search

logger = logging.getLogger(__name__)

PHONE_RE = re.compile(r'(\+?1[-.\s]?)?(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})')
SKIP_DOMAINS = {"capterra.com", "g2.com", "yelp.com", "yellowpages.com",
                "bbb.org", "facebook.com", "linkedin.com", "google.com"}

def enrich_lead(business_name: str) -> dict:
    """
    Look up a business by name and return {website, phone, city, state}.
    All fields may be None if not found. Never raises — returns empty dict on failure.
    """
    result = {"website": None, "phone": None, "city": None, "state": None}
    if not business_name:
        return result

    try:
        query = f"{business_name} pest control"
        urls  = list(search(query, num_results=5, lang="en"))
        website = next(
            (u for u in urls if not any(d in u for d in SKIP_DOMAINS)),
            None,
        )
        if not website:
            return result
        result["website"] = website

        resp = requests.get(website, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (compatible; SwitchKit-Enricher/1.0)"
        })
        if resp.status_code != 200:
            return result

        soup = BeautifulSoup(resp.text, "lxml")

        # Phone: prefer tel: links, fall back to text regex
        tel_link = soup.find("a", href=re.compile(r"^tel:"))
        if tel_link:
            raw_phone = tel_link.get("href", "").replace("tel:", "").strip()
        else:
            text  = soup.get_text()
            match = PHONE_RE.search(text)
            raw_phone = match.group(0) if match else None

        if raw_phone:
            result["phone"] = _normalize_phone(raw_phone)

        # City/state from structured address or footer text
        address_tag = (
            soup.find("address") or
            soup.find(attrs={"itemprop": "address"}) or
            soup.find(class_=re.compile(r"address|location|footer", re.I))
        )
        if address_tag:
            addr_text = address_tag.get_text(" ", strip=True)
            city, state = _parse_city_state(addr_text)
            result["city"]  = city
            result["state"] = state

    except Exception as e:
        logger.warning(f"Enrichment failed for '{business_name}': {e}")

    return result


def _normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("1") and len(digits) == 11:
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return raw  # return as-is if we can't normalize


def _parse_city_state(text: str) -> tuple[str | None, str | None]:
    # Match "City, ST" or "City, State"
    pattern = re.compile(
        r'([A-Z][a-zA-Z\s]+),\s*([A-Z]{2})\b'
    )
    match = pattern.search(text)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return None, None
```

---

## DEDUPLICATOR

File: `app/deduplicator.py`

Primary dedup: fingerprint uniqueness enforced via GSI4 query in `put_lead`.

Secondary: fuzzy dedup to catch near-duplicates that slipped through:

```python
from difflib import SequenceMatcher
from app.db.dynamo import DynamoClient

def find_fuzzy_duplicates(db: DynamoClient, threshold: float = 0.85) -> list[dict]:
    """
    Scan all leads. Return list of potential duplicate pairs.
    Use sparingly — runs a full scan.
    """
    # Scan with projection: lead_id, business_name, reviewer_name, source
    # Group by source, compare business_name similarity within each source
    # Return pairs where similarity > threshold
    # Format: [{"lead_id_1": ..., "lead_id_2": ..., "similarity": 0.92}, ...]
    pass  # implement using DynamoDB scan + Python groupby + SequenceMatcher
```

Expose this as `GET /leads/duplicates` endpoint (read-only, no auth required).

---

## REQUIREMENTS.TXT

```
# API
fastapi>=0.110
uvicorn[standard]>=0.27
mangum>=0.17         # AWS Lambda adapter

# Database
boto3>=1.34

# Validation
pydantic>=2.6
pydantic-settings>=2.2

# Scraping
requests>=2.31
beautifulsoup4>=4.12
lxml>=5.1
googlesearch-python>=1.2

# Dev / testing
pytest>=8.0
moto[dynamodb]>=5.0
httpx>=0.27          # For TestClient in FastAPI tests
python-dotenv>=1.0
```

---

## .ENV.EXAMPLE

```bash
# AWS
AWS_REGION=us-east-1
DYNAMO_TABLE_NAME=switchkit-leads
# For local dev with DynamoDB Local or moto:
# DYNAMO_ENDPOINT_URL=http://localhost:8000

# API
API_KEY=change-me-in-production
ALLOWED_ORIGINS=["http://localhost:3000","https://exitroutes.com"]

# Scraping
SCRAPE_DELAY_SECONDS=3.0
MAX_RETRIES=2
MIN_PAIN_SCORE=3

# Logging
LOG_LEVEL=INFO
```

---

## MAKEFILE

```makefile
.PHONY: dev test lint

dev:
	uvicorn app.main:app --reload --port 8000

test:
	pytest tests/ -v

lint:
	ruff check app/ tests/

install:
	pip install -r requirements.txt
```

---

## TESTING WITH MOTO

File: `tests/conftest.py`

```python
import pytest, boto3
from moto import mock_aws
from fastapi.testclient import TestClient
from app.main import app
from app.db.dynamo import DynamoClient, get_db
from app.db.schema import create_table_if_not_exists
from app.config import settings

@pytest.fixture(scope="function")
def mock_dynamo():
    with mock_aws():
        resource = boto3.resource("dynamodb", region_name="us-east-1")
        create_table_if_not_exists(resource, settings.DYNAMO_TABLE_NAME)
        yield resource

@pytest.fixture
def db(mock_dynamo):
    client = DynamoClient()
    return client

@pytest.fixture
def api_client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()

def make_lead(**overrides) -> dict:
    """Factory for test lead data."""
    base = {
        "source": "capterra",
        "source_url": "https://capterra.com/test",
        "source_id": "test-123",
        "business_name": "Test Pest Co",
        "reviewer_name": "John O.",
        "reviewer_role": "Owner",
        "company_size": "2-10 employees",
        "rating": 1,
        "pain_score": 8,
        "mentions_switching": True,
        "mentions_data_hostage": True,
        "mentions_support": False,
        "mentions_pricing": False,
        "raw_complaint": "They want $500 for an incomplete backup.",
        "full_review_text": "They want $500 for an incomplete backup. Impossible to leave.",
        "fingerprint": "test-fingerprint-abc123",
        "outreach_status": "new",
        "scraped_at": "2026-04-01T10:00:00Z",
    }
    return {**base, **overrides}
```

File: `tests/test_parser.py`

Test the pain scorer with 5 representative review texts:
1. Data hostage complaint by owner → expect score ≥ 8
2. Switching mention only → expect score 5–7
3. Pricing frustration by office manager → expect score 3–5
4. Positive review → expect score < MIN_PAIN_SCORE (filtered out)
5. Support complaint by owner → expect score 4–6

File: `tests/test_dynamo.py`

- `test_put_lead_returns_id` — new lead → returns lead_id string
- `test_put_lead_dedup` — same fingerprint → second put returns None
- `test_get_lead` — put then get → fields match
- `test_update_outreach_status` — update status → GSI2PK updated
- `test_list_by_source` — put 3 capterra + 2 g2 → query GSI1 for capterra returns 3
- `test_list_by_status` — put 4 new + 1 contacted → query new returns 4
- `test_pain_sort_order` — put leads with pain 3,7,9 → list returns 9,7,3

File: `tests/test_leads_api.py`

- `test_get_leads_empty` — empty table → 200 with items=[]
- `test_get_lead_not_found` → 404
- `test_patch_lead_status` — valid API key → 200, status updated
- `test_patch_lead_no_auth` → 403
- `test_export_csv` — put 3 leads → GET /leads/export/csv → valid CSV with 3 rows

---

## BUILD ORDER

1. `app/db/schema.py` — key builders + table creation helper
2. `app/db/dynamo.py` — DynamoClient with all methods
3. `tests/conftest.py` + `tests/test_dynamo.py` — test the DB layer in isolation with moto
4. `app/config.py` — settings + keyword config
5. `app/models.py` — all Pydantic models
6. `app/auth.py` — API key dependency
7. `app/parsers/review_parser.py` + `tests/test_parser.py` — pain scorer, no HTTP
8. `app/scrapers/base.py` — abstract base
9. `app/scrapers/capterra.py` — first real scraper
10. `app/routers/leads.py` + `app/routers/scrape.py` + `app/routers/stats.py`
11. `app/main.py` — wire everything together
12. `tests/test_leads_api.py` — integration tests via TestClient
13. `app/scrapers/g2.py`, `softwareadvice.py`, `getapp.py`, `reddit.py`
14. `app/parsers/reddit_parser.py`
15. `app/enricher.py`
16. `app/deduplicator.py`
17. `Makefile` + `README.md`

---

## WHAT NOT TO BUILD IN THIS SESSION

- No UI — the API is the product; a frontend comes later
- No email sending — outreach stays manual for now
- No Facebook or LinkedIn scraping — login required, ToS issues
- No scheduler — run scrapes via `POST /scrape/run` manually or via cron hitting the API
- No auth beyond the simple API key — no JWT, no user accounts

---

## FIRST THING TO DO

Start with `app/db/schema.py` and `app/db/dynamo.py`.
Write `tests/test_dynamo.py` before any other code and get all DB tests passing
against moto. This validates the single-table design before anything depends on it.

Ask before making any assumptions about the DynamoDB schema or GSI design.
