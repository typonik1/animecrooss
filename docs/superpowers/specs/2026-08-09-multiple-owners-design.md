# Multiple Bot Owners Design

The bot accepts a comma-separated `OWNER_IDS` environment variable while preserving the existing singular `OWNER_ID` for compatibility. On startup, the authenticated reader account is added to the owner set automatically. Every owner can use private admin commands and receives operational notifications. IDs remain deployment configuration and are not hardcoded in the repository.

Tests cover parsing, automatic reader-owner addition, authorization, and notification fan-out.
