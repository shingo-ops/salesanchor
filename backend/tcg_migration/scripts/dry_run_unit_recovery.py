"""
TCG E3a + E5 dry-run スクリプト。

DB から analysis_results を読み取り、単位復旧と状態再計算を
シミュレーションする。DB への書き込みは一切行わない。

使用方法:
  export TCG_DB_PROD_URL="postgresql+psycopg2://user:pass@host:5432/db"
  cd backend
  python -m tcg_migration.scripts.dry_run_unit_recovery

VPS 上 (docker exec):
  docker exec -e DATABASE_URL="..." -w /app astro-webapp-backend-1 \\
    python -m tcg_migration.scripts.dry_run_unit_recovery

終了コード:
  0 = 正常完了（dry-run 結果を stdout に出力）
  1 = エラー（DB 接続失敗など）
"""
from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# backend/ がパス上にあることを保証
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.services.tcg_unit_recovery_svc import run_unit_recovery_dry_run


def main() -> int:
    db_url = os.environ.get("TCG_DB_PROD_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        print(
            "ERROR: TCG_DB_PROD_URL or DATABASE_URL must be set",
            file=sys.stderr,
        )
        return 1

    # psycopg2 ドライバー指定を保証
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    engine = create_engine(db_url, echo=False)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        try:
            result = run_unit_recovery_dry_run(session, "tenant_004")
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc(file=sys.stderr)
            return 1
        finally:
            # dry-run: rollback any accidental changes (should be none)
            session.rollback()

    # Summary for machine parsing
    e3a = result["e3a"]
    e5 = result["e5"]
    print()
    print("=== Machine-readable summary ===")
    print(f"E3A_SUCCESS={e3a['success']}")
    print(f"E3A_COUNT={e3a['updated_count']}")
    print(f"E5_SUCCESS={e5['success']}")
    print(f"E5_TARGET={e5['target_count']}")
    print(f"E5_CHANGED={e5['changed_count']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
