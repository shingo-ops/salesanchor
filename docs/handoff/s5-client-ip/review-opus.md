# 設計審査 — S5 接続元 IP の決め方（client-ip）

**日付**: 2026-10-16　**審査者**: Claude Opus（同一 AI による自己審査。独立した第二者レビューではない）
**対象**: docs/handoff/s5-client-ip/design.md、根拠 docs/handoff/s5-client-ip/recon.md

## 判定: APPROVE（設計合格）

設計合格は PO 承認・マージ・本番反映の承認を兼ねない。本件は 2026-10-16 の PO「y」（S5 着手・KGI K1〜K4）と ccopusgo の委任に基づいて実装へ進む。

## 確認した点

| 観点 | 結果 | 根拠 |
|---|---|---|
| 既存 ADR との整合 | ○ ADR-127 は回数制限の本体（backend/app/cache.py）と nginx 層を変えないと定める。本設計も両方を変えない | recon「既存 ADR の検索結果」、design §3 触らない |
| 実物との整合 | ○ 写し 4＋viewer.py 1 の行番号、呼び出し 6 か所、patch 先 2 件を recon で特定済み | recon §1・§2・§7 |
| 入口の前提 | ○ 本番の入口は nginx だけ（DNS 直・8000 番非公開）、12 location すべてで X-Real-IP を $remote_addr で上書き、本番 nginx -T でも同じ | recon §3 |
| 既存利用者への影響 | ○ 普通の利用者は XFF を送らないため、今も XFF 先頭＝$remote_addr＝X-Real-IP。キー・記録の値は変わらない | recon §3（$proxy_add_x_forwarded_for の挙動） |
| ヘルスチェック | ○ X-Real-IP 無しは request.client.host に戻る | recon §3、design §2 |
| 不具合の実在 | ○ 本番で偽の XFF が監査記録に残ることを再現 | recon §8 |
| 受入条件の検証可能性 | ○ K1 は grep 件数、K2 は CI 試験（変更前に赤を確認）、K3 は本番 DB と nginx 記録の照合、K4 は件数比較 | design §6 |
| 実装範囲の明確さ | ○ 触るファイル 8 つ・触らないファイルを明記。カードに変更前後を書く | design §3、card.md |
| 戻し方 | ○ Revert のみ。DB・設定の変更なし | design §8 |
| 危険パス | migrations/・deploy.yml・本番 scripts/ は含まない。ただし backend/app/auth・backend/app/routers を含むため process-artifacts gate が GO 記録を求める（初版で「不要」と誤記。CI で判明し PR 本文に委任 GO を記載） | design §3 |

## 審査の見落とし（2026-10-16 追記）

- backend/tests/test_real_redis_lockout.py を「手動実行用」と recon の記述のまま受け入れ、CI で走るかを確かめなかった。CI の失敗で判明し、:137 を X-Real-IP に修正。
- GO 記録の要否を危険パス 3 種だけで判定し、gate の対象（backend/app/auth・routers 等）を確かめなかった。

## 未解決事項

- なし（設計の範囲）。端末登録 line_import_devices.py:36 の扱いは別便として記録済み（design §4）。
