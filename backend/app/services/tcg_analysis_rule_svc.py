"""
ANALYSIS-RULE P5: 完売ルール・日付ルール共通サービス層。

設計書: docs/handoff/tcg-import-latest-only/sold-out-rules-design.md §6.2, §14.1
担当: CARD-ANALYSIS-RULE-P5-API-WORKER

機能:
  - get_current_state: active/draft/suite のID・lock_version・activation_state を返す
  - get_revision_rules: 語句一覧（word_kind フィルター対応）
  - create_draft_revision: 新版作成 + draft 参照更新
  - save_test_suite: 正解例保存
  - start_test_run: テスト実行開始（202 + run_id）
  - get_test_run_result: 結果取得
  - activate_revision: 本番適用
  - get_history: 変更履歴
  - get_revision_detail: 版の全内容

contract:
  - policy_type URL kebab-case → DB snake_case 変換は呼び出し元で行う
  - request_key による冪等性: UNIQUE制約でDB側が重複排除
  - lock_version による楽観的ロック: UPDATE ... WHERE lock_version = :expected
  - C93: product_id 変更時に analysis_rule_run_results の invalidated_at を NOW() に設定
  - C95: 本番判断は最新成功 job の items のみ対象（status='done' AND 最新 created_at 1件）
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.tcg_config import TCG_SCHEMA

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# policy_type バリデーション
# ---------------------------------------------------------------------------

VALID_POLICY_TYPES = {"sold_out", "date_format"}

# policy_type ごとに許可される word_kind 一覧
ALLOWED_WORD_KINDS: dict[str, set[str]] = {
    "sold_out": {"search", "exclude"},
    "date_format": {"format_template", "apply_condition"},
}


def _validate_policy_type(policy_type: str) -> None:
    if policy_type not in VALID_POLICY_TYPES:
        raise ValueError(f"policy_type は {VALID_POLICY_TYPES} のいずれかである必要があります: {policy_type!r}")


def _validate_word_kind(policy_type: str, word_kind: str | None) -> None:
    if word_kind is None or word_kind == "both":
        return
    allowed = ALLOWED_WORD_KINDS.get(policy_type, set())
    if word_kind not in allowed:
        raise ValueError(
            f"policy_type={policy_type!r} で word_kind={word_kind!r} は許可されていません。"
            f"許可値: {allowed | {'both'}}"
        )


# ---------------------------------------------------------------------------
# get_current_state
# ---------------------------------------------------------------------------


async def get_current_state(db: AsyncSession, policy_type: str) -> dict[str, Any]:
    """
    GET {base}/current

    active/draft/suite の ID、lock_version、activation_state を返す。
    policy が存在しない場合は 404 相当の None を返す。
    """
    _validate_policy_type(policy_type)
    row = await db.execute(
        text(
            f"""
            SELECT id,
                   active_revision_id,
                   draft_revision_id,
                   current_suite_revision_id,
                   lock_version,
                   activation_state,
                   created_at,
                   updated_at
            FROM public.analysis_policies
            WHERE policy_type = :policy_type
            """
        ),
        {"policy_type": policy_type},
    )
    result = row.mappings().first()
    if result is None:
        return None
    return dict(result)


# ---------------------------------------------------------------------------
# get_revision_rules
# ---------------------------------------------------------------------------


async def get_revision_rules(
    db: AsyncSession,
    revision_id: str,
    policy_type: str,
    *,
    q: str | None = None,
    word_kind: str | None = None,
    deleted: bool | None = None,
    cursor: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """
    GET {base}/revisions/{id}/rules

    指定版から語句を検索する。
    word_kind は完売なら search/exclude/both、日付なら format_template/apply_condition/both。
    """
    _validate_policy_type(policy_type)
    _validate_word_kind(policy_type, word_kind)

    allowed_kinds = ALLOWED_WORD_KINDS[policy_type]

    # word_kind フィルター
    if word_kind and word_kind != "both":
        kind_filter = "AND w.kind = :word_kind"
    else:
        # both or None → policy_type に許可された全 kind
        kind_filter = "AND w.kind = ANY(:allowed_kinds)"

    # テキスト検索
    q_filter = "AND w.text ILIKE :q" if q else ""

    # 削除済みフィルター
    deleted_filter = ""
    if deleted is True:
        deleted_filter = "AND arr.is_deleted = TRUE"
    elif deleted is False:
        deleted_filter = "AND arr.is_deleted = FALSE"

    # カーソルページネーション
    cursor_filter = "AND w.id > :cursor" if cursor else ""

    params: dict[str, Any] = {
        "revision_id": revision_id,
        "limit": limit + 1,  # 次ページ有無判定用に1件多く取得
    }
    if q:
        params["q"] = f"%{q}%"
    if word_kind and word_kind != "both":
        params["word_kind"] = word_kind
    else:
        params["allowed_kinds"] = list(allowed_kinds)
    if cursor:
        params["cursor"] = cursor

    sql = text(
        f"""
        SELECT
            ar.id           AS rule_id,
            arv.id          AS rule_version_id,
            arv.title,
            arv.context_instruction,
            w.id            AS word_id,
            w.kind          AS word_kind,
            w.text          AS word_text,
            w.position,
            arr.is_deleted
        FROM public.analysis_revision_rules arr
        JOIN public.analysis_rules ar
            ON ar.id = arr.rule_id
        JOIN public.analysis_rule_versions arv
            ON arv.id = arr.rule_version_id
        JOIN public.analysis_rule_words w
            ON w.rule_version_id = arv.id
        WHERE arr.revision_id = :revision_id
          {kind_filter}
          {q_filter}
          {deleted_filter}
          {cursor_filter}
        ORDER BY w.id
        LIMIT :limit
        """
    )
    rows = (await db.execute(sql, params)).mappings().all()

    has_next = len(rows) > limit
    items = [dict(r) for r in rows[:limit]]
    next_cursor = items[-1]["word_id"] if has_next and items else None

    return {"items": items, "has_next": has_next, "next_cursor": str(next_cursor) if next_cursor else None}


# ---------------------------------------------------------------------------
# create_draft_revision
# ---------------------------------------------------------------------------


async def create_draft_revision(
    db: AsyncSession,
    policy_type: str,
    *,
    expected_draft_id: str | None,
    expected_active_id: str | None,
    lock_version: int,
    changes: list[dict[str, Any]],
    request_key: str,
    created_by: str,
) -> dict[str, Any]:
    """
    POST {base}/draft-revisions

    新版を作って draft 参照のみ更新する。
    lock_version 不一致 → 409 Conflict。
    request_key 重複 → 既存 run_id を返す（冪等）。
    """
    _validate_policy_type(policy_type)

    # 冪等性: request_key による重複は DB側 UNIQUE 制約の IntegrityError で検出する。
    # analysis_policy_revisions に request_key カラムがない場合、
    # 呼び出し元で IntegrityError をキャッチして冪等レスポンスを返す設計。

    # 楽観的ロック確認 + policy 取得
    policy_row = await db.execute(
        text(
            f"""
            SELECT id, active_revision_id, draft_revision_id, lock_version
            FROM public.analysis_policies
            WHERE policy_type = :policy_type
            """
        ),
        {"policy_type": policy_type},
    )
    policy = policy_row.mappings().first()
    if policy is None:
        raise ValueError(f"policy_type={policy_type!r} が見つかりません")

    if policy["lock_version"] != lock_version:
        raise ConflictError(
            f"lock_version 不一致: 期待={lock_version} 実際={policy['lock_version']}"
        )
    if expected_draft_id and str(policy["draft_revision_id"] or "") != expected_draft_id:
        raise ConflictError(
            f"expected_draft_id 不一致: 期待={expected_draft_id} 実際={policy['draft_revision_id']}"
        )
    if expected_active_id and str(policy["active_revision_id"] or "") != expected_active_id:
        raise ConflictError(
            f"expected_active_id 不一致: 期待={expected_active_id} 実際={policy['active_revision_id']}"
        )

    policy_id = str(policy["id"])

    # 指示文 version 作成（changes に instruction が含まれる場合）
    instruction_id = await _upsert_instruction_version(db, policy_id, changes, created_by)

    # content_digest: changes の JSON ハッシュ
    content_digest = hashlib.sha256(
        json.dumps(changes, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    # 新 revision 作成
    new_revision_id = str(uuid4())
    await db.execute(
        text(
            f"""
            INSERT INTO public.analysis_policy_revisions
                (id, policy_id, parent_revision_id, instruction_version_id, content_digest, created_by)
            VALUES
                (:id, :policy_id, :parent_id, :instruction_id, :digest, :created_by)
            """
        ),
        {
            "id": new_revision_id,
            "policy_id": policy_id,
            "parent_id": policy["draft_revision_id"],
            "instruction_id": instruction_id,
            "digest": content_digest,
            "created_by": created_by,
        },
    )

    # rules を analysis_revision_rules に追加
    await _apply_changes_to_revision(db, policy_id, new_revision_id, changes, created_by)

    # draft 参照を更新（lock_version を +1）
    updated = await db.execute(
        text(
            f"""
            UPDATE public.analysis_policies
            SET draft_revision_id = :new_rev_id,
                activation_state  = CASE activation_state
                                      WHEN 'active' THEN 'active'
                                      ELSE 'draft'
                                    END,
                lock_version      = lock_version + 1,
                updated_at        = NOW()
            WHERE policy_type = :policy_type
              AND lock_version = :expected_lock
            """
        ),
        {
            "new_rev_id": new_revision_id,
            "policy_type": policy_type,
            "expected_lock": lock_version,
        },
    )
    if updated.rowcount == 0:
        raise ConflictError("lock_version 競合: 別のリクエストが先に更新しました")

    await db.commit()
    return {"revision_id": new_revision_id, "policy_type": policy_type}


async def _upsert_instruction_version(
    db: AsyncSession,
    policy_id: str,
    changes: list[dict[str, Any]],
    created_by: str,
) -> str:
    """changes から instruction テキストを探して新版を作成、IDを返す。なければ最新版を使う。"""
    instruction_text = None
    for change in changes:
        if change.get("type") == "instruction" and change.get("body"):
            instruction_text = change["body"]
            break

    if instruction_text:
        new_id = str(uuid4())
        await db.execute(
            text(
                f"""
                INSERT INTO public.analysis_instruction_versions
                    (id, policy_id, body, created_by)
                VALUES (:id, :policy_id, :body, :created_by)
                """
            ),
            {"id": new_id, "policy_id": policy_id, "body": instruction_text, "created_by": created_by},
        )
        return new_id

    # 最新の instruction version を取得
    row = await db.execute(
        text(
            f"""
            SELECT id FROM public.analysis_instruction_versions
            WHERE policy_id = :policy_id
            ORDER BY created_at DESC LIMIT 1
            """
        ),
        {"policy_id": policy_id},
    )
    result = row.scalar_one_or_none()
    if result is None:
        # 初回: ダミー instruction version を作成
        new_id = str(uuid4())
        await db.execute(
            text(
                f"""
                INSERT INTO public.analysis_instruction_versions
                    (id, policy_id, body, created_by)
                VALUES (:id, :policy_id, :body, :created_by)
                """
            ),
            {"id": new_id, "policy_id": policy_id, "body": "(初期指示文)", "created_by": created_by},
        )
        return new_id
    return str(result)


async def _apply_changes_to_revision(
    db: AsyncSession,
    policy_id: str,
    revision_id: str,
    changes: list[dict[str, Any]],
    created_by: str,
) -> None:
    """changes リストに基づき analysis_revision_rules を構築する。"""
    for change in changes:
        if change.get("type") not in ("add_rule", "update_rule", "delete_rule"):
            continue

        rule_id = change.get("rule_id") or str(uuid4())
        is_deleted = change.get("type") == "delete_rule"

        # rule が存在しなければ作成
        await db.execute(
            text(
                f"""
                INSERT INTO public.analysis_rules (id, policy_id)
                VALUES (:id, :policy_id)
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {"id": rule_id, "policy_id": policy_id},
        )

        # rule_version 作成
        rule_version_id = str(uuid4())
        await db.execute(
            text(
                f"""
                INSERT INTO public.analysis_rule_versions
                    (id, rule_id, title, context_instruction, created_by)
                VALUES (:id, :rule_id, :title, :context_instruction, :created_by)
                """
            ),
            {
                "id": rule_version_id,
                "rule_id": rule_id,
                "title": change.get("title", ""),
                "context_instruction": change.get("context_instruction"),
                "created_by": created_by,
            },
        )

        # words を登録
        for pos, word in enumerate(change.get("words", [])):
            word_id = str(uuid4())
            await db.execute(
                text(
                    f"""
                    INSERT INTO public.analysis_rule_words
                        (id, rule_version_id, kind, text, position)
                    VALUES (:id, :rule_version_id, :kind, :text, :position)
                    """
                ),
                {
                    "id": word_id,
                    "rule_version_id": rule_version_id,
                    "kind": word["kind"],
                    "text": word["text"],
                    "position": pos,
                },
            )

        # revision_rules に追加
        await db.execute(
            text(
                f"""
                INSERT INTO public.analysis_revision_rules
                    (revision_id, rule_id, rule_version_id, is_deleted)
                VALUES (:revision_id, :rule_id, :rule_version_id, :is_deleted)
                ON CONFLICT (revision_id, rule_id) DO UPDATE
                    SET rule_version_id = EXCLUDED.rule_version_id,
                        is_deleted      = EXCLUDED.is_deleted
                """
            ),
            {
                "revision_id": revision_id,
                "rule_id": rule_id,
                "rule_version_id": rule_version_id,
                "is_deleted": is_deleted,
            },
        )


