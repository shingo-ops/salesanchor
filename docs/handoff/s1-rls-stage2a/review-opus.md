---
mode: handoff
---
# Opus 審査記録 — S1 段階②a（Google 接続設定 2 表の RLS）

> この文書は何か：設計書が実装に渡せる出来かを、同じ AI（Opus）が審査した記録です。独立した第二者のレビューではありません。

**日付**: 2026-10-16　**対象**: [design.md](design.md)、[recon.md](recon.md)、ADR-1018

**判定: APPROVE**

| 観点 | 結果 | 根拠 |
|---|---|---|
| 既存 ADR との整合 | 適合（ADR-1018 段階②「文脈を張らずに書く経路を先に直す」を同じ PR で実施。型は tenant_carrier_credentials と同一） | recon §1、design §2 |
| 実物との整合 | 適合（文脈なし経路は OAuth 戻り先 2 本のみ。commit 後の再設定漏れ 3 ファイルも修正対象に含めた。admin_engine 経由の利用なし） | recon §3 |
| 本番データとの整合 | 適合（calendar 0 行、Drive 1 行。既存行の値を変えない DDL のみ） | recon §2 |
| CI との整合 | 適合（新試験は CI の RLS 用 2 接続で動く。共通 bootstrap を変えないので他試験に波及しない。保護表一覧に 2 表は無い） | recon §5、scripts/migration-guard/protected-tables.txt |
| 受入条件の検証可能性 | 適合（全行が CI 試験・本番 SQL・ログ件数で○×判定可） | design §4 |
| 実装範囲の明確さ | 適合（変更 7 ファイル・触らない範囲を列挙） | design §2, §7、card.md |
| 審査中に直した点 | 試験の準備を共通一覧（rls_bootstrap.py）ではなく試験ファイル内に変更（共通一覧は tenants 作成前に流れ、FK で失敗するため） | recon §5 |

## 未解決事項

- OAuth 接続の実機通し確認（PO の GUI 操作が必要）。CI 試験 ④ で保存経路は代替確認する。完了報告で「未実施」と明記する。

## コード審査（2026-10-16・Opus）

**判定: APPROVE**（対象コミット 07f1227f2）

| 観点 | 結果 | 根拠 |
|---|---|---|
| 設計どおりか | 適合（migration は design §2-1 と同文、アプリ修正は §2-2 の #1〜#5 のみ、触らない範囲に変更なし） | /tmp/CC報告ファイル/s1-stage2/2a-diff-app.txt |
| 回帰試験の効き | ④: set_tenant_context が無いと app.tenant_id 空 → WITH CHECK が NULL → 42501 → db_error へ転送され `connected=true` の判定で落ちる。⑤: NullPool では commit で接続が閉じ、再設定が無いと 0 行 → 'primary' で落ちる | backend/tests/test_google_config_rls.py:230-317 |
| 試験の並列安全 | 適合（pytest は `--dist=loadfile` で同一ファイルを同じ作業者が順に流す。会社番号 980/981 は他試験で未使用） | backend/pyproject.toml:65 |
| 実行結果（担当の報告。生出力で確認） | 関連試験 112 passed／130 passed、ローカル実 PG で RLS 試験 5 passed、ruff 0 件 | /tmp/CC報告ファイル/s1-stage2/2a-test.txt、2a-test-related.txt、2a-test-rls-local.txt、2a-ruff.txt |
| 補足 | 初回 commit は pre-commit が `ruff` を PATH で見つけられず停止。導入済みの /Library/Frameworks/Python.framework/Versions/3.14/bin を PATH に足して通常どおりフックを通した（迂回なし） | /tmp/CC報告ファイル/s1-stage2/2a-commit.txt、2a-commit2.txt |

## CI 対応（2026-10-16・Opus 判断、担当 Sonnet 実施）

| 事象 | 原因（生ログ） | 対処 |
|---|---|---|
| マイグレーションSQL 実行（内部）失敗 | CI の検証用 DB に 2 表が無い（`relation "public.tenant_google_calendar_config" does not exist`）。この job は前提表を `.github/workflows/migration-test.yml` に最小定義で登録する方式 | tenant_carrier_credentials の RLS（20260609_090000）と同じ前例どおり、2 表の最小定義（原本の CREATE TABLE と同文）を登録。カードの範囲外だが試験用の前提登録のみで、本番には影響しない |
| guard-authoring/evaluation が error | PR の土台（main）が枝の祖先でない＝BEHIND（scripts/run-guard-evaluation.js の merge-base --is-ancestor が失敗） | origin/main を merge commit で取り込み |

回帰試験の効き（実測）: 修正を外した複製で試験 ④⑤ が失敗（2 failed, 3 passed）、修正ありで 5 passed（/tmp/CC報告ファイル/s1-stage2/2a-regress-without-fix.txt、2a-regress-with-fix.txt）。
