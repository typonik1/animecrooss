# Fresh Balanced Deduplication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Select only fresh active unique edits across all sources and include the VPN link in every caption.

**Architecture:** Source candidates are ranked independently and consumed round-robin. Target-channel history restores fingerprint deduplication after Render restarts, and archive fallback is removed.

**Tech Stack:** Python, Telethon, SQLite, pytest.

## Global Constraints

- Fresh means no older than seven days.
- Never use archive fallback when fresh candidates are exhausted.
- The formatted `Лучший VPN` link appears in every published caption.

### Task 1: Balanced fresh-only selection

- [ ] Write failing tests for per-source activity order and round-robin selection.
- [ ] Implement a pure balanced selector and remove archive collection.
- [ ] Run focused tests.

### Task 2: Target-history deduplication

- [ ] Write a failing test that imports target video fingerprints as posted records.
- [ ] Implement one startup history scan through the reader account.
- [ ] Ensure every queue build uses the restored deduplication state.
- [ ] Run focused tests.

### Task 3: Required VPN signature and release

- [ ] Write a failing caption test for the exact HTML link.
- [ ] Add the link to the shared signature so captions with and without AI fields include it.
- [ ] Run compile, all tests, secret scan, commit, push, and verify Render health.