# ---------------------------------------------------------------------------
# save_test_suite
# ---------------------------------------------------------------------------


async def save_test_suite(
    db: AsyncSession,
    policy_type: str,
    *,
    expected_suite_id: str | None,
    cases: list[dict[str, Any]],
    request_key: str,
    created_by: str,
) -> dict[str, Any]:
    """
    POST {base}/test-suites

    正解例保存。新しい suite / case_version を作成して suite_id を返す。
    """
    _validate_policy_type(policy_type)

    # policy 取得
    policy_row = await db.execute(
        text(
            f"""
            SELECT id FROM public.analysis_policies
            WHERE policy_type = :policy_type
            """
        ),
        {"policy_type": policy_type},
    )
    policy = policy_row.mappings().first()
    if policy is None:
        raise ValueError(f"policy_type={policy_type!r} が見つかりません")

    policy_id = str(policy["id"])

    # 新 suite 作成
    suite_id = str(uuid4())
    await db.execute(
        text(
            f"""
            INSERT INTO public.analysis_test_suites (id, policy_id)
            VALUES (:id, :policy_id)
            """
        ),
        {"id": suite_id, "policy_id": policy_id},
    )

    # cases を登録
    for case in cases:
        case_id = case.get("case_id") or str(uuid4())
        case_version_id = str(uuid4())

        await db.execute(
            text(
                f"""
                INSERT INTO public.analysis_test_case_versions
                    (id, case_id, policy_id, raw_text, posted_at, expected, created_by)
                VALUES
                    (:id, :case_id, :policy_id, :raw_text, :posted_at, :expected::jsonb, :created_by)
                """
            ),
            {
                "id": case_version_id,
                "case_id": case_id,
                "policy_id": policy_id,
                "raw_text": case["raw_text"],
                "posted_at": case.get("posted_at"),
                "expected": json.dumps(case["expected"], ensure_ascii=False),
                "created_by": created_by,
            },
        )

        await db.execute(
            text(
                f"""
                INSERT INTO public.analysis_suite_cases
                    (suite_id, case_id, case_version_id)
                VALUES (:suite_id, :case_id, :case_version_id)
                """
            ),
            {"suite_id": suite_id, "case_id": case_id, "case_version_id": case_version_id},
        )

    # policy の current_suite_revision_id を更新
    await db.execute(
        text(
            f"""
            UPDATE public.analysis_policies
            SET current_suite_revision_id = :suite_id,
                updated_at                = NOW()
            WHERE policy_type = :policy_type
            """
        ),
        {"suite_id": suite_id, "policy_type": policy_type},
    )

    await db.commit()
    return {"suite_id": suite_id, "cases_count": len(cases)}


