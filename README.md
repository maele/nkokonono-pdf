# Nkokonono ea PDF

Browser-based PDF utility platform. This repository currently implements
**Phase 1 — Foundation**: application shell, landing page, tool directory,
reusable upload component, server-side upload validation and cleanup.

Document processing (merge, split, compress, etc.) is planned for Phase 2.

## Requirements

- Python 3.12+
- pip and virtualenv
- (for Phase 2 and beyond) additional native packages documented per phase

## Local setup

```bash
git clone <repo>
cd nkokonono-pdf
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Edit `.env` and set a strong `SECRET_KEY`. Then run:

```bash
flask --app wsgi run --debug
```

The app is available at http://127.0.0.1:5000.

## Testing

```bash
pytest
pytest --cov=app
```

## Cleanup of temporary files

A one-hour retention window is enforced by default. Run the cleanup script
periodically (cron, systemd timer or task scheduler):

```bash
python -m scripts.cleanup
```

## Configuration

All deployment-specific settings are read from environment variables.
See `.env.example` for the supported keys.

- `SECRET_KEY` — required in production, no default.
- `MAX_CONTENT_LENGTH` — overall request body limit in bytes.
- `MAX_FILES_PER_JOB` — number of files accepted per operation.
- `FILE_RETENTION_SECONDS` — how long uploaded files are kept.
- `STORAGE_ROOT` — where temporary and output files live.

## Project layout

See the tree in `README.md` at the top of this milestone's deliverable,
or inspect the repository directly.

## Phase 1 status

- Landing page and tool directory.
- Reusable upload UI with drag-and-drop, keyboard support and client-side
  validation.
- Server-side upload validation using magic bytes (PDF, PNG, JPEG).
- Private per-upload temporary storage outside the web root.
- Retention-driven cleanup script.
- Security headers, CSRF protection, structured error responses.
- Automated tests for utilities, upload validation and routes.

## Phase 2 (next milestone)

- Merge PDF and Split PDF processors.
- Job records and status transitions.
- Download endpoint with authorised access.
- Additional tools added incrementally.

## Licence

MIT. See `LICENSE`.


## Phase 2 status

All Release 1 tools are now functional end-to-end:

- **Merge / Split / Compress** — `pypdf`.
- **Organise / Extract / Rotate / Delete** — page manipulation via `pypdf`.
- **Images to PDF** — `Pillow`.
- **PDF to images** — `PyMuPDF` (AGPL — see licence note below).
- **Protect / Unlock** — `pypdf` AES-256 encryption.
- **PDF metadata** — `pypdf` metadata editing.

Uploads are validated, stored privately and described in `meta.json`. Jobs
are created via `POST /api/jobs`, processed synchronously, persisted in the
`jobs` table and downloadable via `GET /api/jobs/<id>/download`.

### Database

Phase 2 uses `db.create_all()` in the app factory for convenience. For a real
deployment, remove that call and run:

```bash
flask db init      # once
flask db migrate -m "jobs table"
flask db upgrade
```

### Licence note — PyMuPDF

`PyMuPDF` is licensed under the AGPL. If you intend to distribute this
application commercially under a non-AGPL licence, either:

1. Obtain a commercial PyMuPDF licence, or
2. Replace `app/processors/pdf_to_images.py` with a `pdf2image`-based
   implementation (requires `poppler-utils` at the OS level).

All other Phase 2 dependencies use permissive licences.