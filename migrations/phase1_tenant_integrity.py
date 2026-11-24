"""Apply Phase 1 tenant indexes/constraints. Safe to re-run.

    python migrations/phase1_tenant_integrity.py

Rollback: see migrations/phase1_tenant_integrity_rollback.sql
"""
from utils.schema import ensure_schema


if __name__ == "__main__":
    ensure_schema()
    print("Phase 1 tenant integrity schema applied.")