# ---------------------------------------------------------------------------
# start_test_run
# ---------------------------------------------------------------------------


async def start_test_run(
    db: AsyncSession,
    policy_type: str,
    *,
    revision_id: str,
    suite_revision_id: str,
    request_key: str,
    started_by: str,
) -> dict[str, Any]:
    """
    POST {base}/test-runs

    テスト実行を開始する（202 + run_id）。
    Celery タスクへのエンキューは呼び出し元ルーターが行う。
    """
    _validate_policy_type(policy_type)

    # policy 取得
    policy_row = await db.execute(
        text(
            f"""
            SELECT id FROM public.analysis_policies
            WHERE policy_type = :policy_type
            """
        ),
        {"policy_type": policy_type},
    )
    policy = policy_row.mappings().first()
    if policy is None:
        raise ValueError(f"policy_type={policy_type!r} が見つかりません")

    run_id = str(uuid4())
    await db.execute(
        text(
            f"""
            INSERT INTO public.analysis_rule_runs
                (id, policy_id, revision_id, suite_revision_id, purpose,
                 engine_version, request_key, started_by, state)
            VALUES
                (:run_id, :policy_id, :revision_id, :suite_revision_id, 'test',
                 'v1', :request_key, :started_by, 'pending')
            """
        ),
        {
            "run_id": run_id,
            "policy_id": str(policy["id"]),
            "revision_id": revision_id,
            "suite_revision_id": suite_revision_id,
            "request_key": request_key,
            "started_by": started_by,
        },
    )
    await db.commit()
    return {"run_id": run_id}


