# Hallo Theo — Architecture

Hallo Theo is an AI copilot for property management. It helps property managers and short-term-rental hosts handle the operational work that lives in their inbox and chat — guest questions, vendor coordination, owner reporting, booking issues — by reading from their property management system (PMS), channel managers, calendars, and messages, then drafting responses, scheduling tasks, and surfacing what needs attention.

_Last refreshed: 2026-05-23._

## System Overview

```mermaid
graph TB
    subgraph Clients
        WEB["Web Browser<br/>React SPA"]
        WA["WhatsApp Bot<br/>(Twilio / Baileys)"]
        SLK["Slack Bot<br/>(Bolt SDK)"]
    end

    subgraph Backend["FastAPI Backend"]
        API[REST API]
        COPILOT["Copilot Engine<br/>LLM turns + tool use"]
        RAG["RAG Service<br/>property knowledge base"]
        WORKER["Background Workers<br/>sync + reminders"]
        SCHED["Scheduler<br/>daily briefings"]
    end

    subgraph External
        LLM["Anthropic Claude<br/>(Opus / Sonnet / Haiku)"]
        EMBED["Embedding model<br/>(e.g. voyage-3)"]
        PMS["PMS<br/>(Hostaway / Guesty / Smoobu)"]
        CHANMGR["Channel Manager<br/>(Airbnb, Booking.com, VRBO)"]
        CAL["Google / Apple Calendar"]
        SMS["SMS / WhatsApp gateway<br/>(Twilio)"]
        EMAIL["Email gateway<br/>(Postmark / SES)"]
    end

    DB[(PostgreSQL 14+<br/>+ pgvector)]

    WEB -->|HTTPS| API
    WA -->|webhook| API
    SLK -->|events| API

    API --> COPILOT
    COPILOT --> RAG
    COPILOT --> LLM
    RAG --> EMBED
    RAG --> DB
    COPILOT --> DB
    API --> DB

    WORKER --> PMS
    WORKER --> CHANMGR
    WORKER --> CAL
    WORKER --> DB
    SCHED --> COPILOT
    SCHED --> EMAIL

    COPILOT -->|outbound| SMS
    COPILOT -->|outbound| EMAIL
```

## Copilot Turn (LLM + Tools)

```mermaid
sequenceDiagram
    participant User
    participant API as FastAPI
    participant COPILOT as Copilot Engine
    participant RAG as RAG Service
    participant LLM as Claude
    participant DB as PostgreSQL
    participant TOOL as Property tools

    User->>API: POST /api/copilot/turn (message + context)
    API->>COPILOT: run_turn(user_id, message)
    COPILOT->>DB: load conversation history + user prefs
    COPILOT->>RAG: retrieve relevant property docs
    RAG->>DB: pgvector similarity search
    DB-->>RAG: top-k chunks
    RAG-->>COPILOT: context block
    COPILOT->>LLM: messages + system + tools
    loop until LLM returns final answer
        LLM-->>COPILOT: tool_use
        COPILOT->>TOOL: dispatch (PMS / calendar / DB)
        TOOL-->>COPILOT: tool_result
        COPILOT->>LLM: tool_result
    end
    LLM-->>COPILOT: assistant message
    COPILOT->>DB: persist assistant turn
    COPILOT-->>API: response
    API-->>User: 200 OK (SSE stream)
```

## Inbound Message Flow (WhatsApp / Slack)

```mermaid
sequenceDiagram
    participant Guest
    participant Gateway as Twilio / Slack
    participant API as FastAPI
    participant COPILOT as Copilot Engine
    participant Manager as Property Manager

    Guest->>Gateway: message ("AC isn't working in unit 4")
    Gateway->>API: webhook (signed)
    API->>API: verify signature, map to user/property
    API->>COPILOT: classify_and_handle(message)
    alt Auto-reply confident
        COPILOT-->>Gateway: reply (canned + LLM-drafted)
        Gateway-->>Guest: response
    else Needs human
        COPILOT->>Manager: notify (push / digest / inbox card)
        COPILOT-->>Gateway: acknowledgment ("we're on it")
    end
```

## Frontend Architecture

