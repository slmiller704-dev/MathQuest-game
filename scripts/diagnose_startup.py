import os
import sys
import traceback


def safe_database_label(url: str | None) -> str:
    if not url:
        return "missing"
    if url.startswith("postgres"):
        return "postgresql"
    if url.startswith("sqlite"):
        return "sqlite"
    return "configured-unknown-driver"


print("[startup-check] Python:", sys.version.split()[0])
print("[startup-check] DATABASE_URL:", safe_database_label(os.getenv("DATABASE_URL")))
print("[startup-check] Importing app.main...")

try:
    from sqlalchemy import inspect, text
    from app.main import app, engine

    print("[startup-check] app.main imported")

    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1")).scalar_one()
        print("[startup-check] database SELECT 1:", result)

    table_names = inspect(engine).get_table_names()
    print("[startup-check] tables:", ", ".join(sorted(table_names)))

    route_paths = sorted(
        route.path for route in app.routes if getattr(route, "path", None)
    )
    print("[startup-check] routes:", ", ".join(route_paths))
    print("[startup-check] PASS")
except Exception:
    print("[startup-check] FAIL")
    traceback.print_exc()
    raise
