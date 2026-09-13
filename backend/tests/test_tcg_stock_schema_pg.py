"""Real disposable CI PostgreSQL contract, including source-removal refusal.

Each fixture has its own database. CI service shutdown owns disposal.
These tests require actual CI execution before PostgreSQL acceptance is claimed.
"""

import copy
import os
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import psycopg2
import pytest
from psycopg2 import sql
from psycopg2.extras import Json
from sqlalchemy.engine import make_url

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"
MIGRATION = "20260913_230000_tcg_stock_projection.sql"
SCHEMA = "tenant_951"
TABLES = {"tcg_stock_offers", "tcg_stock_events", "tcg_restock_plans", "tcg_stock_publications", "tcg_stock_control", "tcg_stock_inbox"}
EMPTY = {"offer": None, "plans": [], "validated_inputs": []}
DIGEST = "a" * 64
STAMP = "2026-09-13T00:00:00Z"
RAW_FIELDS = ("raw_product_name", "raw_quantity", "raw_price", "raw_unit", "raw_state", "raw_memo", "raw_work_name")


def query(connection, statement, params=None):
    with connection.cursor() as cursor:
        cursor.execute(statement, params)
        return cursor.fetchall() if cursor.description else []


def apply(connection):
    query(connection, (MIGRATIONS / MIGRATION).read_text())


def bootstrap(connection, schema):
    query(connection, (MIGRATIONS / "20260906_120000_create_tcg_tables_t001.sql").read_text().replace("tenant_001", schema))
    query(connection, (MIGRATIONS / "20260910_010000_tcg_import_message_links.sql").read_text())


@contextmanager
def database(partial=False):
    assert os.getenv("GITHUB_ACTIONS") == "true", "Actual disposable GitHub Actions PostgreSQL required"
    configured = os.getenv("RLS_ADMIN_DATABASE_URL")
    assert configured, "RLS_ADMIN_DATABASE_URL required; cannot skip acceptance"
    url = make_url(configured)
    assert url.host in ("localhost", "127.0.0.1"), "Refuse nonlocal server"
    assert url.database == "jarvis_test_db", "Refuse non-test administration database"
    kwargs = dict(host=url.host, port=url.port, user=url.username, password=url.password)
    name = "tcg_stock_test_" + uuid4().hex
    admin = psycopg2.connect(dbname=url.database, **kwargs)
    admin.autocommit = True
    try:
        with admin.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    finally:
        admin.close()
    connection = psycopg2.connect(dbname=name, **kwargs)
    try:
        query(connection, "CREATE SCHEMA tenant_951; CREATE SCHEMA tenant_952; CREATE SCHEMA tenant_953; CREATE SCHEMA tenant_954")
        if partial:
            bootstrap(connection, "tenant_954")
            query(connection, "ALTER TABLE tenant_954.source_messages RENAME TO stock_missing_source_messages")
        else:
            bootstrap(connection, "tenant_951")
            bootstrap(connection, "tenant_952")
            apply(connection)
        connection.commit()
        yield connection
    finally:
        connection.close()


@pytest.fixture
def pg():
    with database() as connection:
        yield connection


def rejects(connection, operation, error=psycopg2.Error):
    connection.commit()
    try:
        with pytest.raises(error):
            operation()
            connection.commit()
    finally:
        connection.rollback()


def seed(connection, schema=SCHEMA):
    channel = str(query(connection, f"SELECT id FROM {schema}.supplier_channels ORDER BY id LIMIT 1")[0][0])
    product, unit, condition, source, target = [str(uuid4()) for _ in range(5)]
    query(connection, f"INSERT INTO {schema}.tcg_products(id,code,japanese_title,category_class,is_active) VALUES(%s,%s,'商品A','Box',true)", (product, product[:8]))
    query(connection, f"INSERT INTO {schema}.units(id,code,canonical,is_active) VALUES(%s,%s,'BOX',true)", (unit, unit[:8]))
    query(connection, f"INSERT INTO {schema}.conditions(id,code,canonical,is_active) VALUES(%s,%s,'未開封',true)", (condition, condition[:8]))
    query(connection, f"INSERT INTO {schema}.source_messages(id,supplier_channel_id,raw_text,raw_sha256,is_active,line_posted_at) VALUES(%s,%s,'商品A',%s,true,%s)", (source, channel, DIGEST, STAMP))
    query(connection, f"INSERT INTO {schema}.tcg_distribution_targets(id,name,spreadsheet_id,sheet_name) VALUES(%s,'target','sheet-id','在庫')", (target,))
    connection.commit()
    return dict(channel=channel, product=product, unit=unit, condition=condition, source=source, target=target)