```mermaid
graph TB
    subgraph App["App.tsx (Router + Layout)"]
        ROUTER[Path-based routing]
    end

    subgraph Pages
        LOGIN[Login.tsx]
        DASH["Dashboard.tsx<br/>Today's work, alerts, occupancy"]
        INBOX["Inbox.tsx<br/>Guest + owner conversations"]
        PROPS["Properties.tsx<br/>List + detail"]
        TASKS["Tasks.tsx<br/>Cleanings, maintenance"]
        SETTINGS["Settings.tsx<br/>Integrations + voice"]
    end

    subgraph "Copilot UI"
        CHAT["CopilotChat<br/>SSE streaming"]
        DRAFT["DraftPanel<br/>review + edit AI replies"]
        BRIEF["BriefingCard<br/>daily summary"]
    end

    subgraph "Hooks"
        WSH[useWebSocket]
        COPH[useCopilot]
        INTH[useIntegrations]
        TASKSH[useTasks]
    end

    ROUTER --> LOGIN
    ROUTER --> DASH
    ROUTER --> INBOX
    ROUTER --> PROPS
    ROUTER --> TASKS
    ROUTER --> SETTINGS

    DASH --> BRIEF
    INBOX --> CHAT
    INBOX --> DRAFT
    CHAT --> COPH
    INBOX --> WSH
```

## Backend Module Structure

```mermaid
graph TB
    subgraph "API Layer (src/halloteo/api/)"
        AUTH_API[auth.py]
        COPILOT_API["copilot.py<br/>POST /turn (SSE)"]
        INBOX_API[inbox.py]
        PROP_API[properties.py]
        TASK_API[tasks.py]
        INT_API[integrations.py]
        WH_API["webhooks.py<br/>WhatsApp / Slack / PMS"]
    end

    subgraph "Application Layer (src/halloteo/application/)"
        APP_COPILOT["copilot/<br/>run_turn + tools/ + providers/"]
        APP_INBOX["inbox/<br/>route, classify, reply"]
        APP_BRIEF["briefing/<br/>daily digest generator"]
        APP_SYNC["sync/<br/>PMS + channel manager sync"]
    end

    subgraph "Storage Layer (src/halloteo/storage/)"
        DB_CORE["database.py<br/>asyncpg pool"]
        USR_ST[users.py]
        PROP_ST[properties.py]
        BOOK_ST[bookings.py]
        MSG_ST[messages.py]
        TASK_ST[tasks.py]
        DOC_ST["documents.py<br/>knowledge base + embeddings"]
        CONV_ST["conversations.py<br/>copilot history"]
    end

    subgraph "Service Modules"
        LLM_SVC["llm/<br/>client, prompt_templates,<br/>tool_registry"]
        RAG_SVC["rag/<br/>retriever, chunker, embedder"]
        INT_SVC["integrations/<br/>hostaway, guesty, airbnb,<br/>booking, gcal"]
        MSG_SVC["messaging/<br/>twilio, slack, postmark"]
        AUTH_SVC[auth/jwt + sessions]
    end

    COPILOT_API --> APP_COPILOT
    INBOX_API --> APP_INBOX
    WH_API --> APP_INBOX
    APP_COPILOT --> LLM_SVC
    APP_COPILOT --> RAG_SVC
    APP_COPILOT --> CONV_ST
    APP_COPILOT --> MSG_ST
    APP_INBOX --> LLM_SVC
    APP_INBOX --> MSG_ST
    APP_INBOX --> MSG_SVC
    APP_BRIEF --> LLM_SVC
    APP_BRIEF --> BOOK_ST
    APP_SYNC --> INT_SVC
    APP_SYNC --> BOOK_ST
    APP_SYNC --> PROP_ST
    RAG_SVC --> DOC_ST
```

## Data Model (PostgreSQL)

> **Schema baseline** lives in `src/halloteo/storage/schema.sql`; production state is the baseline plus all migrations under `src/halloteo/storage/migrations/`.

