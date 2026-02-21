# BlackRock Challenge — REST API

A production-ready Python Flask application for automated retirement savings through expense-based micro-investments

---

## Table of Contents

- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Architecture](#architecture)
- [API Reference](#api-reference)
  - [POST /transactions:parse](#1-post-transactionsparse)
  - [POST /transactions:validator](#2-post-transactionsvalidator)
  - [POST /transactions:filter](#3-post-transactionsfilter)
  - [POST /returns:nps](#4-post-returnsnps)
  - [POST /returns:index](#5-post-returnsindex)
  - [GET /performance](#6-get-performance)
- [Business Logic](#business-logic)
- [Error Codes](#error-codes)

---

## Project Structure

```
BLKHACK/
├── app.py                            
├── requirements.txt
└── app/
│   ├── __init__.py                   
│   ├── models/
│   │   └── schemas.py                
│   ├── utils/
│   │   ├── financial.py              
│   │   ├── time_utils.py             
│   │   └── performance.py            
│   ├── services/
│   │   ├── transaction_service.py    
│   │   ├── validation_service.py     
│   │   ├── temporal_service.py       
│   │   └── return_service.py         
│   └── routes/
│       ├── transactions.py           
│       ├── returns.py                
│       └── performance.py
└── tests/
└── .github/
│       ├── workflows/
└── tests/
├── Dockerfile                            
├── .gitignore                            
├── pytest.ini                            
    
```

---

## Tech Stack

| Dependency | Purpose |
|---|---|
| Python 3.11+ | Runtime |
| Flask 3.x | HTTP framework |
| psutil | Memory usage measurement |
| pytest / pytest-cov | Testing |
| streamlit | UI | 

-- Streamlit & other ui libraries not added in the requirements.txt as not needed for the docker run of flask api app.

---

## Getting Started

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the server

```bash
python app.py
# Listening on http://0.0.0.0:5477
```

### 3. Run with docker

```bash
docker pull ghcr.io/abhijitdutta338/blk-hacking-ind-abhijit-dutta:latest
docker run -it ghcr.io/abhijitdutta338/blk-hacking-ind-abhijit-dutta:latest
```

---

## Architecture

The codebase follows a strict layered architecture — no business logic lives inside route handlers.

```
HTTP Request
    │
    ▼
routes/          ← parse JSON, validate types, return HTTP responses
    │
    ▼
services/        ← all business logic (pure functions, no I/O)
    │
    ▼
models/          ← immutable frozen dataclasses (data containers only)
    │
    ▼
utils/           ← stateless helpers (math, time, system metrics)
```


## API Reference

Base URL: `http://localhost:5477/blackrock/challenge/v1`

All endpoints consume and produce `application/json`.

---

### 1. POST /transactions:parse

Enriches raw expenses with **ceiling** and **remanent**.

- **ceiling** = smallest multiple of 100 ≥ amount
- **remanent** = ceiling − amount

**Request**
```json
{
  "expenses": [
    { "timestamp": "2023-10-12 20:15:30", "amount": 250 },
    { "timestamp": "2023-02-28 15:49:20", "amount": 375 }
  ]
}
```

**Response `200`**
```json
{
  "transactions": [
    { "date": "2023-10-12 20:15:30", "amount": 250.0, "ceiling": 300.0, "remanent": 50.0 },
    { "date": "2023-02-28 15:49:20", "amount": 375.0, "ceiling": 400.0, "remanent": 25.0 }
  ],
  "totalExpense": 625.0,
  "totalCeiling": 700.0,
  "totalRemanent": 75.0
}
```

**curl**
```bash
curl -X POST http://localhost:5477/blackrock/challenge/v1/transactions:parse \
  -H "Content-Type: application/json" \
  -d '{
    "expenses": [
      {"timestamp": "2023-10-12 20:15:30", "amount": 250},
      {"timestamp": "2023-02-28 15:49:20", "amount": 375}
    ]
  }'
```

---

### 2. POST /transactions:validator

Validates enriched transactions 

**Request**
```json
{
  "wage": 50000,
  "transactions": [
    { "date": "2023-02-28 15:49:20", "amount": 375.0, "ceiling": 400.0, "remanent": 25.0 },
    { "date": "2023-02-28 15:49:20", "amount": 100.0, "ceiling": 200.0, "remanent": 100.0 }
  ]
}
```

**Response `200`**
```json
{
  "valid": [
    { "date": "2023-02-28 15:49:20", "amount": 375.0, "ceiling": 400.0, "remanent": 25.0 }
  ],
  "invalid": [
    {
      "date": "2023-02-28 15:49:20", "amount": 100.0, "ceiling": 200.0, "remanent": 100.0,
      "message": "Duplicate timestamp: '2023-02-28 15:49:20'."
    }
  ]
}
```

**curl**
```bash
curl -X POST http://localhost:5477/blackrock/challenge/v1/transactions:validator \
  -H "Content-Type: application/json" \
  -d '{
    "wage": 50000,
    "transactions": [
      {"date": "2023-02-28 15:49:20", "amount": 375.0, "ceiling": 400.0, "remanent": 25.0},
      {"date": "2023-02-28 15:49:20", "amount": 100.0, "ceiling": 200.0, "remanent": 100.0}
    ]
  }'
```

---

### 3. POST /transactions:filter

Accepts raw `{ "date", "amount" }` transactions, then applies temporal constraint rules

**Request**
```json
{
  "q": [{ "fixed": 0, "start": "2023-07-01 00:00:00", "end": "2023-07-31 23:59:59" }],
  "p": [{ "extra": 30, "start": "2023-10-01 00:00:00", "end": "2023-12-31 23:59:59" }],
  "k": [{ "start": "2023-01-01 00:00:00", "end": "2023-12-31 23:59:59" }],
  "transactions": [
    { "date": "2023-02-28 15:49:20", "amount": 375 },
    { "date": "2023-07-15 10:30:00", "amount": 620 },
    { "date": "2023-10-12 20:15:30", "amount": 250 },
    { "date": "2023-10-12 20:15:30", "amount": 250 },
    { "date": "2023-12-17 08:09:45", "amount": -480 }
  ]
}
```

**Response `200`**
```json
{
  "valid": [
    { "date": "2023-02-28 15:49:20", "amount": 375.0, "ceiling": 400.0, "remanent": 25.0, "inKPeriod": true },
    { "date": "2023-10-12 20:15:30", "amount": 250.0, "ceiling": 300.0, "remanent": 80.0, "inKPeriod": true }
  ],
  "invalid": [
    { "date": "2023-10-12 20:15:30", "amount": 250.0, "message": "Duplicate transaction" },
    { "date": "2023-12-17 08:09:45", "amount": -480.0, "message": "Negative amounts are not allowed" }
  ]
}
```

**curl**
```bash
curl -X POST http://localhost:5477/blackrock/challenge/v1/transactions:filter \
  -H "Content-Type: application/json" \
  -d '{
    "q": [{"fixed": 0, "start": "2023-07-01 00:00:00", "end": "2023-07-31 23:59:59"}],
    "p": [{"extra": 30, "start": "2023-10-01 00:00:00", "end": "2023-12-31 23:59:59"}],
    "k": [{"start": "2023-01-01 00:00:00", "end": "2023-12-31 23:59:59"}],
    "transactions": [
      {"date": "2023-02-28 15:49:20", "amount": 375},
      {"date": "2023-07-15 10:30:00", "amount": 620},
      {"date": "2023-10-12 20:15:30", "amount": 250},
      {"date": "2023-10-12 20:15:30", "amount": 250},
      {"date": "2023-12-17 08:09:45", "amount": -480}
    ]
  }'
```

---

### 4. POST /returns:nps

Calculates compound-growth investment returns using the **NPS (National Pension Scheme)** at **7.11% p.a.**, with a tax benefit.

**Request**
```json
{
  "age": 29,
  "wage": 50000,
  "inflation": 5.5,
  "q": [{ "fixed": 0, "start": "2023-07-01 00:00:00", "end": "2023-07-31 23:59:59" }],
  "p": [{ "extra": 25, "start": "2023-10-01 08:00:00", "end": "2023-12-31 19:59:59" }],
  "k": [
    { "start": "2023-01-01 00:00:00", "end": "2023-12-31 23:59:59" },
    { "start": "2023-03-01 00:00:00", "end": "2023-11-31 23:59:59" }
  ],
  "transactions": [
    { "date": "2023-02-28 15:49:20", "amount": 375 },
    { "date": "2023-07-01 21:59:00", "amount": 620 },
    { "date": "2023-10-12 20:15:30", "amount": 250 },
    { "date": "2023-12-17 08:09:45", "amount": 480 }
  ]
}
```

**Response `200`**
```json
{
  "totalTransactionAmount": 1725.0,
  "totalCeiling": 1900.0,
  "savingsByDates": [
    {
      "start": "2023-01-01 00:00:00",
      "end": "2023-12-31 23:59:59",
      "amount": 145.0,
      "profit": 86.88,
      "taxBenefit": 0.0
    },
    {
      "start": "2023-03-01 00:00:00",
      "end": "2023-11-31 23:59:59",
      "amount": 75.0,
      "profit": 44.94,
      "taxBenefit": 0.0
    }
  ]
}
```

**curl**
```bash
curl -X POST http://localhost:5477/blackrock/challenge/v1/returns:nps \
  -H "Content-Type: application/json" \
  -d '{
    "age": 29, "wage": 50000, "inflation": 5.5,
    "q": [{"fixed": 0, "start": "2023-07-01 00:00:00", "end": "2023-07-31 23:59:59"}],
    "p": [{"extra": 25, "start": "2023-10-01 08:00:00", "end": "2023-12-31 19:59:59"}],
    "k": [
      {"start": "2023-01-01 00:00:00", "end": "2023-12-31 23:59:59"},
      {"start": "2023-03-01 00:00:00", "end": "2023-11-31 23:59:59"}
    ],
    "transactions": [
      {"date": "2023-02-28 15:49:20", "amount": 375},
      {"date": "2023-07-01 21:59:00", "amount": 620},
      {"date": "2023-10-12 20:15:30", "amount": 250},
      {"date": "2023-12-17 08:09:45", "amount": 480}
    ]
  }'
```

---

### 5. POST /returns:index

Same as `/returns:nps` but uses the **Index Fund (NIFTY 50)** rate of **14.49% p.a.** with no tax benefit (`taxBenefit` is always `0.0`).

**curl**
```bash
curl -X POST http://localhost:5477/blackrock/challenge/v1/returns:index \
  -H "Content-Type: application/json" \
  -d '{ ... same body as returns:nps ... }'
```

---

### 6. GET /performance

Returns a live system performance snapshot.

**Response `200`**
```json
{
  "time": "0.4213 ms",
  "memory": "42.18 MB",
  "threads": 2
}
```

**curl**
```bash
curl http://localhost:5477/blackrock/challenge/v1/performance
```

---