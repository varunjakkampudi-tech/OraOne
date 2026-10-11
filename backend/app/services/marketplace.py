"""AI Marketplace catalogue (Phase Z).

A curated, in-code catalogue of installable building blocks so tenants can go
from zero to a working agent in one click. Keeping the catalogue in code (like
the Prompt Studio industry templates) means no seed data or extra table — we
only persist *installations*.

Categories
----------
* ``agent_template`` — a ready-made business agent (installs a real Agent).
* ``integration``    — a third-party connector blueprint.
* ``workflow``       — an automation recipe.
"""
from __future__ import annotations

from typing import Any, Optional

CATEGORIES = [
    {"value": "agent_template", "label": "Agent Templates"},
    {"value": "integration", "label": "Integrations"},
    {"value": "workflow", "label": "Workflows"},
]
_CATEGORY_VALUES = {c["value"] for c in CATEGORIES}


def _agent(slug, name, summary, icon, tags, system_prompt, greeting, *, featured=False,
           voice="emma", language="en", model="gpt-4o-mini",
           knowledge=None, workflow=None, integrations=None, pipeline=None,
           theme=None, analytics=None):
    """A full-stack business template.

    Installing it provisions a real :class:`Agent` (+config) and a starter
    :class:`KnowledgeBase`; the remaining stack (workflow, widget theme,
    suggested integrations, lead pipeline, analytics) is declared in the
    blueprint so the UI can show exactly what a one-click install sets up.
    """
    return {
        "slug": slug,
        "name": name,
        "category": "agent_template",
        "summary": summary,
        "icon": icon,
        "tags": tags,
        "author": "OraOne",
        "featured": featured,
        "blueprint": {
            "system_prompt": system_prompt,
            "greeting": greeting,
            "voice": voice,
            "language": language,
            "model": model,
            "knowledge_structure": knowledge or ["FAQs", "Pricing", "Policies", "Services"],
            "workflow": workflow or {"trigger": "lead.created", "steps": ["wait_1h", "email"]},
            "suggested_integrations": integrations or ["google_calendar", "hubspot"],
            "lead_pipeline": pipeline or ["New", "Contacted", "Qualified", "Won", "Lost"],
            "widget_theme": theme or {"primary": "#4F46E5", "launcher": "chat", "position": "bottom-right", "dark_mode": True},
            "analytics_dashboard": analytics or ["Conversations", "Leads", "Conversion %", "CSAT", "Avg handle time"],
        },
    }