# ---------------------------------------------------------------------------
# get_test_run_result
# ---------------------------------------------------------------------------


async def get_test_run_result(db: AsyncSession, run_id: str) -> dict[str, Any] | None:
    """
    GET {base}/test-runs/{id}

    実行結果を返す。expected と actual を原文根拠と併記する。
    """
    run_row = await db.execute(
        text(
            f"""
            SELECT id, revision_id, suite_revision_id, purpose, engine_version,
                   state, started_at, completed_at, started_by
            FROM public.analysis_rule_runs
            WHERE id = :run_id
            """
        ),
        {"run_id": run_id},
    )
    run = run_row.mappings().first()
    if run is None:
        return None

    # 結果一覧
    results_row = await db.execute(
        text(
            f"""
            SELECT r.id,
                   r.case_version_id,
                   r.extraction_item_id,
                   r.decision,
                   r.source_spans,
                   r.rule_version_refs,
                   r.validation_error,
                   r.invalidated_at,
                   r.created_at,
                   cv.raw_text     AS expected_raw_text,
                   cv.expected     AS expected_json
            FROM public.analysis_rule_run_results r
            LEFT JOIN public.analysis_test_case_versions cv
                ON cv.id = r.case_version_id
            WHERE r.run_id = :run_id
            ORDER BY r.created_at
            """
        ),
        {"run_id": run_id},
    )
    results = [dict(row) for row in results_row.mappings().all()]

    total = len(results)
    passed_count = sum(
        1 for r in results
        if r.get("validation_error") is None and r.get("invalidated_at") is None
    )

    return {
        "run": dict(run),
        "results": results,
        "summary": {
            "total": total,
            "passed": passed_count,
            "failed": total - passed_count,
        },
    }