def evidence():
    return {"format_version": 5, "field_evidence": {key: [] for key in RAW_FIELDS}, "shipping": {"label": "", "evidence": []}, "clauses": []}


def event_values(refs, event_id=None, item_id=None):
    selector = dict(channel_id=refs["channel"], product_id=None, unit_id=None, condition_id=None, price=None, shipping_label=None,
                    evidence={key: [] for key in ("product_id", "unit_id", "condition_id", "price", "shipping_label")})
    payload = None
    if item_id:
        payload = {key: "" for key in RAW_FIELDS}
        payload.update(raw_product_name="商品A", resolved_work_id=None, line_start=1, line_end=1, evidence_payload=evidence())
    inputs = dict(schema_version=1, engine_version="stock-test", prompt_version="v5", policy_version="1", work_reference_sha256=None,
                  source_sha256=DIGEST, extraction_payload=payload, correction_ids=[])
    result = dict(schema_version=1, kind="item" if item_id else "no_item", extraction_item_id=item_id,
                  product_id=None, unit_id=None, condition_id=None, quantity=None, price=None, status=None, exclusion=None,
                  pid_resolved=False, unit_resolved=False, needs_review=False, pid_basis=None, unit_basis=None, condition_basis=None,
                  review_reasons=[], evidence={}, correction_ids=[],
                  proposal=dict(event_kind="stock_set" if item_id else "ignore", target_selector=selector, patch={}, review_reasons=[]))
    return dict(id=event_id or str(uuid4()), source_message_id=refs["source"], extraction_item_id=item_id, offer_id=None,
                event_kind="stock_set" if item_id else "ignore", event_key=str(uuid4()), engine_version="stock-test", source_posted_at=STAMP,
                evidence={}, patch={}, decision="pending", review_reasons=[], before_values=copy.deepcopy(EMPTY), after_values=copy.deepcopy(EMPTY),
                analysis_input_snapshot=inputs, analysis_result_snapshot=result,
                analysis_input_digest=DIGEST, analysis_result_digest=DIGEST, proposal_input_digest=DIGEST)


def insert(connection, table, values, schema=SCHEMA):
    columns = list(values)
    statement = sql.SQL("INSERT INTO {}.{} ({}) VALUES ({})").format(
        sql.Identifier(schema), sql.Identifier(table), sql.SQL(",").join(map(sql.Identifier, columns)),
        sql.SQL(",").join(sql.Placeholder() for _ in columns))
    query(connection, statement, tuple(Json(value) if isinstance(value, (dict, list)) else value for value in values.values()))


def offer_values(refs, **overrides):
    values = dict(id=str(uuid4()), supplier_channel_id=refs["channel"], product_id=refs["product"], unit_id=refs["unit"],
                  condition_id=refs["condition"], price="100", shipping_label=None, shipping_evidence=[], quantity="10", availability="available")
    values.update(overrides)
    return values