# ─────────────────────────────── catalogue ───────────────────────────────────
LISTINGS: list[dict[str, Any]] = [
    _agent(
        "dental-clinic-ai", "Dental Clinic AI",
        "Books appointments, answers treatment questions and captures new patients.",
        "🦷", ["healthcare", "appointments", "receptionist"],
        "You are a warm, professional member of the front desk team at a dental clinic. "
        "Help callers book or reschedule appointments, answer questions about common "
        "treatments and pricing ranges, and capture new-patient details. Confirm names, "
        "phone numbers and times by reading them back. Never give clinical diagnoses.",
        "Hi, thanks for calling! How can I help you with your dental care today?",
        featured=True,
    ),
    _agent(
        "real-estate-ai", "Real Estate AI",
        "Qualifies buyers, books viewings and follows up on listings.",
        "🏠", ["real-estate", "sales", "lead-gen"],
        "You are a friendly real-estate sales associate. Qualify the caller's budget, "
        "location and timeline, match them to suitable listings, and book property "
        "viewings. Capture full contact details and the property of interest.",
        "Hi there! Are you looking to buy, sell or rent today?",
        featured=True,
    ),
    _agent(
        "restaurant-ai", "Restaurant Reservations AI",
        "Takes table bookings, answers menu questions and handles waitlists.",
        "🍽️", ["hospitality", "bookings"],
        "You are a courteous host at a restaurant. Take and confirm table reservations "
        "(date, time, party size, name and phone), answer questions about the menu, "
        "hours and dietary options, and manage the waitlist politely.",
        "Hello! Thanks for calling. Would you like to make a reservation?",
    ),
    _agent(
        "ecommerce-support-ai", "E-commerce Support AI",
        "Tracks orders, handles returns and answers product questions.",
        "🛍️", ["ecommerce", "support"],
        "You are a helpful customer-support specialist for an online store. Help with "
        "order status, returns and exchanges, shipping timelines and product questions. "
        "Verify the order reference and the customer's email before sharing details.",
        "Hi! I can help with your order, a return or any product question — what do you need?",
        featured=True,
    ),
    _agent(
        "saas-onboarding-ai", "SaaS Onboarding AI",
        "Welcomes new signups, books demos and answers product questions.",
        "💻", ["saas", "onboarding", "sales"],
        "You are a friendly product specialist for a software company. Welcome new "
        "signups, understand their use-case, answer questions about features and "
        "pricing tiers, and book a demo with the right specialist.",
        "Hey! Welcome aboard. Want a quick hand getting set up, or shall I book you a demo?",
    ),
    _agent(
        "education-admissions-ai", "Education Admissions AI",
        "Answers course questions, captures applicants and books counselling.",
        "🎓", ["education", "admissions", "lead-gen"],
        "You are a helpful admissions advisor. Answer questions about courses, fees and "
        "schedules, capture the prospective student's details and goals, and book a "
        "counselling session. Be encouraging and clear.",
        "Hi! Are you exploring a course with us? I'd be happy to help.",
    ),
    _agent(
        "insurance-ai", "Insurance Advisor AI",
        "Qualifies prospects, explains policies and books advisor calls.",
        "🛡️", ["insurance", "sales", "lead-gen"],
        "You are a clear, trustworthy insurance advisor. Understand the caller's needs "
        "(life, health, motor, property), explain plan options and coverage in simple "
        "terms, capture their details, and book a call with a licensed advisor. Never "
        "make guarantees about claims outcomes.",
        "Hi! Are you looking for health, motor, life or property cover today?",
        featured=True,
        knowledge=["Plans & Coverage", "Premium Calculator", "Claims Process", "Eligibility"],
        pipeline=["Lead", "Qualified", "Quoted", "Policy Issued", "Lost"],
        analytics=["Quotes", "Conversion %", "Premium value", "Renewals"],
    ),
    _agent(
        "automobile-ai", "Automobile Dealership AI",
        "Books test drives, qualifies buyers and schedules service.",
        "🚗", ["automobile", "sales", "service"],
        "You are an enthusiastic automobile dealership associate. Help callers book test "
        "drives, compare models and finance options, and schedule service appointments. "
        "Capture name, phone, model of interest and preferred time.",
        "Hi! Are you interested in a new vehicle, a test drive, or booking a service?",
        knowledge=["Models & Pricing", "Finance & EMI", "Test Drives", "Service & Warranty"],
        pipeline=["Lead", "Test Drive", "Negotiation", "Sold", "Lost"],
        analytics=["Test drives", "Conversion %", "Avg deal value", "Service bookings"],
    ),
    # ── integrations ──
    {
        "slug": "integration-google-calendar", "name": "Google Calendar",
        "category": "integration", "summary": "Sync appointments and bookings to Google Calendar.",
        "icon": "📅", "tags": ["calendar", "scheduling"], "author": "OraOne", "featured": False,
        "blueprint": {"provider": "google_calendar", "scopes": ["calendar.events"]},
    },
    {
        "slug": "integration-hubspot", "name": "HubSpot CRM",
        "category": "integration", "summary": "Push qualified leads and call notes into HubSpot.",
        "icon": "🧲", "tags": ["crm", "leads"], "author": "OraOne", "featured": True,
        "blueprint": {"provider": "hubspot", "objects": ["contacts", "deals"]},
    },
    # ── workflows ──
    {
        "slug": "workflow-lead-followup", "name": "Lead Follow-up Sequence",
        "category": "workflow", "summary": "Auto-follow-up new leads by email.",
        "icon": "⚡", "tags": ["automation", "lead-gen"], "author": "OraOne", "featured": True,
        "blueprint": {"trigger": "lead.created", "steps": ["wait_1h", "email"]},
    },
]

_BY_SLUG = {item["slug"]: item for item in LISTINGS}


def list_listings(category: Optional[str] = None, q: Optional[str] = None) -> list[dict[str, Any]]:
    """Return catalogue listings filtered by category and/or a search query."""
    items = LISTINGS
    if category and category in _CATEGORY_VALUES:
        items = [i for i in items if i["category"] == category]
    if q:
        needle = q.strip().lower()
        items = [
            i for i in items
            if needle in i["name"].lower()
            or needle in i["summary"].lower()
            or any(needle in t for t in i.get("tags", []))
        ]
    # Featured first, then alphabetical.
    return sorted(items, key=lambda i: (not i.get("featured"), i["name"].lower()))


def get_listing(slug: str) -> Optional[dict[str, Any]]:
    return _BY_SLUG.get(slug)