# ---------------------------------------------------------------------------
# activate_revision
# ---------------------------------------------------------------------------


async def activate_revision(
    db: AsyncSession,
    policy_type: str,
    *,
    revision_id: str,
    run_id: str,
    expected_active_id: str | None,
    lock_version: int,
    request_key: str,
    activated_by: str,
) -> dict[str, Any]:
    """
    POST {base}/activate

    全検証後 active 参照を更新し監査記録を一括 commit する。

    検証:
      - lock_version 一致
      - run の state = 'passed' かつ purpose = 'test'
      - 全件通過・誤判定0・見落とし0
    """
    _validate_policy_type(policy_type)

    # 楽観的ロック確認
    policy_row = await db.execute(
        text(
            f"""
            SELECT id, active_revision_id, lock_version, activation_state
            FROM public.analysis_policies
            WHERE policy_type = :policy_type
            """
        ),
        {"policy_type": policy_type},
    )
    policy = policy_row.mappings().first()
    if policy is None:
        raise ValueError(f"policy_type={policy_type!r} が見つかりません")

    if policy["lock_version"] != lock_version:
        raise ConflictError(
            f"lock_version 不一致: 期待={lock_version} 実際={policy['lock_version']}"
        )
    if expected_active_id and str(policy["active_revision_id"] or "") != expected_active_id:
        raise ConflictError(
            f"expected_active_id 不一致: 期待={expected_active_id} 実際={policy['active_revision_id']}"
        )

    # run 検証
    run_row = await db.execute(
        text(
            f"""
            SELECT id, state, purpose, revision_id, suite_revision_id
            FROM public.analysis_rule_runs
            WHERE id = :run_id
            """
        ),
        {"run_id": run_id},
    )
    run = run_row.mappings().first()
    if run is None:
        raise ValueError(f"run_id={run_id!r} が見つかりません")
    if run["purpose"] != "test":
        raise ValueError("本番適用には purpose='test' の run が必要です")
    if run["state"] != "passed":
        raise ConflictError(f"run の state が 'passed' ではありません: state={run['state']!r}")
    if str(run["revision_id"]) != revision_id:
        raise ConflictError(f"run の revision_id が一致しません: run={run['revision_id']} 期待={revision_id}")

    # 全件通過の確認（invalidated_at IS NULL かつ validation_error IS NULL）
    fail_count_row = await db.execute(
        text(
            f"""
            SELECT COUNT(*) FROM public.analysis_rule_run_results
            WHERE run_id = :run_id
              AND (validation_error IS NOT NULL OR invalidated_at IS NOT NULL)
            """
        ),
        {"run_id": run_id},
    )
    fail_count = fail_count_row.scalar_one()
    if fail_count > 0:
        raise ConflictError(f"テスト結果に {fail_count} 件の不合格があります。本番適用を拒否します")

    total_count_row = await db.execute(
        text(
            f"""
            SELECT COUNT(*) FROM public.analysis_rule_run_results
            WHERE run_id = :run_id
            """
        ),
        {"run_id": run_id},
    )
    total_count = total_count_row.scalar_one()
    if total_count == 0:
        raise ConflictError("テスト結果が0件です。本番適用を拒否します")

    # active 参照を更新
    updated = await db.execute(
        text(
            f"""
            UPDATE public.analysis_policies
            SET active_revision_id = :revision_id,
                activation_state   = 'active',
                lock_version       = lock_version + 1,
                updated_at         = NOW()
            WHERE policy_type  = :policy_type
              AND lock_version = :expected_lock
            """
        ),
        {
            "revision_id": revision_id,
            "policy_type": policy_type,
            "expected_lock": lock_version,
        },
    )
    if updated.rowcount == 0:
        raise ConflictError("lock_version 競合: 別のリクエストが先に更新しました")

    await db.commit()
    return {"activated": True, "revision_id": revision_id}