def make_applied(connection, refs):
    job, item_id, event_id = [str(uuid4()) for _ in range(3)]
    query(connection, f"INSERT INTO {SCHEMA}.extraction_jobs(id,source_message_id,status) VALUES(%s,%s,'done')", (job, refs["source"]))
    query(connection, f"INSERT INTO {SCHEMA}.extraction_items(id,extraction_job_id,raw_product_name,line_start,line_end) VALUES(%s,%s,'商品A',1,1)", (item_id, job))
    offer = offer_values(refs, quantity_event_id=event_id, price_event_id=event_id, condition_event_id=event_id, validation_event_id=event_id)
    insert(connection, "tcg_stock_offers", offer)
    audit_offer = dict(offer, revision=1)
    values = event_values(refs, event_id, item_id)
    values.update(offer_id=offer["id"], decision="applied", applied_offer_revision=1, applied_at=STAMP,
                  after_values=dict(offer=audit_offer, plans=[], validated_inputs=[
                      dict(field_key=key, event_id=event_id, proposal_input_digest=DIGEST)
                      for key in ("condition", "identity", "price", "quantity")]))
    insert(connection, "tcg_stock_events", values)
    return offer["id"], event_id


def publication_values(connection, refs, kind="legacy_stock", state="building"):
    rollout, revision = query(connection, f"SELECT rollout_id,revision FROM {SCHEMA}.tcg_stock_control")[0]
    target = query(connection, f"SELECT {SCHEMA}.stock_target_value(t) FROM {SCHEMA}.tcg_distribution_targets t WHERE id=%s", (refs["target"],))[0][0]
    manifest = dict(schema_version=1, kind=kind, rollout_id=str(rollout), control_revision=revision, watermark_seq=None,
                    source_ids=[refs["source"]], offer_revisions=[], target_snapshots={refs["target"]: target},
                    validation=dict(blocking_reasons=[], warning_reasons=[]), baseline_publication_id=None)
    result = dict(target_snapshot=target, status="pending", attempts=[], verified_rows=None, verified_sha256=None,
                  verified_at=None, review_reason=None, reservation_attempt_id=None)
    return dict(id=str(uuid4()), state=state, schema_version=1, input_manifest=manifest, rows=[["header"] * 12], row_count=0,
                rows_sha256=DIGEST if state=="ready" else None, ready_at=STAMP if state=="ready" else None,
                target_results={refs["target"]: result})


def test_repeat_and_existing_data(pg):
    refs = seed(pg)
    before = query(pg, f"SELECT row_to_json(s) FROM {SCHEMA}.source_messages s")
    control = query(pg, f"SELECT row_to_json(c) FROM {SCHEMA}.tcg_stock_control c")
    apply(pg)
    pg.commit()
    apply(pg)
    pg.commit()
    assert before == query(pg, f"SELECT row_to_json(s) FROM {SCHEMA}.source_messages s")
    assert control == query(pg, f"SELECT row_to_json(c) FROM {SCHEMA}.tcg_stock_control c")
    names = query(pg, "SELECT table_name FROM information_schema.tables WHERE table_schema=%s AND table_name=ANY(%s)", (SCHEMA, list(TABLES)))
    assert {row[0] for row in names} == TABLES
    columns = query(pg, "SELECT table_name,column_name FROM information_schema.columns WHERE table_schema=%s AND ((table_name='extraction_items' AND column_name='evidence_payload') OR (table_name='tcg_distribution_targets' AND column_name='active_publication_id'))", (SCHEMA,))
    assert len(columns) == 2
    assert query(pg, f"SELECT active_publication_id FROM {SCHEMA}.tcg_distribution_targets WHERE id=%s", (refs["target"],)) == [(None,)]
    registry = (MIGRATIONS.parent / "scripts/run_all_migrations.sh").read_text()
    assert registry.count("run_sql migrations/" + MIGRATION) == 1
    assert registry.index("run_sql migrations/20260913_150000_tcg_empty_box_condition.sql") < registry.index("run_sql migrations/" + MIGRATION)


