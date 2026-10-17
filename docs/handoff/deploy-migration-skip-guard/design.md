# design: 前回デプロイが最後まで成功していなければ、DB 更新を必ず実行する（P6）

状態: 設計案作成済み・設計審査済み（Opus 自己審査）・PO 承認済み（2026-10-17 チャット「y」）・Sonnet 実装委任
参照: recon.md（同フォルダ）、ADR-082:48、ADR-092:33-39、ADR-115、ADR-1005

## 1. 目的（POの言葉）
デプロイが途中で止まったり置き換えられたりしても、次のデプロイで DB の更新（migration）とその前のバックアップが飛ばされないようにする。

## 2. KGI（○×で判定）
- KGI-1: 「前のデプロイが成功で終わっていない」状態で次のデプロイが走ったとき、migrations・バックアップ・nginx・smoke の4段が必ず実行される。
- KGI-2: 前のデプロイが成功で終わっている通常時は、今と同じく変更の無い段は skip される（所要時間が増えない）。

## 3. 変更前 → 変更後
- 変更前: paths-filter（.github/workflows/deploy.yml:33-59）が「push 直前の commit との差分」だけで判定。前の run が失敗・cancelled でも、その run の変更は差分に入らない。
- 変更後: paths-filter の直後に1段「前回デプロイの完了確認」を足す。
  - GitHub API で deploy.yml の main・成功 run の最新1件の head_sha を取る。
  - それが今回の push 直前の commit（github.event.before）と同じなら、paths-filter の結果をそのまま使う。
  - 違う・取れない・API が失敗した、のどれでも「全部実行」（安全側。ADR-082:48 と同じ考え方）。
  - 結果を steps.gate.outputs.{migrations,nginx,db_migrations} にまとめ、5か所（:178・:447・:528・:549・:629）の steps.changes.outputs を steps.gate.outputs に置き換える。
- 変えないもの: paths-filter のフィルタ定義（:36-59）、concurrency（:13-15）、.deploy_prev_sha とロールバック（:228-230・ADR-115）、run_all_migrations.sh、サーバー側。

## 4. 代替案と選んだ理由
| 案 | 中身 | 判断 |
|---|---|---|
| A | paths-filter の base に「最後に成功した SHA」を渡す | 不採用。push イベントで SHA を base にした挙動が公式 README に明記されていない（recon 未確認1） |
| B | migrations を毎回実行（ADR-082 をやめる） | 不採用。毎回 71〜459秒＋バックアップ 86〜90秒増える（recon 7）。必要なのは直近1000件で7回だけ |
| C | サーバーに「適用済み SHA」を新しく記録 | 不採用。成功した run の記録は GitHub に既にあり、同じ事実を2か所に持つことになる（SSOT 違反） |
| D（採用） | 前回成功 run の SHA が push 直前と一致しなければ全部実行 | 正の記録は GitHub の run 履歴1か所。判定できない時は安全側。フィルタ定義を複製しない |

## 5. 段の中身（実装役が書く形）
```yaml
      - name: Check previous deploy completed
        id: gate
        env:
          GH_TOKEN: ${{ secrets.PIPELINE_PAT }}
          BEFORE: ${{ github.event.before }}
          C_MIG: ${{ steps.changes.outputs.migrations }}
          C_NGX: ${{ steps.changes.outputs.nginx }}
          C_DB: ${{ steps.changes.outputs.db_migrations }}
        run: |
          last=$(gh api "repos/${{ github.repository }}/actions/workflows/deploy.yml/runs?branch=main&event=push&status=success&per_page=1" --jq '.workflow_runs[0].head_sha // ""' 2>/dev/null || echo "")
          if [ -n "$last" ] && [ "$last" = "$BEFORE" ]; then
            echo "前回デプロイは成功（${last:0:7}）→ 差分どおり"
            { echo "migrations=$C_MIG"; echo "nginx=$C_NGX"; echo "db_migrations=$C_DB"; } >> "$GITHUB_OUTPUT"
          else
            echo "::warning::前回の成功デプロイ(${last:0:7})が push 直前(${BEFORE:0:7})と違う／取れない → 全部実行"
            { echo "migrations=true"; echo "nginx=true"; echo "db_migrations=true"; } >> "$GITHUB_OUTPUT"
          fi
```
- 置き換え5か所: `steps.changes.outputs.` → `steps.gate.outputs.`（.github/workflows/deploy.yml:178・:447・:528・:549・:629。コメント :173 も合わせる）。
- ADR-082 に追記1段落:「前回のデプロイが成功で終わっていないときは差分にかかわらず全部実行する（P6）」。追記後 node scripts/generate-adr-index.js。

