# 引き継ぎ — auth-self-hosted-passkey

> この文書は何か：ログインの自社化とパスキー追加の設計を、次のセッションが続きから進めるための引き継ぎです。

親: [docs/specs/auth-login/README.md](../../specs/auth-login/README.md)

**日付**: 2026-10-13  
**書いた人**: 設計パートナー（Opus・ccopusgo セッション）

## 状態（2026-10-13 時点・証拠つき）

| 段階 | 状態 | 証拠 |
|---|---|---|
| 設計案 | 作成済み | `docs/handoff/auth-self-hosted-passkey/design.md` |
| 設計審査 | 済み（Fable 2 回。審査 2 は「示した直し方どおりに直せば再審査不要」） | design.md §10 |
| PO 承認 | 済み（2026-10-13 チャット「y」） | `docs/specs/auth-login/ideal-state.md` |
| 文書の保存 | コミット 2 件を push 済み（4a6b15550・3fd159513） | ブランチ release/auth-self-hosted-passkey-design |
| PR 提出 | **未提出** | `gh pr list --head release/auth-self-hosted-passkey-design` が空 |
| 実装 | 未着手 | — |

## 次の一手（順番どおり）

1. この引き継ぎ書のコミットを含めて、PR を出す（docs のみ・Draft にしない）
   - 本文は下の「PR 本文の下書き」をそのまま使い、「触るファイル」にこの handoff.md を足す
   - 提出前に関所を通す: `bash scripts/dev/validate-pr-body.sh < 本文ファイル`
   - ローカルの main が古いと関所が終わらないことがある（2026-10-13 実測。main..HEAD が約 1960 コミット）。その場合は `scripts/dev/validate-pr-body.sh:304-317` と同じ環境変数で `node scripts/check-process-artifacts.js` を直接実行し、環境変数 MOCK_BASE_REF を origin/main にする
   - 「削除するファイル:」は、行を 1 行でも消したファイルを書く決まり（`scripts/check-process-artifacts.js` の削除行の判定）。今回は ADR-138 と docs/adr/README.md
   - バッククォートの中は実在するパスだけ（関所が実在を確かめる）。API の経路・環境変数・新しく作る予定のファイルは囲まない
2. PR のマージは、ルールどおりに判断する（docs のみ。マージの判断は次のセッションで規則を確かめてから）
3. 便1（migration）の実装カードを作る → カードチェック → PO に実装承認を y/n で聞く。便ごとに「カード → 実装承認 → Sonnet が実装 → Fable がコード審査 → CI → 危険便は GO」

## 途中で分かった注意

- Sonnet は週の利用上限に達した（2026-10-13 夕方。回復は 10/16 18:00 JST）。それまで調査・実装の委任はできない
- 担当のコマンドに「psql」の語と「|」が両方あると、フック psql-write-guard が誤検知して止める。言い換えて再試行するのは迂回になるので禁止
- 本番 backend は `docker run` で入れ替える作り（`scripts/blue-green-cutover.sh`）。compose のサービス名では見つからない。コンテナ名 astro-webapp-backend-1 で読む
- ADR 索引のスクリプトは、状態の欄に「承認」の語があると Accepted と判定する（`scripts/generate-adr-index.js:59`）。未承認の ADR に「未承認」と書かない
- PO の端末で実行した読み取りスクリプト（結果は PO の Mac の /tmp/CC報告ファイル/auth-*）はセッション専用の置き場にあり、次のセッションからは見えない。必要な事実は recon.md の P1〜P13 に転記済み

## 最初の依頼（審査用アカウント）

- review@salesanchor.jp は Firebase に存在し（停止なし）、public.users にも id=10・tenant 6・使用中で存在する（recon P6・P13）。ログインできない原因はパスワード不一致だけ
- 直し方は PO に案内済み: ログイン画面「パスワードをお忘れの方」→ さくらの Web メール（review の受信箱）で再設定リンクを開く。PO が実施したかは未確認

## PR 本文の下書き

```
## なぜ
ログインの判定を Firebase から自社サーバーへ移し、パスキー（顔・指紋）でのログインを足す方針を、ADR-1013 と設計仕様書にまとめるため。PO が 2026-10-13 にチャットで「y」と承認済み。

## 何を変えたか
- ADR-1013（Accepted）を新規追加。ADR-138（password_hash 列廃止）を Superseded に更新
- 設計仕様書 docs/specs/auth-login/（README・ideal-state・kgi）を新規追加し、索引を更新
- recon.md・design.md・handoff.md を docs/handoff/auth-self-hosted-passkey/ に追加
- ADR 索引（docs/adr/README.md・FEATURE-INDEX.md）を再生成

## 変更規模
大（11ファイル・文書のみ）

## 概要
- docs のみ。製品コード・DB・本番には触れていない
- 実装は未着手
- PO 承認: 2026-10-13 チャットで「y」
- Fable による審査 2 回（REVISE → 反映済み）
- 計画: 便0〜6 の段階実装（詳細は design.md）

---

### 標準ワークフロー確認

- recon: docs/handoff/auth-self-hosted-passkey/recon.md
- 設計: docs/handoff/auth-self-hosted-passkey/design.md
- 対象ADR: ADR-1013
- 設計仕様書（あるべき姿）: docs/specs/auth-login/README.md
- 触るファイル: docs/adr/ADR-1013-self-hosted-auth-and-passkey.md, docs/adr/ADR-138-remove-password-hash.md, docs/adr/FEATURE-INDEX.md, docs/adr/README.md, docs/specs/README.md, docs/specs/auth-login/README.md, docs/specs/auth-login/ideal-state.md, docs/specs/auth-login/kgi.md, docs/handoff/auth-self-hosted-passkey/recon.md, docs/handoff/auth-self-hosted-passkey/design.md, docs/handoff/auth-self-hosted-passkey/handoff.md
- 削除するファイル: docs/adr/ADR-138-remove-password-hash.md, docs/adr/README.md

### 共通
- [x] 文書のみの変更（テスト対象なし）

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```