def test_value_and_snapshot_constraints(pg):
    refs = seed(pg)
    for overrides in [dict(quantity=None), dict(availability="sold_out"), dict(quantity="-1"), dict(price="-1"),
                      dict(quantity="NaN"), dict(price="NaN"), dict(price="Infinity"), dict(quantity="Infinity"),
                      dict(availability="invalid"), dict(shipping_evidence={}), dict(shipping_evidence=None)]:
        rejects(pg, lambda overrides=overrides: insert(pg, "tcg_stock_offers", offer_values(refs, **overrides)))
    good = event_values(refs)
    ids = ["1", "2", "10", "9007199254740993", "9223372036854775807"]
    for name in ("analysis_input_snapshot", "analysis_result_snapshot"):
        good[name]["correction_ids"] = ids
    insert(pg, "tcg_stock_events", good)
    pg.commit()
    assert query(pg, f"SELECT analysis_input_snapshot->'correction_ids',analysis_result_snapshot->'correction_ids' FROM {SCHEMA}.tcg_stock_events WHERE id=%s", (good["id"],)) == [(ids, ids)]
    for invalid in [[str(uuid4())], [1], ["0"], ["-1"], ["1.5"], ["01"], ["9223372036854775808"], ["2", "1"], ["1", "1"]]:
        for name in ("analysis_input_snapshot", "analysis_result_snapshot"):
            row = event_values(refs)
            row[name]["correction_ids"] = invalid
            rejects(pg, lambda row=row: insert(pg, "tcg_stock_events", row))
    for key, value in [("analysis_input_digest", "a" * 63), ("analysis_result_snapshot", []), ("analysis_input_snapshot", None), ("evidence", [])]:
        row = event_values(refs)
        row[key] = value
        rejects(pg, lambda row=row: insert(pg, "tcg_stock_events", row))
    for path in [("kind",), ("proposal", "event_kind"), ("proposal", "target_selector", "channel_id"),
                 ("proposal", "target_selector", "evidence", "product_id")]:
        row = event_values(refs)
        target = row["analysis_result_snapshot"]
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = None
        rejects(pg, lambda row=row: insert(pg, "tcg_stock_events", row))
    for scope in ("selector", "evidence"):
        for mode in ("missing", "extra", "wrong_type"):
            row = event_values(refs)
            target = row["analysis_result_snapshot"]["proposal"]["target_selector"]
            if scope == "evidence":
                target = target["evidence"]
            key = next(iter(target))
            if mode == "missing":
                del target[key]
            elif mode == "extra":
                target["unexpected"] = []
            else:
                target[key] = 7
            rejects(pg, lambda row=row: insert(pg, "tcg_stock_events", row))
    for version in (None, 5.0, True):
        bad = evidence()
        bad["format_version"] = version
        assert query(pg, f"SELECT {SCHEMA}.stock_evidence_shape(%s)", (Json(bad),)) == [(False,)]


def test_event_integrity(pg):
    refs = seed(pg)
    for extra in [dict(decision="applied"), dict(decision="applied", offer_id=str(uuid4()), applied_at=STAMP),
                  dict(decision="applied", applied_offer_revision=1)]:
        row = event_values(refs)
        row.update(extra)
        rejects(pg, lambda row=row: insert(pg, "tcg_stock_events", row))
    offer, event = make_applied(pg, refs)
    pg.commit()
    rejects(pg, lambda: query(pg, f"UPDATE {SCHEMA}.tcg_stock_events SET patch=%s WHERE id=%s", (Json({"quantity": 0}), event)))
    rejects(
        pg,
        lambda: query(
            pg,
            f"DELETE FROM {SCHEMA}.source_messages WHERE id=%s",
            (refs["source"],),
        ),
        psycopg2.errors.ForeignKeyViolation,
    )
    assert query(
        pg,
        f"SELECT count(*) FROM {SCHEMA}.source_messages WHERE id=%s",
        (refs["source"],),
    ) == [(1,)]
    assert query(
        pg,
        f"SELECT count(*) FROM {SCHEMA}.tcg_stock_events WHERE id=%s",
        (event,),
    ) == [(1,)]
    other_channel = query(pg, f"SELECT id FROM {SCHEMA}.supplier_channels WHERE id<>%s LIMIT 1", (refs["channel"],))[0][0]
    rejects(pg, lambda: query(pg, f"UPDATE {SCHEMA}.source_messages SET supplier_channel_id=%s WHERE id=%s", (other_channel, refs["source"])))
    rejects(pg, lambda: query(pg, f"UPDATE {SCHEMA}.source_messages SET line_posted_at=line_posted_at+interval '1 hour' WHERE id=%s", (refs["source"],)))
    wrong = offer_values(refs, quantity_event_id=event)
    wrong["supplier_channel_id"] = str(other_channel)
    rejects(pg, lambda: insert(pg, "tcg_stock_offers", wrong))
    assert query(pg, f"SELECT quantity FROM {SCHEMA}.tcg_stock_offers WHERE id=%s", (offer,))[0][0] == 10


