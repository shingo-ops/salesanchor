# CI Guard Design — supplier_channels.supplier_id SSOT 保護

## 目的
supplier SSOT 移行（PR #3539）により `supplier_channels.supplier_id` は
`INTEGER` 型（`public.suppliers` FK）に統一された。
この列の削除・型変更が将来のマイグレーションで誤って行われることを CI で防ぐ。

## アプローチ
`.github/workflows/migration-guard.yml` にチェック9を追加する。

### 検出方法
チェック6（`.github/workflows/migration-guard.yml:343-391`）と同パターン:

1. `git diff BASE HEAD -- 'migrations/*.sql'` で追加行のみ抽出
2. SQLコメント行（`--` / `#`）を除外
3. `supplier_channels` を含む行があるか確認（なければスキップ）
4. 危険パターンを grep:
   - `DROP COLUMN [IF EXISTS] supplier_id`
   - `ALTER COLUMN supplier_id TYPE`
5. 検出された場合、PR本文に `ADR-NNN` 参照があれば警告付き通過、なければ `exit 1`

### ADR 脱出ハッチ
意図的な変更は ADR を起案し PR 本文に `ADR-NNN` を明記することで通過できる。
これによりシステムを壊さず意図的な変更は許容する。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| DROP COLUMN supplier_id を含む migration がブロックされる | migration-guard.yml の grep パターンが該当行を検出し exit 1 |
| ALTER COLUMN supplier_id TYPE を含む migration がブロックされる | 同上 |
| ADR番号がPR本文にあれば通過する | チェック6と同じ ADR 参照ロジック（grep -oiE 'ADR-[0-9]+'） |
| supplier_channels に無関係な migration は影響なし | supplier_channels 未参照ならスキップ |
| migration 変更なし PR は影響なし | DIFF_LINES が空ならスキップ |

## 外部事例
- Check 6 (DROP COLUMN/TABLE) が先例：ADR参照による意図的変更は許可する保守的ガードパターン
- 同プロジェクト ADR-155（チェック7-8）もマスタSSoT保護として同様アプローチ

## 守り手
- 破壊: なし（YAML追加のみ・アプリコード無変更）
- 戻し方: チェック9ブロック（`- name: supplier_channels...` から `exit 1` まで）を削除
- 測り方: migration-guard CI が当該パターンを含む PR で exit 1 を返すことを確認

## 関連
- `docs/handoff/supplier-ssot/ci-guard-recon.md` — recon
- PR #3539 — supplier SSOT migration（保護対象の移行）
- `.github/workflows/migration-guard.yml:343` — チェック6（参照パターン）
