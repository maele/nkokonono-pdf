"""Public pages: landing, tool directory, health checks."""
from __future__ import annotations

from flask import Blueprint, jsonify, render_template

from app.tools.registry import CATEGORIES, POPULAR_SLUGS, TOOLS, TOOLS_BY_SLUG

bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    popular = [TOOLS_BY_SLUG[s] for s in POPULAR_SLUGS if s in TOOLS_BY_SLUG]
    return render_template(
        "index.html",
        tools=TOOLS,
        categories=CATEGORIES,
        popular=popular,
    )


@bp.get("/tools")
def tool_directory():
    return render_template("tools/directory.html", tools=TOOLS, categories=CATEGORIES)


@bp.get("/health")
def health():
    return jsonify({"status": "ok"})


@bp.get("/health/ready")
def readiness():
    # In Phase 1 there are no external dependencies to check.
    return jsonify({"status": "ready"})

@bp.get("/terms")
def terms():
    return render_template("terms.html")


@bp.get("/privacy")
def privacy():
    return render_template("privacy.html")


@bp.get("/contact")
def contact():
    return render_template("contact.html")


@bp.get("/licensing")
def licensing():
    return render_template("licensing.html")


@bp.get("/docs")
def docs():
    return render_template("docs.html", tools=TOOLS, categories=CATEGORIES)