def test_deferred_transaction_integrity(pg):
    refs = seed(pg)
    offer, event = make_applied(pg, refs)
    pg.commit()
    assert query(pg, f"SELECT validation_event_id::text FROM {SCHEMA}.tcg_stock_offers WHERE id=%s", (offer,)) == [(event,)]
    original = query(pg, f"SELECT count(*) FROM {SCHEMA}.tcg_stock_offers")[0][0]
    invalid = offer_values(refs, quantity_event_id=str(uuid4()))
    rejects(pg, lambda: insert(pg, "tcg_stock_offers", invalid))
    assert query(pg, f"SELECT count(*) FROM {SCHEMA}.tcg_stock_offers")[0][0] == original
    pg.commit()
    second = psycopg2.connect(pg.dsn)
    try:
        query(pg, f"SELECT {SCHEMA}.stock_check_event(%s)", (event,))
        query(second, "SET LOCAL lock_timeout='100ms'")
        with pytest.raises(psycopg2.errors.LockNotAvailable):
            query(second, f"UPDATE {SCHEMA}.source_messages SET line_posted_at=line_posted_at+interval '1 hour' WHERE id=%s", (refs["source"],))
        second.rollback()
        pg.commit()
    finally:
        second.close()


def add_plan(connection, refs, offer, previous_event, **date_values):
    event_id, plan_id = str(uuid4()), str(uuid4())
    item_id, before = query(connection, f"SELECT extraction_item_id::text,after_values FROM {SCHEMA}.tcg_stock_events WHERE id=%s", (previous_event,))[0]
    plan = dict(id=plan_id, offer_id=offer, polarity="positive", certainty_raw="予定", date_kind="arrival", date_precision="day",
                date_raw="2026年9月14日", date_start="2026-09-14", date_end="2026-09-14", resolution="resolved", review_reason=None,
                source_event_id=event_id, revision=1)
    plan.update(date_values)
    after = copy.deepcopy(before)
    after["offer"]["revision"] += 1
    after["offer"]["validation_event_id"] = event_id
    after["plans"].append({key: value for key, value in plan.items() if key != "offer_id"})
    after["plans"].sort(key=lambda value: value["id"])
    after["validated_inputs"].append(dict(field_key="plan:" + plan_id, event_id=event_id, proposal_input_digest=DIGEST))
    after["validated_inputs"].sort(key=lambda value: value["field_key"])
    row = event_values(refs, event_id, item_id)
    row["analysis_result_snapshot"]["proposal"]["event_kind"] = "plan_assert"
    row.update(event_kind="plan_assert", decision="applied", offer_id=offer, before_values=before, after_values=after,
               applied_at=STAMP, applied_offer_revision=after["offer"]["revision"])
    query(connection, f"UPDATE {SCHEMA}.tcg_stock_offers SET revision=revision+1,validation_event_id=%s WHERE id=%s", (event_id, offer))
    insert(connection, "tcg_stock_events", row)
    insert(connection, "tcg_restock_plans", plan)
    return plan


