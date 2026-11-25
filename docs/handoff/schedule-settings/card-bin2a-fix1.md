# 実装カード 便2a 直し1（マージ前審査の REVISE 3 件）

- 元のカード: docs/handoff/schedule-settings/card-bin2a.md（委任の定型・報告の形・停止条件はそのまま効く）
- ブランチ: release/schedule-settings-bin2a（PR #5759。head f8e0e0789 から積む）
- 発行: Opus（設計統括）2026-11-25。PO の委任（「1,このセッションでは…PRマージ、デプロイまで完走させてくれ。」）の範囲内の直し

## なぜ

マージ前審査（reviewer・opus）が REVISE。必須チェック 2 本（会社のひな形の形の差0・Frontend unit tests）が赤。Opus が手元で 3 件とも事実を確かめた。

## 触るファイル（この 4 つだけ）

1. `migrations/20261126_100000_create_calendar_categories.sql`
2. `frontend/src/lib/apiErrorReason.ts`（元のカードに無い。この直しで足す）
3. `frontend/src/locales/ja.json` と `frontend/src/locales/en.json`
4. `docs/handoff/cloud-case-ai/stage1-column-class.tsv`

## 直し

### 直し1 関数の本文を会社のひな形と文字単位で同じにする

- 事実: 移行 `migrations/20261126_100000_create_calendar_categories.sql:64-68` の `$function$` の中は 12 桁と 14 桁の字下げ。会社のひな形 `backend/app/services/tenant.py:2169-2173` は 6 桁と 8 桁。
- 直し: 移行の `:64-68` の 5 行を、`tenant.py:2169-2173` と同じ空白数にする（`BEGIN` 6 桁・中の 2 行 8 桁・`END;` 6 桁・閉じの `$function$` 6 桁）。他の行は触らない。
- 変更前（移行 :64-68）:

```
            BEGIN
              NEW.updated_at = NOW();
              RETURN NEW;
            END;
            $function$
```

- 変更後:

```
      BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
      END;
      $function$
```

### 直し2 「見つからない」の表に予定の種類を足す

- 事実: 裏側は新しく 404 `not_found:calendar_category` を返す。`frontend/src/lib/apiErrorReason.ts:57` の `NOT_FOUND_TARGET_KEYS` に行が無く、`src/lib/apiErrorReason.test.ts` の「every not_found target used in backend/app is in the table」が落ちる。
- 直し:
  - `apiErrorReason.ts` の表の `calendar_owner` 行の次に `calendar_category: "apiError.notFoundTarget.calendar_category",` を足す。
  - `ja.json` の `apiError.notFoundTarget` の `calendar_owner` の次に `"calendar_category": "予定の種類",` を足す。
  - `en.json` の同じ場所に `"calendar_category": "The event category",` を足す。

### 直し3 表の壊れた 1 行を元に戻す

- 事実: `docs/handoff/cloud-case-ai/stage1-column-class.tsv` の 566 行目（`tenant_*` `calendar_events` `calendar_type` `allow` …）だけ列が 5 つ。他の行は 6 つ。`allow` と理由の間のタブが消えている。
- 直し: 566 行目の `allow` の後ろにタブを 1 つ戻す。他の行は触らない。

## 確かめ（生の出力をファイルに残す）

- `awk -F'\t' 'NF!=6' docs/handoff/cloud-case-ai/stage1-column-class.tsv | wc -l` が 0。
- `git diff -- backend/app/services/tenant.py` が空（ひな形は触らない）。
- 移行の `:64-68` と `tenant.py:2169-2173` を `diff` で比べて差が無い。
- 手元の PostgreSQL 16 で、会社のひな形の形の差の台本（CI の「会社のひな形の形の差0（実DB）」と同じもの）を流して FAIL 0。台本が手元で動かないときは、そのことと理由の原文を書く（止まらない）。
- `cd frontend && npx vitest run src/lib/apiErrorReason.test.ts src/pages/schedule` が全部通る。
- ja.json と en.json の `notFoundTarget` のキー数が同じ。
- 提出前: `bash scripts/dev/check-before-submit.sh`。
- commit（`--no-verify` は使わない）→ `git push -u origin HEAD` → `git log origin/release/schedule-settings-bin2a -1 --oneline`。

## 停止する条件（BLOCKED: で返す）

- 上の 4 つ以外を変える必要が出た。
- 直し1 をしても形の差が残った（残った物の名前と差の原文を書く）。
- 上の試験が、この直しと関係なく落ちる。

END OF CARD
