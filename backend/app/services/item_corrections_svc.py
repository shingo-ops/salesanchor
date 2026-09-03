"""
PARITY-03 Phase 3 Stage 3: 修正履歴保存サービス（item_corrections）。

tenant_004.item_corrections に 1フィールド = 1行で append INSERT する。
上書きしない（GAS の overwrite 方式は踏襲しない）。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_SCHEMA = "tenant_004"


async def save_corrections(
    db: AsyncSession,
    *,
    extraction_item_id: str,
    source_message_id: str,
    fields: list[dict[str, str]],
    corrected_by: str,
) -> dict[str, int]:
    """
    非空の修正フィールドを item_corrections に INSERT する。

    Args:
        fields: [{"field_name": str, "system_value": str, "human_value": str}, ...]
                human_value が空のものは呼び出し元で除外済みであること。
        corrected_by: ユーザーの email アドレス。

    Returns:
        {"saved": <挿入行数>}
    """
    if not fields:
        return {"saved": 0}

    for field in fields:
        await db.execute(
            text(
                f"INSERT INTO {_SCHEMA}.item_corrections "
                "(extraction_item_id, source_message_id, field_name, system_value, human_value, corrected_by) "
                "VALUES (:eid, :smid, :fn, :sv, :hv, :cb)"
            ),
            {
                "eid": extraction_item_id,
                "smid": source_message_id,
                "fn": field["field_name"],
                "sv": field.get("system_value", ""),
                "hv": field["human_value"],
                "cb": corrected_by,
            },
        )

        # product_id 変更時のみ analysis_results を同一トランザクションで更新
        # human_value は product UUID 文字列。system_value と異なる場合のみ更新（確認済みは除く）
        if (
            field["field_name"] == "product_id"
            and field["human_value"]
            and field["human_value"] != field.get("system_value", "")
        ):
            await db.execute(
                text(
                    f"UPDATE {_SCHEMA}.analysis_results "
                    "SET product_id   = :new_pid::uuid, "
                    "    pid_basis    = 'MANUAL', "
                    "    pid_resolved = TRUE "
                    "WHERE extraction_item_id = :eid::uuid"
                ),
                {"new_pid": field["human_value"], "eid": extraction_item_id},
            )

    await db.commit()
    return {"saved": len(fields)}