def test_plan_and_publication_integrity(pg):
    refs = seed(pg)
    valid = [dict(), dict(date_precision="range", date_end="2026-09-16")]
    valid += [dict(resolution="unspecified", date_precision=precision, date_start=None, date_end=None)
              for precision in ("period", "unspecified")]
    valid += [dict(resolution="needs_review", date_precision=precision, date_start=None, date_end=None, review_reason="year_unresolved")
              for precision in ("day", "range", "period", "unspecified")]
    plans = []
    for dates in valid:
        offer, event = make_applied(pg, refs)
        pg.commit()
        plans.append(add_plan(pg, refs, offer, event, **dates))
        pg.commit()
    assert query(pg, f"SELECT count(*) FROM {SCHEMA}.tcg_restock_plans")[0][0] == len(valid)
    for dates in [dict(date_start="infinity"), dict(date_start="2026-09-15"), dict(date_precision="period"), dict(date_precision="unspecified"),
                  dict(resolution="unspecified"), dict(resolution="needs_review"), dict(date_precision="invalid"),
                  dict(resolution="unspecified", date_precision="period", date_start=None, date_end=None, date_raw="")]:
        plan = dict(plans[0], id=str(uuid4()), **dates)
        rejects(pg, lambda plan=plan: insert(pg, "tcg_restock_plans", plan), psycopg2.errors.CheckViolation)
    first = plans[0]
    rejects(pg, lambda: query(pg, f"UPDATE {SCHEMA}.tcg_restock_plans SET polarity='negative',revision=revision+1 WHERE id=%s", (first["id"],)))
    for mode in ("extra", "null", "type", "missing"):
        bad = publication_values(pg, refs)
        target = bad["target_results"][refs["target"]]
        if mode == "extra":
            target["extra"] = True
        elif mode == "null":
            target["status"] = None
        elif mode == "type":
            target["attempts"] = {}
        else:
            del target["verified_rows"]
        rejects(pg, lambda bad=bad: insert(pg, "tcg_stock_publications", bad))
    bad = publication_values(pg, refs, state="ready")
    bad["input_manifest"]["target_snapshots"][refs["target"]]["sheet_name"] = "different"
    bad["target_results"][refs["target"]]["target_snapshot"]["sheet_name"] = "different"
    rejects(pg, lambda: insert(pg, "tcg_stock_publications", bad))
    pub = publication_values(pg, refs, state="ready")
    insert(pg, "tcg_stock_publications", pub)
    pg.commit()
    rejects(pg, lambda: query(pg, f"UPDATE {SCHEMA}.tcg_stock_publications SET rows_sha256=%s WHERE id=%s", ("b" * 64, pub["id"])))
    rejects(pg, lambda: query(pg, f"UPDATE {SCHEMA}.tcg_stock_publications SET input_manifest=jsonb_set(input_manifest,'{{control_revision}}','99') WHERE id=%s", (pub["id"],)))
    attempt_id = str(uuid4())
    results = copy.deepcopy(pub["target_results"])
    result = results[refs["target"]]
    attempt = dict(attempt_id=attempt_id, request_key=str(uuid4()), request_hash=DIGEST, actor="test-admin", reason="contract test",
                   started_at=STAMP, finished_at=None, outcome="in_flight", error=None)
    result.update(status="in_flight", attempts=[attempt], reservation_attempt_id=attempt_id)
    query(pg, f"UPDATE {SCHEMA}.tcg_stock_publications SET state='delivering',target_results=%s WHERE id=%s", (Json(results), pub["id"]))
    query(pg, f"UPDATE {SCHEMA}.tcg_distribution_targets SET active_publication_id=%s WHERE id=%s", (pub["id"], refs["target"]))
    pg.commit()
    wrong_target = str(uuid4())
    query(pg, f"INSERT INTO {SCHEMA}.tcg_distribution_targets(id,name,spreadsheet_id,sheet_name) VALUES(%s,'other','other','other')", (wrong_target,))
    pg.commit()
    rejects(pg, lambda: query(pg, f"UPDATE {SCHEMA}.tcg_distribution_targets SET active_publication_id=%s WHERE id=%s", (pub["id"], wrong_target)))
    result.update(status="unknown", review_reason="outcome_unknown")
    attempt.update(outcome="unknown", error="timeout")
    query(pg, f"UPDATE {SCHEMA}.tcg_stock_publications SET target_results=%s WHERE id=%s", (Json(results), pub["id"]))
    pg.commit()
    rejects(pg, lambda: query(pg, f"UPDATE {SCHEMA}.tcg_distribution_targets SET active_publication_id=NULL WHERE id=%s", (refs["target"],)))
    query(pg, f"UPDATE {SCHEMA}.tcg_distribution_targets SET sheet_name='changed' WHERE id=%s", (refs["target"],))
    pg.commit()
    assert query(pg, f"SELECT target_results->%s->>'review_reason' FROM {SCHEMA}.tcg_stock_publications WHERE id=%s", (refs["target"], pub["id"])) == [("target_config_changed",)]
    result.update(status="succeeded", verified_rows=0, verified_sha256=DIGEST, verified_at=STAMP, reservation_attempt_id=None, review_reason="target_config_changed")
    attempt.update(outcome="succeeded", error=None, finished_at=STAMP)
    for key, value in (("verified_rows", 1), ("verified_sha256", "b" * 64)):
        bad_results = copy.deepcopy(results)
        bad_results[refs["target"]][key] = value
        rejects(pg, lambda bad_results=bad_results: query(pg, f"UPDATE {SCHEMA}.tcg_stock_publications SET state='completed',target_results=%s WHERE id=%s", (Json(bad_results), pub["id"])))
    query(pg, f"UPDATE {SCHEMA}.tcg_stock_publications SET state='completed',target_results=%s WHERE id=%s", (Json(results), pub["id"]))
    query(pg, f"UPDATE {SCHEMA}.tcg_distribution_targets SET active_publication_id=NULL WHERE id=%s", (refs["target"],))
    pg.commit()
    assert query(pg, f"SELECT state FROM {SCHEMA}.tcg_stock_publications WHERE id=%s", (pub["id"],)) == [("completed",)]
    mutated = copy.deepcopy(results)
    mutated[refs["target"]]["attempts"][0]["actor"] = "changed"
    rejects(pg, lambda: query(pg, f"UPDATE {SCHEMA}.tcg_stock_publications SET target_results=%s WHERE id=%s", (Json(mutated), pub["id"])))


