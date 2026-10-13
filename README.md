# MunchMate — Group Ordering Made Effortless 🍕🥤

> **The modern collaborative late-night snack & grocery group order manager built for college students, hostel residents, roommates, and late-night study groups.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16%20App%20Router-black?style=flat&logo=next.js&logoColor=white)](https://nextjs.org)
[![TailwindCSS](https://img.shields.io/badge/Tailwind-CSS-38B2AC?style=flat&logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 📌 The Problem MunchMate Solves

In hostels, PGs, and apartments, late-night food ordering is historically frustrating:
1. **Host Burden**: One host collects 15 chaotic WhatsApp messages and screenshots.
2. **Math Headaches**: Splitting delivery fees (₹40), platform fees (₹10), and packaging across different people leaves fractions and odd paise.
3. **Chasing Roommates for Money**: The host pays out of pocket and spends days asking friends to send money on GPay.
4. **Order Mistakes**: Forgotten items and missing quantities cause disputes.

### **The MunchMate Solution**
- **One Shared Link**: Host creates an order pool in 10 seconds. Friends join directly through the link without being forced to create accounts.
- **Live Collaborative Cart**: Roommates add items (Maggi, Red Bull, chips, sweets, etc.) in real time via WebSockets.
- **Deterministic Paise-Level Bill Splitter**: Calculates each person's exact share in integer paise using the Hamilton-Hare method with zero rounding discrepancies.
- **Personalized Exact-Amount UPI QR Codes**: Each roommate scans their unique QR code or uses the mobile intent link to pay their share directly.
- **Host Dashboard & Auto Receipts**: Host sees live payment progress, can confirm manual UPI payments, accesses the consolidated shopping list grouped by product, and records merchant placement on Blinkit, Zepto, or Campus Canteens.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph Frontend["Frontend (Next.js 16 + React 19 + TypeScript)"]
        Landing["Landing & Discover (/discover)"]
        CreateGroup["Create Group Order (/create)"]
        JoinGroup["Join via Code (/join)"]
        LiveCart["Live Group Cart & Menu (/group/[code])"]
        Checkout["Smart Bill Split & UPI QR (/group/[code]/checkout)"]
        Receipt["Digital Receipt (/receipt/[token])"]
        Dashboard["Host Dashboard (/group/[code]/dashboard)"]
        Summary["Consolidated Shopping List (/group/[code]/summary)"]
    end

    subgraph Backend["Backend (FastAPI + SQLAlchemy 2.0)"]
        AuthRouter["/api/v1/auth (JWT & Guest Sessions)"]
        GroupRouter["/api/v1/groups (Pools & Locking)"]
        CartRouter["/api/v1/groups/[id]/cart (Items)"]
        BillRouter["/api/v1/groups/[id]/billing (Integer Paise Engine)"]
        PayRouter["/api/v1/payments (UPI QR, Razorpay & Demo)"]
        RcptRouter["/api/v1/receipts (Digital Receipts)"]
        OrderRouter["/api/v1/orders (Merchant Tracking)"]
        WSService["/api/v1/ws (WebSocket Collaboration)"]
    end

    subgraph Storage["Persistent Database & Gateways"]
        DB[("SQLite (Dev) / PostgreSQL (Prod)")]
        UPI["NPCI Standard UPI QR (upi://pay)"]
        Gateway["Razorpay Gateway (Optional/Live)"]
    end

    LiveCart <-->|WebSocket Events| WSService
    LiveCart -->|REST API| CartRouter
    Checkout -->|Verify Payment| PayRouter
    PayRouter -->|Generate QR| UPI
    PayRouter -->|Signatures| Gateway
    CartRouter --> BillRouter
    BillRouter --> DB
    PayRouter --> DB
    RcptRouter --> DB
```

---

## 🛠️ Tech Stack

| Layer | Technologies |
|---|---|
| **Frontend** | Next.js 16 (App Router), React 19, TypeScript (Strict Mode), Tailwind CSS, Lucide Icons, Framer Motion, Canvas Confetti |
| **Backend** | Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic |
| **Database** | SQLite (Default for zero-config local run), PostgreSQL (Production ready) |
| **Real-time** | WebSockets (group-scoped event broadcasting) |
| **Payments** | Dynamic NPCI UPI QR code generation, Razorpay HMAC signature verification, Idempotent payment processing, Demo payment simulator |
| **Design** | Warm cream background (`#FAF8F5`), Deep charcoal (`#1A1A1A`), Vibrant tangerine (`#FF5C00`), Plus Jakarta Sans & Outfit typography |

---

## ⚡ Quick Start (Local Development)

### Prerequisites
- **Node.js** v18+ and **npm**
- **Python** 3.11+

### 1. Clone & Set Up Backend

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt email-validator

# Run database seed (Seeds 9 categories and 26 realistic late-night products)
python -c "from app.seed import seed_database; seed_database()"

# Start FastAPI server on port 8000
uvicorn app.main:app --reload --port 8000
```

FastAPI interactive documentation will be available at:
- **Interactive OpenAPI Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

### 2. Set Up & Run Frontend

In a separate terminal:

```bash
cd frontend

# Install dependencies
npm install

# Start Next.js development server on port 3000
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🧪 Automated Test Suite

The backend includes a comprehensive pytest suite covering all business logic, integer paise calculations, payment states, and cart locking:

```bash
cd backend
$env:PYTHONPATH="." ; .\venv\Scripts\pytest -v
```

### Verified Test Suite (15/15 Passing — 100% Pass Rate):
1. `test_auth_and_guest_session_flow` — Friction-free guest session creation and token auth.
2. `test_products_catalog_api` — Product discovery, category search, and availability checks.
3. `test_manual_upi_confirmation_by_host` — Host marks UPI payment received on phone with audit logging and digital receipt issue.
4. `test_unauthorized_non_host_payment_confirmation` — Rejects unauthorized participants trying to approve payments (HTTP 400).
5. `test_demo_payment_failure_scenario` — Simulates bank failure state, safely recording FAILED status without receipt issue.
6. `test_combined_group_summary_receipt_api` — Consolidated order shopping list grouped by item, accessible by UUID and 6-char code.
7. `test_equal_split_deterministic_rounding` — Equal fee division distributes leftover paise deterministically with zero error.
8. `test_proportional_split_policy` — Proportional shared fee allocation using Hamilton-Hare largest remainder algorithm.
9. `test_host_covers_shared_fees` — Policy where host covers delivery/platform fees while friends pay only item costs.
10. `test_cart_locking_behavior` — Locking stops item addition and rejects unauthorized modifications with HTTP 400.
11. `test_group_summary_grouped_products` — Product consolidation aggregates quantities (e.g. 3 Maggi + 2 Maggi = 5 Maggi).
12. `test_upi_qr_generation` — Validates NPCI standard URI (`upi://pay?pa=...&pn=...&am=...&cu=INR`) and base64 PNG generation.
13. `test_payment_idempotency` — Duplicate payment requests return the same record, preventing duplicate charges.
14. `test_demo_payment_verification` — Verified simulation outcomes (SUCCESS, FAILURE, PENDING).
15. `test_razorpay_signature_validation` — Cryptographic HMAC-SHA256 signature verification.

---

## 🏆 Hackathon Judge Walkthrough Script (3 Minutes)

Follow this 5-step flow to experience the entire MunchMate product lifecycle:

1. **Step 1: Create a Group Order**
   - Go to [http://localhost:3000](http://localhost:3000) and click **"Start Group Order"**.
   - Title: `Block B Late Night Maggi Party`, Host: `Aditya`, Room: `B-314`.
   - Click **"Create Group Order & Get Share Link"** — generates a unique 6-character room code (e.g. `XVP0VL`).
2. **Step 2: Add Snacks & Real-Time Sync**
   - Click **"+ Add Snacks"** to open the in-context drawer.
   - Add **Maggi 2-Minute Noodles**, **Red Bull**, and **Buldak 2x Spicy Noodles**.
   - Notice the live subtotal and item counter update instantly.
   - Click **"Invite via WhatsApp"** to preview the prefilled WhatsApp invitation message.
3. **Step 3: Lock Cart & Smart Bill Split**
   - Click **"Lock Cart & Proceed to Split"** — immediately locks additions for everyone.
   - On the Checkout page (`/checkout`), inspect the transparent mathematical breakdown:
     - Item cost + Shared Delivery fee + Platform fee + Taxes = **Exact Payable Share**.
4. **Step 4: Scan Dynamic UPI QR or Demo Pay**
   - View the personalized NPCI UPI QR code generated with the exact paise amount.
   - Click **"Simulate Instant Payment Success"** (Demo Mode).
   - Confetti bursts and automatically redirects to the **Verified Digital Receipt**.
5. **Step 5: Host Command Center & Consolidated Shopping List**
   - On the receipt page, toggle between **"My Individual Receipt"** and **"Consolidated Group Receipt"**.
   - Navigate to the **Host Dashboard** (`/dashboard`):
     - View the live payment progress bar (100% collected).
     - Inspect the **Consolidated Shopping List** (e.g. `Maggi × 4`, `Red Bull × 2`) ready for instant copy.
     - Record the external merchant order on **Blinkit**, **Zepto**, or **Instamart** with ETA timer.

---

## 💰 Smart Bill Splitting Engine

All monetary calculations in MunchMate are performed strictly in **integer paise** (e.g. ₹14.00 = 1400 paise) to prevent floating-point discrepancies.

### Allocation Policies:
1. **`EQUAL_SPLIT` (Default)**:
   - Shared fees (Delivery: ₹40, Platform: ₹10, Packaging: ₹15) are divided equally among active participants.
   - Any remainder paise ($r = \text{Fees} \pmod N$) are deterministically distributed 1 paise each to the first $r$ participants sorted by ID.
2. **`PROPORTIONAL`**:
   - Shared charges are distributed according to each roommate's subtotal ratio using the **Hamilton-Hare Largest Remainder Method**.
3. **`HOST_COVERS`**:
   - Host assumes 100% of delivery, platform, and packaging fees. Roommates pay only their raw items.

**Mathematical Invariant**:
$$\sum_{i=1}^N \text{ParticipantPayable}_i \equiv \text{GrandTotal} \pmod{\text{exact 1 paisa}}$$

---

## 📱 Payment Integration Modes

MunchMate supports three payment modes:

1. **Direct UPI QR (Mode 1)**:
   - Dynamic QR code generated with exact amount in rupees.
   - Deep link intent button: "Open in UPI App" (opens Google Pay, PhonePe, Paytm, CRED directly on mobile).
   - "I Have Paid" flow updates status and allows optional UTR entry.
2. **Demo Simulation Mode (Mode 2)**:
   - Clearly labeled with **DEMO** badge.
   - Instant success, simulated bank delays, or simulated failure testing without real money.
3. **Razorpay Gateway Mode (Mode 3)**:
   - Official Razorpay API integration with HMAC-SHA256 server-side signature verification.

---

## 🚢 Production Deployment Guide

### Deploy Backend (e.g. Render / Railway / Fly.io)
1. Push repository to GitHub.
2. Create a new Web Service pointing to `backend/`.
3. Set Build Command: `pip install -r requirements.txt email-validator`
4. Set Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Configure Environment Variables:
   - `DATABASE_URL`: `postgresql://user:pass@host:5432/dbname`
   - `FRONTEND_URL`: `https://your-frontend.vercel.app`
   - `SECRET_KEY`: `your-production-secret-key`
   - `PAYMENT_MODE`: `demo` or `razorpay`

### Deploy Frontend (Vercel)
1. Import repository on [Vercel](https://vercel.com).
2. Set Root Directory to `frontend`.
3. Framework Preset: **Next.js**.
4. Configure Environment Variables:
   - `NEXT_PUBLIC_API_URL`: `https://your-backend.onrender.com/api/v1`
   - `NEXT_PUBLIC_WS_URL`: `your-backend.onrender.com/api/v1`

---

## 📄 License
MIT License. Built with ❤️ for college students and hostelers everywhere.
#   S w a y a m  
 