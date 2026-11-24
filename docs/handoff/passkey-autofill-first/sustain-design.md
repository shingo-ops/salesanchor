# パスキーの自動の候補 — 続けるための仕組み（設計案）

状態: 設計案（Opus 作成・審査役の審査待ち）。実装は PO の実装承認の後。
親: [design.md](design.md) ／ KGI: [../../specs/auth-login/kgi.md](../../specs/auth-login/kgi.md)「KGI 追加 — パスキーの自動の候補」 ／ 対象 ADR: ADR-1013・ADR-1063（毎日点検の形の前例）・ADR-1051（画面点検の通知）

## 1. 目的（PO の言葉）
PO 2026-11-24:「この仕組みを標準化して管理定着させて継続させるための機械的な仕組みも出来ているか事実ベースで…」「残っていることも不透明にせずに事実確認を実施すること」。
→ 人が覚えていなくても、(a) 壊す変更は合流できない、(b) 本番で壊れたら知らせが来る、(c) 効果の数が決まった日に自動で届く、の3つを機械で持つ。

## 2. 今ある仕組み（事実・2026-11-24 11:40 JST・origin/main 1ac87e46b）

| # | 仕組み | 事実 | 根拠 |
|---|---|---|---|
| A1 | 壊す変更を止める試験 | T1〜T12 が vitest にある。T7 はメール欄の `email webauthn` を確かめる | frontend/src/pages/login/LoginPage.test.tsx:451-453、frontend/src/lib/auth/passkey.test.ts:162-288 |
| A2 | 試験が合流の必須 | vitest（unit-run）は必須チェック「Lint & Dark Mode Check (ADR-067)」の集約に入る。画面を変えた PR で落ちれば赤 | .github/workflows/e2e.yml:89-121, 129-167。main の ruleset の必須一覧に同名あり（gh api rulesets 出力） |
| A3 | 決まりの置き場 | あるべき姿・KGI・設計が仕様書と索引から辿れる | docs/specs/README.md:82、docs/adr/FEATURE-INDEX.md:48、docs/specs/auth-login/kgi.md |
| A4 | 攻撃の見張り | パスキーの確認の失敗(401/429)が5分に10件超・1時間に20件超で知らせる | monitoring/loki/rules/jarvis/alerts.yml:10-33 |
| A5 | 毎朝の画面点検 | 本番のログイン画面を開き(S1)、パスワードでログインする(S2)。失敗だけ Discord | tests/prod-check/prod-ui.spec.ts:28-42、.github/workflows/prod-ui-check.yml:134-172。直近5回すべて success（gh run list） |
| A6 | ログイン記録 | public.auth_events に道ごとの記録。90日残る | migrations/001_create_auth_events.sql:6-16、backend/app/tasks/maintenance.py:179-189 |

## 3. 足りない所（事実）

| # | 足りない所 | 事実 |
|---|---|---|
| G1 | 効果の数（P5・KPI）を数える仕組みが無い | 12/8・12/24 の数えはどこにも予約されていない。auth_events を数えて知らせる係は無い（backend/app/tasks に passkey の語 0件: `git grep -il passkey origin/main -- backend/app/tasks` 出力なし） |
| G2 | 本番で「候補が出る設定」が消えても気づけない | 画面点検 S1 は欄が見えるかだけを見る。`webauthn` の語は tests/prod-check に 0件 |
| G3 | パスキーの道が本番で 5xx になっても知らせが無い | A4 は 401/429 だけを数える |

## 4. 残っている確かめ（事実・本番 auth_events、反映後 2026-11-24 03:27〜11:35 JST）
生の記録: 手元 scratchpad/sustain/passkey-after-deploy.tsv・pw-after-deploy.tsv（IP は読んでいない）

| KGI | 済み/残り | 事実 |
|---|---|---|
| P1 Mac の Chrome | 済み | 08:15 PO の id で passkey/login/verify 200（Mac・Chrome 157） |
| P1 Android の Chrome | 一部 | 11:20 verify 200 は「テスト管理者」の id。PO の id の成功は無い（PO 目視は「ログインまで出来た」） |
| P1 iPhone の Safari | 残り | 反映後 iPhone からの verify 0件（10:45 iPhone の Chrome で options だけ1件） |
| P2 すぐ確認が出る | 未判定 | 記録ではボタンからか候補からか区別できない。PO の目視が要る |
| P3 無いときの案内 | 残り | シークレット窓での目視はまだ |
| P4 Safari は今まで通り | 残り | P1 iPhone と同時に見られる |
| P5 パスワードも使える | 進行中 | 自動点検の係が 12回成功（最後 11:35）。14日分は 12/8 |
| P6・P7 | 済み | PR #5710 に migrations 無し・必須チェック緑 |

## 5. 変更の案（3つ・どれも本番の DB は読むだけ）