def test_control_integrity(pg):
    refs = seed(pg)
    assert query(pg, f"SELECT mode,resume_mode,baseline_publication_id,approved_publication_id FROM {SCHEMA}.tcg_stock_control") == [("legacy", None, None, None)]
    query(pg, f"UPDATE {SCHEMA}.tcg_stock_control SET mode='paused',resume_mode='legacy',revision=revision+1")
    pg.commit()
    query(pg, f"UPDATE {SCHEMA}.tcg_stock_control SET mode='legacy',resume_mode=NULL,revision=revision+1")
    pg.commit()
    rejects(pg, lambda: query(pg, f"UPDATE {SCHEMA}.tcg_stock_control SET mode='shadow',revision=revision+1"))
    rejects(pg, lambda: query(pg, f"UPDATE {SCHEMA}.tcg_stock_control SET mode='projected',revision=revision+1"))
    rejects(pg, lambda: query(pg, f"UPDATE {SCHEMA}.tcg_stock_control SET rollout_id=%s,revision=revision+1", (str(uuid4()),)))
    baseline = publication_values(pg, refs, kind="baseline", state="ready")
    insert(pg, "tcg_stock_publications", baseline)
    query(pg, f"UPDATE {SCHEMA}.tcg_stock_control SET mode='shadow',baseline_publication_id=%s,revision=revision+1", (baseline["id"],))
    pg.commit()
    query(pg, f"UPDATE {SCHEMA}.tcg_stock_control SET mode='paused',resume_mode='shadow',watermark_seq=0,revision=revision+1")
    pg.commit()
    cutover = publication_values(pg, refs, kind="cutover", state="ready")
    cutover["input_manifest"].update(watermark_seq=0, baseline_publication_id=baseline["id"])
    insert(pg, "tcg_stock_publications", cutover)
    pg.commit()
    query(pg, f"UPDATE {SCHEMA}.tcg_stock_control SET mode='projected',resume_mode=NULL,approved_publication_id=%s,revision=revision+1", (cutover["id"],))
    pg.commit()
    assert query(pg, f"SELECT mode FROM {SCHEMA}.tcg_stock_control") == [("projected",)]
    rejects(pg, lambda: query(pg, f"UPDATE {SCHEMA}.tcg_stock_control SET mode='legacy',revision=revision+1"))