```mermaid
erDiagram
    users {
        text id PK
        citext email UK
        text name
        text role "owner|manager|cleaner|staff"
        text password_hash
        timestamptz created_at
        timestamptz last_seen
        text timezone
    }

    properties {
        text id PK
        text owner_id FK
        text name
        text address
        text city
        text country
        int bedrooms
        int max_guests
        text pms_provider "hostaway|guesty|smoobu"
        text pms_external_id
        jsonb amenities
        timestamptz created_at
    }

    bookings {
        text id PK
        text property_id FK
        text guest_name
        citext guest_email
        text guest_phone
        date check_in
        date check_out
        int guest_count
        text channel "airbnb|booking|vrbo|direct"
        text channel_external_id
        text status "confirmed|checked_in|checked_out|cancelled"
        numeric payout_amount
        timestamptz created_at
    }

    messages {
        text id PK
        text user_id FK
        text property_id FK
        text booking_id FK
        text channel "whatsapp|slack|email|sms"
        text direction "in|out"
        citext from_address
        citext to_address
        text body_text
        text body_html
        text status
        timestamptz created_at
    }

    tasks {
        text id PK
        text property_id FK
        text booking_id FK
        text assignee_id FK
        text type "cleaning|maintenance|check_in|check_out|other"
        text status "open|in_progress|done|cancelled"
        text title
        text notes
        timestamptz due_at
        timestamptz completed_at
        timestamptz created_at
    }

    documents {
        text id PK
        text property_id FK
        text kind "house_manual|policy|faq|amenity|other"
        text title
        text body_text
        text source_url
        timestamptz updated_at
    }

    document_chunks {
        text id PK
        text document_id FK
        int chunk_index
        text content
        vector_1024 embedding
        timestamptz created_at
    }

    conversations {
        text id PK
        text user_id FK
        text title
        timestamptz created_at
        timestamptz updated_at
    }

    conversation_messages {
        bigserial id PK
        text conversation_id FK
        text role "user|assistant|tool"
        text content
        jsonb tool_calls
        timestamptz created_at
    }

    integrations {
        text id PK
        text user_id FK
        text kind "pms|channel|calendar|messaging"
        text provider
        text status
        jsonb credentials_encrypted
        timestamptz connected_at
        timestamptz last_synced_at
    }

    sessions {
        text id PK
        text user_id FK
        text refresh_token_jti UK
        timestamptz created_at
        timestamptz expires_at
        timestamptz revoked_at
    }

    users ||--o{ properties : "owns"
    users ||--o{ sessions : "has"
    users ||--o{ conversations : "asks"
    users ||--o{ integrations : "connects"
    properties ||--o{ bookings : "has"
    properties ||--o{ tasks : "schedules"
    properties ||--o{ documents : "describes"
    properties ||--o{ messages : "context"
    bookings ||--o{ messages : "thread"
    bookings ||--o{ tasks : "triggers"
    documents ||--o{ document_chunks : "split into"
    conversations ||--o{ conversation_messages : "has"
```

## Authentication

```mermaid
graph LR
    SIGNUP[Signup] -->|POST /auth/signup| API[auth API]
    API -->|bcrypt hash| DB[(users)]
    LOGIN[Login] -->|POST /auth/signin| API
    API -->|issue| JWT[Access JWT 24h]
    API -->|issue| RJ[Refresh JWT 7d]
    RJ -->|rotate| SESS[(sessions)]
    SESS -->|reuse detected| REVOKE[revoke family]
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **FastAPI + asyncpg + Pydantic v2** | Single async stack; Pydantic v2 for fast validation; minimal magic. |
| **PostgreSQL 14+ with pgvector** | One database for relational data and embeddings — no separate vector DB during the hackathon. `citext` for case-insensitive emails. |
| **Anthropic Claude as primary LLM** | Tool use is first-class; routing by tier (Haiku for classify/route, Sonnet for reasoning, Opus only when escalated). |
| **Tool-use copilot, not free-form generation** | The copilot must take real actions (read PMS, draft replies, create tasks). Tools enforce structure and auditability. |
| **WebSocket only for live UI events** | Browser↔backend pushes (new message, sync progress). Bots use webhooks. |
| **No external task queue (v0)** | All background work via `asyncio.create_task()` orchestrated in `initialization/background_tasks.py`. Add Celery/RQ only if we hit scale issues. |
| **Encrypted integration credentials** | OAuth refresh tokens, PMS API keys, Twilio tokens encrypted at rest with a server-side key. |
| **Property-scoped multi-tenancy** | Every query filters by `user_id` or `property_id`. No global queries from the API surface. |
| **Prompts versioned in code** | `src/halloteo/llm/prompts/` — every prompt change is a commit, never a config flip. |
| **Hackathon: single deploy target** | One process, one Postgres, one domain. Defer blue/green and worker fleet until post-hackathon. |

## Open Questions

> Update this list as decisions land — leaving a question open here is fine; ignoring it is not.

- Which PMS do we integrate first? (Hostaway likely — best API.)
- WhatsApp via Twilio (regulated, easy onboarding) or Baileys (unrestricted, fragile)?
- How aggressive should auto-reply be? Pure suggestion vs. send-on-confidence?
- Do we need a notion of "team" (multiple managers per property) before Day 2?
- Embedding model: voyage-3 (best retrieval) vs. OpenAI text-embedding-3-small (cheaper)?