# ---------------------------------------------------------------------------
# get_history
# ---------------------------------------------------------------------------


async def get_history(
    db: AsyncSession,
    policy_type: str,
    *,
    cursor: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """
    GET {base}/history

    変更前後を参照可能な変更履歴を返す。
    """
    _validate_policy_type(policy_type)

    cursor_filter = "AND apr.id > :cursor" if cursor else ""
    params: dict[str, Any] = {"policy_type": policy_type, "limit": limit + 1}
    if cursor:
        params["cursor"] = cursor

    rows = await db.execute(
        text(
            f"""
            SELECT
                apr.id,
                apr.parent_revision_id,
                apr.content_digest,
                apr.created_by,
                apr.created_at
            FROM public.analysis_policy_revisions apr
            JOIN public.analysis_policies ap ON ap.id = apr.policy_id
            WHERE ap.policy_type = :policy_type
              {cursor_filter}
            ORDER BY apr.created_at DESC
            LIMIT :limit
            """
        ),
        params,
    )
    items_all = rows.mappings().all()
    has_next = len(items_all) > limit
    items = [dict(r) for r in items_all[:limit]]
    next_cursor = items[-1]["id"] if has_next and items else None

    return {"items": items, "has_next": has_next, "next_cursor": str(next_cursor) if next_cursor else None}


# ---------------------------------------------------------------------------
# get_revision_detail
# ---------------------------------------------------------------------------


async def get_revision_detail(db: AsyncSession, revision_id: str) -> dict[str, Any] | None:
    """
    GET {base}/revisions/{id}

    指定版の全内容（指示文、ルール、語句）を返す。
    """
    rev_row = await db.execute(
        text(
            f"""
            SELECT
                apr.id,
                apr.policy_id,
                apr.parent_revision_id,
                apr.content_digest,
                apr.created_by,
                apr.created_at,
                aiv.body AS instruction_body
            FROM public.analysis_policy_revisions apr
            LEFT JOIN public.analysis_instruction_versions aiv
                ON aiv.id = apr.instruction_version_id
            WHERE apr.id = :revision_id
            """
        ),
        {"revision_id": revision_id},
    )
    rev = rev_row.mappings().first()
    if rev is None:
        return None

    # ルールと語句一覧
    rules_row = await db.execute(
        text(
            f"""
            SELECT
                ar.id           AS rule_id,
                arv.id          AS rule_version_id,
                arv.title,
                arv.context_instruction,
                arr.is_deleted,
                w.id            AS word_id,
                w.kind          AS word_kind,
                w.text          AS word_text,
                w.position
            FROM public.analysis_revision_rules arr
            JOIN public.analysis_rules ar ON ar.id = arr.rule_id
            JOIN public.analysis_rule_versions arv ON arv.id = arr.rule_version_id
            LEFT JOIN public.analysis_rule_words w ON w.rule_version_id = arv.id
            WHERE arr.revision_id = :revision_id
            ORDER BY arv.id, w.position
            """
        ),
        {"revision_id": revision_id},
    )
    rule_rows = rules_row.mappings().all()

    return {
        "revision": dict(rev),
        "rules": [dict(r) for r in rule_rows],
    }


# ---------------------------------------------------------------------------
# C95: 最新成功 job の items を取得するクエリヘルパー
# ---------------------------------------------------------------------------


async def get_latest_job_items(
    db: AsyncSession,
    source_message_id: str,
) -> list[dict[str, Any]]:
    """
    C95: 本番完売判断用の対象 items を取得する。

    対象 source_message_id に紐づく extraction_jobs のうち
    status='done' かつ created_at が最新の 1 件の extraction_items のみを返す。
    """
    rows = await db.execute(
        text(
            f"""
            WITH latest_job AS (
                SELECT id FROM {TCG_SCHEMA}.extraction_jobs
                WHERE source_message_id = :msg_id
                  AND status = 'done'
                ORDER BY created_at DESC
                LIMIT 1
            )
            SELECT ei.id, ei.extraction_job_id,
                   ei.line_start, ei.line_end,
                   ei.raw_product_name, ei.raw_quantity, ei.raw_price,
                   ei.raw_unit, ei.raw_state, ei.raw_memo,
                   ei.resolved_work_id, ei.created_at
            FROM {TCG_SCHEMA}.extraction_items ei
            WHERE ei.extraction_job_id = (SELECT id FROM latest_job)
            ORDER BY ei.line_start
            """
        ),
        {"msg_id": source_message_id},
    )
    return [dict(r) for r in rows.mappings().all()]


# ---------------------------------------------------------------------------
# カスタム例外
# ---------------------------------------------------------------------------


class ConflictError(Exception):
    """楽観的ロック競合または版検証失敗。"""


__all__ = [
    "get_current_state",
    "get_revision_rules",
    "create_draft_revision",
    "save_test_suite",
    "start_test_run",
    "get_test_run_result",
    "activate_revision",
    "get_history",
    "get_revision_detail",
    "get_latest_job_items",
    "ConflictError",
    "VALID_POLICY_TYPES",
    "ALLOWED_WORD_KINDS",
]