def test_inbox_integrity(pg):
    refs = seed(pg)
    row = dict(source_message_id=refs["source"], seq=1, state="pending", event_ids=[])
    insert(pg, "tcg_stock_inbox", row)
    pg.commit()
    rejects(pg, lambda: insert(pg, "tcg_stock_inbox", row))
    rejects(pg, lambda: query(pg, f"UPDATE {SCHEMA}.tcg_stock_inbox SET seq=2 WHERE source_message_id=%s", (refs["source"],)))
    rejects(pg, lambda: query(pg, f"UPDATE {SCHEMA}.tcg_stock_inbox SET state='settled' WHERE source_message_id=%s", (refs["source"],)))
    other = dict(refs, source=str(uuid4()))
    query(pg, f"INSERT INTO {SCHEMA}.source_messages(id,supplier_channel_id,raw_text,raw_sha256,is_active,line_posted_at) VALUES(%s,%s,'other',%s,true,%s)", (other["source"], refs["channel"], "b" * 64, STAMP))
    different = event_values(other)
    insert(pg, "tcg_stock_events", different)
    pg.commit()
    rejects(pg, lambda: insert(pg, "tcg_stock_inbox", dict(row, source_message_id=other["source"])))
    rejects(pg, lambda: query(pg, f"UPDATE {SCHEMA}.tcg_stock_inbox SET state='settled',event_ids=%s WHERE source_message_id=%s", (Json([different["id"]]), refs["source"])))
    event = event_values(refs)
    event.update(decision="ignored", review_reasons=["irrelevant"])
    insert(pg, "tcg_stock_events", event)
    query(pg, f"UPDATE {SCHEMA}.tcg_stock_inbox SET state='settled',event_ids=%s WHERE source_message_id=%s", (Json([event["id"]]), refs["source"]))
    pg.commit()
    assert query(pg, f"SELECT state FROM {SCHEMA}.tcg_stock_inbox WHERE source_message_id=%s", (refs["source"],)) == [("settled",)]
    rejects(pg, lambda: query(pg, f"UPDATE {SCHEMA}.tcg_stock_inbox SET event_ids='[]' WHERE source_message_id=%s", (refs["source"],)))


def test_existing_future_and_absent_tenants(pg):
    refs = seed(pg)
    other = seed(pg, "tenant_952")
    assert query(pg, "SELECT count(*) FROM information_schema.tables WHERE table_schema IN ('tenant_953','tenant_954')")[0][0] == 0
    rejects(pg, lambda: insert(pg, "tcg_stock_offers", offer_values(refs), schema="tenant_952"))
    own = offer_values(other)
    insert(pg, "tcg_stock_offers", own, schema="tenant_952")
    pg.commit()
    assert query(pg, "SELECT count(*) FROM tenant_951.tcg_stock_offers")[0][0] == 0
    assert query(pg, "SELECT count(*) FROM tenant_952.tcg_stock_offers")[0][0] == 1
    bootstrap(pg, "tenant_953")
    pg.commit()
    apply(pg)
    pg.commit()
    apply(pg)
    pg.commit()
    names = query(pg, "SELECT table_name FROM information_schema.tables WHERE table_schema='tenant_953' AND table_name=ANY(%s)", (list(TABLES),))
    assert {row[0] for row in names} == TABLES
    assert query(pg, "SELECT mode FROM tenant_953.tcg_stock_control") == [("legacy",)]
    with database(partial=True) as incomplete:
        rejects(incomplete, lambda: apply(incomplete))
        assert query(incomplete, "SELECT count(*) FROM information_schema.tables WHERE table_name=ANY(%s)", (list(TABLES),))[0][0] == 0