## 6. リスクと対処
| リスク | 対処 |
|---|---|
| PIPELINE_PAT 失効で API が失敗 | 失敗＝全部実行（安全側）。遅くなるだけで壊れない。warning が出るので気づける |
| rerun（同じ SHA の再実行）で before と一致しない | 全部実行になる。今回の 39009743471 rerun と同じ動きで正しい |
| 失敗が続くと毎回全部実行 | 成功が1回出れば戻る。前回が失敗なら全部やるのが目的どおり |
| deploy.yml 変更自体が migrations フィルタ対象（:41） | 実装を入れる初回は全部実行される。想定どおり |

## 7. 受入条件
|基準|検証方法|
|---|---|
| K1 通常時: 直前の run が成功のあとの docs だけの push で、gate が「差分どおり」・migrations が skipped | 実装マージ後の次の docs PR の deploy ログで gate の出力と段の結果を見る |
| K2 前回不成功時: 直前の run が失敗/cancelled のあとの run で、gate が「全部実行」・バックアップ/migrations/smoke が success | gate の run 部分をそのまま bash で4通り（一致／不一致／API が空を返す／gh が失敗）実行し、出力と GITHUB_OUTPUT の中身を記録（実装 PR の証跡）。本番では次に失敗が起きた直後の run のログで確認 |
| K3 API が読める | 実装マージ直後の deploy ログで gate の「前回デプロイは成功（xxxxxxx）」に7桁の SHA が出る（空なら PAT 権限を PO に確認） |
| K4 置き換え漏れ0 | `grep -c "steps.changes.outputs" .github/workflows/deploy.yml` が gate の env 3行だけ（=3）|
| K5 所要時間が増えない | K1 の run の総時間が直近の docs だけの run（中央値）±60秒以内 |

## 8. 戻し方
実装 PR を revert して main にマージ（deploy.yml だけの変更なので、戻すと今の判定に戻る）。

## 維持の仕組み（9. 測り方・維持）
- 測る: gate の warning が出た回数（全部実行の回数）と、その直前の run の結果。直近1000件では7回相当。
- 維持: 正は GitHub の run 履歴。フィルタを足すときは paths-filter 側（:36-59）だけ直せばよく、gate は触らない。

## 外部・過去事例の参照と我々への応用（10）
- 出典: GitHub Docs「Control the concurrency of workflows and jobs」（pending の run は新しい run で置き換えられ cancelled）、dorny/paths-filter README（push は直前 commit と比較）。いずれも 2026-10-17 取得。
- 数値の事例は使わない。理由: この穴は当リポジトリの2つの部品の組み合わせで起きる型で、直接の根拠は recon 6 の実測7件で足りるため。

## 11. 審査（Opus 自己審査・独立レビューではない）
判定: APPROVE（実装可）。根拠: 既存 ADR-082:48 の安全側原則と一致、正の記録が1か所、変更は deploy.yml の1段追加と5か所の置き換えに閉じる、受入条件はログと grep で○×判定可。未解決: K3（PAT で読めるか）は実装後に確かめる。読めなくても安全側に倒れるので実装可を妨げない。
危険パス: .github/workflows/deploy.yml を含むので ADR-136 の GO 手順（PO の委任に基づく Opus 発行）を通す。