### 5-1. 週1回のパスキーの報告（G1・G3 を埋める）
- 新しい係 `backend/app/tasks/passkey_weekly_report.py`。形は ADR-1063 便6 の毎日点検（backend/app/tasks/tenant_isolation_daily_check.py）と同じ: DB を読むだけ・管理者用 Discord（環境変数 `ADMIN_NOTIFICATION_DISCORD_WEBHOOK`・tenant_isolation_daily_check.py:31 と同じ）・緑でも毎回送る（届かない＝止まっている）。
- 時刻: 毎週月曜 09:10 JST（celery beat、backend/app/celery_app.py の `tenant-isolation-daily-check` の隣）。
- 数えるもの（直近7日・auth_events だけ）:
  1. パスキーでのログイン成功（passkey/login/verify 200）の回数と人数
  2. PO のログインのうちパスキーの割合（KPI。PO の id は設定の値で持ち、コードに書かない）
  3. 自動点検の係のパスワードでのログイン成功があった日数（P5。7日中何日）
  4. パスキーの道（passkey/login/options・verify）の 5xx の回数
- 色: 赤＝(4) が1件以上、または (3) が7日未満。緑＝それ以外。
- 新しい表・列は作らない（P6 の約束どおり）。数えるのは auth_events だけ。
- 12/8・12/24 の数えは、この報告の 12/7 週・12/21 週の分で代える（14日＝2回分・30日＝報告4回＋その日の手元の数え1回）。

### 5-2. 毎朝の画面点検に1行足す（G2 を埋める）
- tests/prod-check/prod-ui.spec.ts の S1 に、ログイン画面のメール欄の autocomplete が `email webauthn` であることを足す。
- 落ちれば今ある仕組み（prod-ui-check.yml:134-172）で Discord に届く。新しい通知の道は作らない。

### 5-3. 残りの確かめを KGI の表に書く（§4）
- docs/specs/auth-login/kgi.md の「KGI 追加」に、P1〜P7 の済み/残りを日付つきで書く。

## 6. 選ばなかった案
- 毎日送る: パスキーの回数は1日0〜2回で、毎日では変化が見えない。週1にした。
- 手元の Mac の定期で数える: Mac を閉じていると動かない。本番の中の係なら止まらない（ADR-1063 便6 は 11/19〜11/24 で毎日届いた: k9 の記録）。
- 外部の監視の会社を使う: 費用が増え、データが外へ出る。

## 7. 弊害と対処
| 弊害 | 対処 |
|---|---|
| Discord の通知が週1通増える | 管理者用の部屋だけ。月曜の1通 |
| PO の id を間違えると KPI が0% | 設定の値が空なら KPI の行に「未設定」と書く。試験で確かめる |
| DB の負荷 | auth_events の (event_type, created_at) の索引あり（001:19-20）。7日分の数えだけ |

## 8. 受け入れ条件

| 基準 | 検証方法 |
|---|---|
| 月曜 09:10 JST に管理者用 Discord に報告が1通届く（反映後の最初の月曜） | celery-worker のログに係の succeeded と webhook の 204（K9 と同じ読み方） |
| 報告の (1)(3)(4) の数が、同じ時間の reader 鍵の数えと一致 | ai_ro.public__auth_events を同じ条件で数えて照合 |
| 5xx を混ぜた試験で赤、無ければ緑 | backend の試験（judge の単体試験）が CI の pytest 必須で緑 |
| 画面点検 S1 が本番で緑。`email webauthn` を外した見本では赤 | prod-ui-check の実行結果。見本は手元の試験の差し替えで確かめる |
| 新しい表・列なし | PR の差分に migrations が無い |

## 9. 続けるための仕組み（だれが・何で）
- 壊す変更: A1・A2（必須チェック）が止める。
- 本番で壊れた: 5-2（毎朝）と 5-1 の赤（毎週）と A4（すぐ）が知らせる。
- 効果: 5-1 が毎週数を届ける。読むのは Opus（毎週月曜の報告を読む）と PO。
- 報告そのものが止まった: 月曜に届かないことで分かる（ADR-1063 便6 と同じ考え方）。

## 10. 外部事例
- 同じ考え方（壊れたら知らせ・緑でも定期に送る）は、この会社の ADR-1063 便6 が前例。11/19〜11/24 で毎日届き、日数を数えられた（scratchpad k9 の記録）。
- パスキーの普及の事例は design.md・evidence.md に記載済み（Microsoft・Yahoo! JAPAN・adidas ほか）。この設計は普及策ではなく見張りのため、新しい外部事例は使わない。

## 11. 未解決（PO に戻すこと）
- 実装（5-1・5-2）に進むかは PO の実装承認が要る。
- 残りの確かめ（§4 の iPhone・シークレット窓・PO の id での Android）は PO の手元の機械が要る。
