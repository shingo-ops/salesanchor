<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — デザイントークン週次監査の Discord 送信失敗

**仕事名**: design-token-audit-notify-path  
**日付**: 2026-11-24  
**対象ADR**: ADR-035（L5 Owner ping）／ ADR-067（デザイントークン強制）  
**担当**: architect（Opus 設計担当の自己審査。独立した第二者レビューではない）  
**基準**: origin/main bef5a7a8b（2026-11-23 18:44 JST）

---

## きっかけ

Discord の知らせの置き場の引っ越し（docs/handoff/discord-channel-consolidation/design.md の K4）を 2026-11-23 の月曜の週次で確かめた際に見つかった。K4 自体は合格。

## 既存 ADR 検索

- `git grep -il -E 'design-token-audit|discord-owner-ping|working-directory' -- docs/adr` → ADR-035 のみ（`docs/adr/ADR-035-external-state-verification.md:160` L5 Owner ping の台本の定義）。
- `docs/adr/FEATURE-INDEX.md:80` デザイントークン → ADR-033／066／067／068／073／013。送信の置き場所の指定に触れる ADR は無い。

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `.github/workflows/design-token-audit.yml:13` | job 全体の既定 `defaults.run.working-directory` の開始 |
| `.github/workflows/design-token-audit.yml:15` | 既定の作業場所が `frontend` |
| `.github/workflows/design-token-audit.yml:74` | Discord 通知の段（未使用トークンありのときだけ動く・75行の if） |
| `.github/workflows/design-token-audit.yml:82` | `bash scripts/notify/discord-owner-ping.sh "$MSG"`。作業場所 frontend からの相対なので frontend/scripts/notify/... を探して失敗する |
| `scripts/notify/discord-owner-ping.sh:31` | 送信台本の実体はリポジトリ根元の scripts/notify にある（frontend の下には無い） |
| `.github/workflows/test.yml:284` | 既存の CI 点検台本 `scripts/ci/check_ci_aggregators.py` を呼ぶ段（新しい点検を足す場所の候補） |
| `.github/workflows/test.yml:288` | 同じ job で `scripts/ci/check_queue_triggers.py` を呼ぶ段 |
| `.github/workflows/schema-check.yml:224` | `cd backend` の後に ../scripts/... を呼ぶ形（点検が cd を考えに入れないと誤って止める例） |

## 実測（2026-11-24 01:2x JST・読むだけ）

- 実行記録 45110699200（2026-11-23 04:15Z schedule）: 送る段で `bash: scripts/notify/discord-owner-ping.sh: No such file or directory`／`exit code 127`。HTTP 送信まで届いていない。
- 同じ仕組みの結論: 2026-11-09・11-16・11-23 の3回とも failure（gh api .../design-token-audit.yml/runs）。
- 監査の中身: 未使用トークン 40 件。Issue 作成の段は「未クローズのaudit Issueが既にあるためスキップ」（2026-06-01 作成の Issue が open のまま）。
- 同じ種類の間違いの数（試しの点検・全 workflow の run 内の `bash|sh|node|python scripts/...` 141 件を、作業場所と行頭の `cd` を考えに入れて git ls-files と照合）: 不一致は 1 件（上の 82 行）だけ。cd を考えに入れない版では schema-check.yml の2件が誤って出た。
- 似た形の brand-asset-monitor.yml・security-scan.yml は作業場所の指定が段ごと（job 既定ではない）なので、送る段は根元から動き問題なし。

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 送る段の作業場所は本当に frontend か | 実行記録の「No such file」と `.github/workflows/design-token-audit.yml:15` | ✅ 解消済み |
| 2 | 引っ越しの設定（送り先）が原因か | 同じ送り先を使う他2本が 11/23 に HTTP 204 で「定期の報告」に届いた | ✅ 解消済み（無関係） |
| 3 | 他にも同じ間違いがあるか | 試しの点検で 141 件中 1 件 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

## 補足

- 生の出力: /tmp/CC報告ファイル/discord-channels/ の k4-log-45110699200.txt・k4-fix-proto2.txt（リポジトリ外）。
