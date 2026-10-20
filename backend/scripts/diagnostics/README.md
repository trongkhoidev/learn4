# Backend diagnostics

These scripts are manual diagnostics, not pytest tests. Run them from `backend/` with
`./.venv/bin/python -m scripts.diagnostics.debug_assignments`,
`./.venv/bin/python -m scripts.diagnostics.debug_deadline`, or
`./.venv/bin/python -m scripts.diagnostics.inspect_scoring`. The API scripts override the database, storage, teacher code, and
provider settings before importing the app; their SQLite database and uploads live in a
throwaway temporary directory and are removed when the command exits. They do not read
or modify the configured local database or real storage.
