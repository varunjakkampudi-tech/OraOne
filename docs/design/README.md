# OraOne product interface

This folder records the design constraints and implementation boundary for the single authoritative OraOne application. Product 1 (OraOne AI Chat Platform) is the active implementation. Products 2–9 remain planned and Product 10 (OraOne OS) remains the long-term vision.

The temporary Lovable export was a design reference, not an application runtime. Its useful shell, authentication presentation, information architecture, and Product 1 URL vocabulary were integrated into `src/` while retaining the existing FastAPI contracts, PostgreSQL-backed identity and roles, project context, and website-widget SDK. The duplicate export, demo services, sample data, and generated dependencies are not part of the production repository.

## Documents

- [Design system and shell constraints](DESIGN_SYSTEM.md)

Visual review and automated checks are implementation evidence, not owner approval of every screen. Future design work must continue to preserve the real service boundary and truthful product availability.
