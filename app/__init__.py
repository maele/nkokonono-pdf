from __future__ import annotations

import logging
import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from app.config import config_map
from app.extensions import csrf, db, migrate


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")
    config_cls = config_map.get(config_name)
    if config_cls is None:
        raise RuntimeError(f"Unknown FLASK_ENV: {config_name!r}")

    app.config.from_object(config_cls)

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY is not set. It is required in every environment.")

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    storage_root = Path(app.config["STORAGE_ROOT"])
    (storage_root / "temporary").mkdir(parents=True, exist_ok=True)
    (storage_root / "output").mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    logging.basicConfig(
        level=app.config.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )

    # --- blueprints -----------------------------------------------------
    from app.routes.main import bp as main_bp
    from app.routes.tools import bp as tools_bp
    from app.routes.jobs import bp as jobs_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(tools_bp)
    app.register_blueprint(jobs_bp)

    # --- database tables (Phase 2 MVP) ----------------------------------
    with app.app_context():
        from app import models  # noqa: F401
        db.create_all()

    _register_error_handlers(app)
    _register_security_headers(app)
    _register_template_context(app)

    # Nothing may come after this line.
    return app


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(400)
    def bad_request(err: HTTPException):
        if _wants_json():
            return jsonify({"error": {"code": "BAD_REQUEST", "message": err.description}}), 400
        return render_template("errors/404.html", message=err.description), 400

    @app.errorhandler(404)
    def not_found(err: HTTPException):
        if request.path.startswith("/api/"):
            app.logger.warning("API 404: %s %s", request.method, request.path)
        if _wants_json():
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Resource not found."}}), 404
        return render_template("errors/404.html", message="Page not found."), 404

    @app.errorhandler(413)
    def payload_too_large(err: HTTPException):
        if _wants_json():
            return jsonify({"error": {"code": "FILE_TOO_LARGE", "message": "The upload exceeds the configured limit."}}), 413
        return render_template("errors/404.html", message="File too large."), 413

    @app.errorhandler(500)
    def internal_error(err: HTTPException):
        app.logger.exception("Unhandled server error")
        if _wants_json():
            return jsonify({"error": {"code": "INTERNAL_ERROR", "message": "An internal error occurred."}}), 500
        return render_template("errors/500.html"), 500


def _wants_json() -> bool:
    if request.path.startswith("/api/"):
        return True
    accept = request.accept_mimetypes
    return accept["application/json"] > accept["text/html"]


def _register_security_headers(app: Flask) -> None:
    @app.after_request
    def _add_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        return response


def _register_template_context(app: Flask) -> None:
    @app.context_processor
    def _inject_limits():
        from datetime import datetime, timezone
        return {
            "max_upload_mb": app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024),
            "max_files_per_job": app.config["MAX_FILES_PER_JOB"],
            "retention_seconds": app.config["FILE_RETENTION_SECONDS"],
            "app_name": "Nkokonono ea PDF",
            "current_year": datetime.now(timezone.utc).year,
            "github_url": app.config.get(
                "GITHUB_URL", "https://github.com/maele/nkokonono-pdf"
            ),
            "support_email": app.config.get(
                "SUPPORT_EMAIL", "support@nalaneindustries.co.za"
            ),
        }
