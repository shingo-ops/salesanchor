# 設計審査記録: 本番の自動点検（qa-smoke）作り直し

- 審査: Opus（同一AIによる自己審査。独立した第二者レビューではない）
- 日時: 2026-10-30
- 対象: /tmp/CC報告ファイル/qa-smoke-design/design.md 第1版（Fable 作成、写し design-v1.md）→ 第2版
- 追加調査: Sonnet（/tmp/CC報告ファイル/qa-smoke-review/sonnet/）、Opus 照合（tenant-rules.txt・discord.txt・adr-nums.txt・viewer-role.txt）

## 第1版の判定: REVISE

| # | 指摘 | 根拠 | 第2版での扱い |
|---|---|---|---|
| R1 | 「ロールは閲覧（viewer）」という役割は存在しない。viewer_* は閲覧ページ用の別物 | tenant.py:50- の DEFAULT_ROLES 7 種、viewer_allowlist.py、models.py に role 列なし | *.view だけのカスタム役割を画面で作る形に修正。owner/admin 不可の理由（ADR-1048:16,23）を明記 |
| R2 | K3「1 行も書き換えない」は事実と違う。ログインで last_login と refresh トークンが変わる | auth.py:300-306,315 | 「業務データを変えない」に言い直し、副作用を明記 |
| R3 | 朝 7 時なら配備と重ならない、は根拠なし | 10/20〜10/30 で 7 時台 3 件 | 配備中かを確かめて見送る仕組みに変更 |
| R4 | 不合格通知の試験で secrets を変える手順は危険操作（secrets 変更）を増やす | CLAUDE.md の不可逆操作一覧 | 手動実行の入力で「わざと不合格」にする方式に変更 |
| R5 | tenant_001 は空の可能性 | data-durability-design/design.md:79 | リスク表に追加、段階 2 で件数確認 |
| R6 | Cloudflare の記載が docs 内で食い違う | gas-viewer-fresh-fast/design.md:455 ほか vs outage-recovery-watch/design.md:88 | リスク表に追加、U1 は段階 3 の手動実行で確定 |
| R7 | U2・U3・U4・U5・U6 は調べれば分かる | Sonnet 調査 Q3〜Q8 | すべて解消として記入 |

## 確認できた点（指摘なし）

- DISCORD_WEBHOOK_OWNER_PING は deploy.yml:670,683 で使用中（discord.txt）
- ADR 番号は ADR-1050 が最新で、1051 は空き（adr-nums.txt）
- tenant_001 は QA 用、tenant_004 は触れない、tenant_006 は QA 禁止（STANDARD-WORKFLOW.md:98）
- 利用者は 1 テナント限定（models.py:24-26）
- 管理者でない人は二段階の対象外（ADR-1048:23）

## 第2版の判定: APPROVE（設計として）

- 条件: D1〜D5 は PO 判断。U1（Cloudflare が GitHub の機械を通すか）と tenant_001 の件数は、段階 3・段階 2 で実物で確かめる前提を設計に明記済み。
- これは設計合格であり、PO 承認・実装承認ではない。
- 残る未確認: U1、U7（tenant_006 の扱い。D3 で解消）、U8（id=86 のメール。止血で影響なし）、U9（Playwright 公式の版。実装時に Context7）、tenant_001 の件数。
