# Hallo Theo — Product Behavior Specification

> **Purpose**: Single source of truth for how Hallo Theo behaves across web and chat surfaces. Designed for both humans and AI coding assistants (Claude Code) to consume as an implementation guideline.
>
> **How to read this spec**: Behavior defined in §1 (Global Principles) applies everywhere unless explicitly overridden. §2 defines surface-specific behavior. §3 catalogs reusable component behavior. §4 defines state machines for core objects.

---

## Table of Contents

1. [Global Principles](#1-global-principles)
2. [Surfaces](#2-surfaces) — Web App, WhatsApp Bot, Slack Bot
3. [Core Domains](#3-core-domains) — Properties, Bookings, Inbox, Tasks, Copilot
4. [Component Behavior Catalog](#4-component-behavior-catalog)
5. [State Machines](#5-state-machines)
6. [User Flows](#6-user-flows)
7. [Notifications](#7-notifications)
8. [Settings & Preferences](#8-settings--preferences)
9. [Onboarding](#9-onboarding)
10. [Error Handling & Edge Cases](#10-error-handling--edge-cases)
11. [Permissions & Access Control](#11-permissions--access-control)
12. [Search](#12-search)
13. [Keyboard Shortcuts & Gestures](#13-keyboard-shortcuts--gestures)

---

# 1. Global Principles

> Fill in: the non-negotiables that apply to every surface. (e.g. "Copilot never sends an outbound message without explicit user approval in v1.")

## 1.1 What Hallo Theo Is
- TBD: one-paragraph description.

## 1.2 Who It's For
- TBD: target user (e.g. STR host with 1–20 units, boutique property manager).

## 1.3 Tone of Voice
- TBD: how does the copilot speak? (friendly, professional, concise?)

## 1.4 Safety Rails
- TBD: rules the copilot must never break (no booking changes without confirmation, no PII to third parties, etc.).

---

# 2. Surfaces

## 2.1 Web App
- TBD: primary daily-driver UI; describe purpose and shape.

## 2.2 WhatsApp Bot
- TBD: who talks to it (guest vs. manager), what it can do, what requires escalation.

## 2.3 Slack Bot
- TBD: internal team surface; commands and notifications.

---

# 3. Core Domains

## 3.1 Properties
- TBD: what data we store, how it's created, what's editable.

## 3.2 Bookings
- TBD: where they come from (PMS sync), lifecycle, cancellation handling.

## 3.3 Inbox (Conversations)
- TBD: how guest/owner messages are grouped, threaded, prioritized.

## 3.4 Tasks
- TBD: cleanings, maintenance, check-in/out — who creates them, who assigns, status flow.

## 3.5 Copilot
- TBD: what tools it has, when it asks for confirmation, how it cites sources.

## 3.6 Knowledge Base
- TBD: house manuals, policies, FAQs — how they're ingested and used in RAG.

---

# 4. Component Behavior Catalog

> Fill in: per-component behavior for reusable UI primitives (DraftPanel, BriefingCard, etc.).

---

# 5. State Machines

## 5.1 Booking
- TBD: states + allowed transitions.

## 5.2 Task
- TBD: open → in_progress → done; cancellation rules.

## 5.3 Message
- TBD: in/out, draft/sent/failed.

## 5.4 Copilot Turn
- TBD: how a turn progresses from prompt → tool loop → final answer.

---

# 6. User Flows

## 6.1 First-Time Setup
- TBD: signup → connect PMS → import properties → first briefing.

## 6.2 Daily Briefing
- TBD: when it's generated, what it contains, where it's delivered.

## 6.3 Guest Question (auto-handled)
- TBD: guest asks → copilot answers from KB → manager reviews log.

## 6.4 Guest Question (escalated)
- TBD: copilot detects uncertainty → routes to manager → manager replies via web/chat.

## 6.5 Maintenance Issue
- TBD: report → triage → task creation → assignment → close-out.

---

# 7. Notifications

- TBD: what triggers a push/email/in-app notification, and on which surfaces.

---

# 8. Settings & Preferences

- TBD: per-user toggles (auto-reply confidence threshold, quiet hours, voice).

---

# 9. Onboarding

- TBD: minimum steps to a useful first session.

---

# 10. Error Handling & Edge Cases

- TBD: PMS sync fails, LLM times out, guest sends 50 messages in a minute, etc.

---

# 11. Permissions & Access Control

- TBD: owner vs. manager vs. cleaner permissions; property-scoped data.

---

# 12. Search

- TBD: what's searchable (bookings, messages, properties, docs) and how.

---

# 13. Keyboard Shortcuts & Gestures

- TBD: web app shortcuts.
