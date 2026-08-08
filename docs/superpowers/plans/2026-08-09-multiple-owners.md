# Multiple Bot Owners Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow the reader account and additional configured Telegram IDs to administer the bot.

**Architecture:** Parse `OWNER_IDS` plus legacy `OWNER_ID` into a set. Add the current reader account at startup, authorize commands by set membership, and send notifications to every owner.

**Tech Stack:** Python, Telethon, pytest.

## Global Constraints

- Owner IDs are configured through Render environment variables, not committed values.
- `OWNER_ID` remains backward compatible.

### Task 1: Owner-set configuration and authorization

- [ ] Write failing tests for comma-separated parsing and membership checks.
- [ ] Implement `OWNER_IDS` set parsing and update admin authorization.
- [ ] Run focused tests.

### Task 2: Startup and notification fan-out

- [ ] Write failing tests for reader-owner addition and notification fan-out.
- [ ] Add the authenticated reader ID and notify every owner independently.
- [ ] Run all tests, commit, and push `main`.
