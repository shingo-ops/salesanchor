# design: 毎朝の本番の画面点検を、配備と重なっても見送らず、配備が終わるのを待って行う（2026-11-13）

- 状態: 設計案（Claude Opus 作成）・自己審査済み。PO の選択「2. 配備と重なったら待ってから点検する直しを設計する」（2026-11-13）に基づく。成功条件（§2）は PO の選択「1. この目標で決める」（2026-11-14）で承認済み。実装は未着手（実装の承認は別に受ける）。
- recon: `docs/handoff/prod-ui-check-wait-deploy/recon.md`（以下 recon §n）
- 関連 ADR: ADR-1051（`docs/adr/ADR-1051-prod-ui-black-box-check.md:27` を改訂する）、ADR-1053（速さの記録。毎朝の実行の中で動く）、ADR-136（deploy.yml は触らない）

## 1. 目的（PO の言葉と、その奥）

- PO の言葉: 「配備と重なったら待ってから点検する直し」。
- 奥の目的: 毎朝の点検と速さの記録が、配備が多い日でも毎日 1 回は必ず動き、点検 0 件の日が「合格」に見えないようにする。
- 今の困りごと: 11/12 は毎朝の点検が 10 分待って見送られ、結果は success なのに画面点検 0 件・速さの記録 0 件だった（recon §2-1）。見送りは知らせも出ない（recon §1 の :118-119）。

## 2. 成功条件（KGI・KPI）— PO 承認済み（2026-11-14「1」）

KGI: 毎朝の点検が、配備と重なった日も配備が終わるのを待って動き、画面点検 12 件と速さの記録が毎日そろう。待っても始められなかった日は Discord に「未実行」と知らせが来る。

| # | 基準 | 検証方法 | ○× |
|---|---|---|---|
| K1 | 合流後 14 日間の毎朝の点検で「本番の画面点検を実行」が skipped の日が 0 日 | `gh run list --workflow prod-ui-check.yml --event schedule` の各 run を `gh run view --json jobs` で見る | 0 日なら○ |
| K2 | 同じ 14 日間で、配備と重なって待った日は、待ったあとに画面点検と速さの記録の両方が動いている | 「配備中の確認」の段が 1 分を超えた run で、次の 2 段が success（skipped は×） | 該当する日すべてで○（該当 0 日なら「確かめられず」と書き、×にしない） |
| K3 | 50 分待っても配備が終わらないときは、仕事が failure になり、Discord に「配備が 50 分以上続き、点検を始められませんでした」と出る | 手動起動（workflow_dispatch）の試験はしない（本番配備を 50 分止められない）。審査で §4 のコードの分かれ道を読み、合流後に起きたら Discord の文面で確かめる | 審査で○ |
| K4 | 配備の後の点検（workflow_run）の動きは変わらない | 審査で、event が workflow_run のときの分かれ道が今と同じ（10 分待って 1 回だけ確かめ直し、まだなら見送り）であることを diff で確かめる | 審査で○ |

## 3. 選んだやり方と、選ばなかったやり方

| 案 | 中身 | 判断 |
|---|---|---|
| A（採る） | 毎朝・手動の実行だけ、配備が終わるまで 1 分ごとに数え直して最大 50 分待つ。50 分で終わらなければ不合格にして知らせる | 実測の最長の配備の続きは 47.5 分（recon §2-3）。50 分なら 10 日間の全部が収まる |
| B | 毎朝の起動を毎時 0 分以外（例 06:17）にずらし、配備の少ない時間に動かす | GitHub は毎時 0 分が混むと書いている（recon §3）。ただし今の遅れ 2.6〜5.9 時間がどれだけ縮むかは実測がない（recon §4）。変更は 1 度に 1 つにするため、A の効果を測ってから別に考える |
| C | 配備の後の点検も同じく長く待つ | 配備の後の点検は、見送っても約 11 分後に次の配備の後の点検が必ず動いている（recon §2-2）。長く待たせると同じ組で待つ 1 本の置き換えが増え、毎朝の 1 本が取り消されるおそれが増える（recon §3）。採らない |
| D | 毎朝の点検を別の組にして同時に動かす | 同じ点検用の人の同時ログインで締め出されるかが未確認（recon §4）。採らない |

## 4. 変更の中身（実装役は書いてあるとおりに変える。触るのは `.github/workflows/prod-ui-check.yml` と ADR-1051 の 2 ファイルだけ）

### 4-1. 仕事の上限（`.github/workflows/prod-ui-check.yml:35-36`）

変更前:
```yaml
    # 速さの記録の段（最大 40 分で打ち切る）を含めて 60 分
    timeout-minutes: 60
```
変更後:
```yaml
    # 配備の待ち（最大 50 分）と速さの記録の段（最大 46 分）を含めて 110 分
    timeout-minutes: 110
```
根拠: 待ち 50 + 準備約 2 + 画面点検約 4 + 速さの記録 46 = 102 分。余り 8 分。

### 4-2. 「配備中の確認」（`.github/workflows/prod-ui-check.yml:38-61`）

変更後（段の全体を置き換える）:
```yaml
      - name: 配備中の確認
        id: gate
        env:
          GH_TOKEN: ${{ github.token }}
          EVENT_NAME: ${{ github.event_name }}
        run: |
          count_active() {
            total=0
            for st in in_progress queued waiting; do
              c=$(gh run list --repo "${{ github.repository }}" --workflow deploy.yml --status "$st" --json databaseId --jq length)
              total=$((total + ${c:-0}))
            done
            echo "$total"
          }
          n=$(count_active)
          if [ "$EVENT_NAME" = "workflow_run" ]; then
            # 配備の後の点検は今までどおり: 10 分待って 1 回だけ確かめ直す
            if [ "${n:-0}" -ge 1 ]; then
              sleep 600
              n=$(count_active)
            fi
            if [ "${n:-0}" -ge 1 ]; then
              echo "skip=true" >> "$GITHUB_OUTPUT"
              echo "配備中のため見送り" >> "$GITHUB_STEP_SUMMARY"
            else
              echo "skip=false" >> "$GITHUB_OUTPUT"
            fi
          else
            # 毎朝・手動の点検は見送らない: 配備が終わるまで 1 分ごとに数え直す（最大 50 分）
            deadline=$(( $(date +%s) + 3000 ))
            while [ "${n:-0}" -ge 1 ] && [ "$(date +%s)" -lt "$deadline" ]; do
              sleep 60
              n=$(count_active)
            done
            if [ "${n:-0}" -ge 1 ]; then
              echo "配備が 50 分以上続き、点検を始められませんでした（未実行）" >> "$GITHUB_STEP_SUMMARY"
              exit 1
            fi
            echo "skip=false" >> "$GITHUB_OUTPUT"
          fi
```
- 1 分ごとにする理由: 1 回で GitHub に 3 回問い合わせる。50 分で最大 150 回。GITHUB_TOKEN の上限（1 時間に 1,000 回/repo）の中に収まる。
- 数えるのに失敗したとき（`c` が空）は 0 と数える。今と同じ扱いで変えない。

### 4-3. 不合格の知らせ（`.github/workflows/prod-ui-check.yml:118-149`）

- `if:` は変えない（`failure() && steps.gate.outputs.skip != 'true'`。待ち切れで gate が failure のとき skip は 'true' でないので知らせが動く）。
- `env:` に 1 行足す: `GATE_OUTCOME: ${{ steps.gate.outcome }}`
- python の `label = ...` の行（今の :145）を次に置き換える:
```python
          if os.environ.get("GATE_OUTCOME") == "failure":
              label = "配備が 50 分以上続き、点検を始められませんでした（未実行）"
          else:
              label = " / ".join(names) if names else "点検を最後まで実行できませんでした"
```
- 出力の値（outputs）は失敗した段では頼らない。`steps.<id>.outcome` が failure になることは GitHub の文書で確かめた（contexts の steps）。

### 4-4. 速さの記録（`.github/workflows/prod-ui-check.yml:157-158` の `if:`）

変更前:
```yaml
        if: always() && steps.gate.outputs.skip != 'true' && github.event_name != 'workflow_run'
```
変更後:
```yaml
        if: always() && steps.gate.outcome == 'success' && steps.gate.outputs.skip != 'true' && github.event_name != 'workflow_run'
```
理由: `always()` があるため、待ち切れで gate が failure のときにも準備なしで動いてしまう。gate が success のときだけにする。

あわせて `:160` の注記を変える。
変更前: `        # 試験の上限 45 分 + 1 分。この段が延びても仕事の上限 60 分の中で終わらせる（設計 5-8）`
変更後: `        # 試験の上限 45 分 + 1 分。配備の待ち（最大 50 分）があってもこの段が仕事の上限 110 分の中で終わる（設計 5-8・prod-ui-check-wait-deploy §4-1）`

### 4-5. ADR-1051 の改訂（`docs/adr/ADR-1051-prod-ui-black-box-check.md:27`）

変更後:
```
- 配備（deploy.yml）が動いている間、配備の後の点検は 10 分待って 1 回だけ確かめ直し、まだ動いていれば見送る（不合格にしない。次の配備の後の点検が続けて動くため）。毎朝と手動の点検は見送らず、配備が終わるまで 1 分ごとに確かめ直して最大 50 分待つ。50 分を超えたら不合格にして Discord に「未実行」と知らせる（2026-11-13 改訂）。
```
- 表の「備考」に改訂の一文を足す（PO の選択 2026-11-13「2」と、成功条件の承認日）。
- ADR を変えたら `node scripts/generate-adr-index.js` で `docs/adr/README.md` を作り直してコミットする。

### 4-6. 触らない範囲

- `.github/workflows/deploy.yml`（ADR-136）、`tests/prod-check/` の点検の中身、`concurrency` の組、毎朝の起動時刻（案 B は別件）。

## 5. 影響範囲

- 呼び出し元: この仕事を起こすのは schedule・workflow_run・workflow_dispatch の 3 つ（`.github/workflows/prod-ui-check.yml:7-20`）。変わるのは schedule と workflow_dispatch の待ち方だけ。
- 毎朝の点検が待っている間、同じ組の配備の後の点検は 1 本だけ待ち、新しいものが来れば古いものと置き換わる（今と同じ仕組み）。待ちが終われば最後の 1 本が動き、最新の本番を点検する。
- GitHub の機械の使用時間は増える。この repo は公開（ADR-1051 What）なので、GitHub 提供の機械の料金はかからない。

## 6. リスクと対処

| リスク | 対処 |
|---|---|
| 配備が 50 分を超えて続く日に未実行になる | 不合格にして知らせる（K3）。今の「success で黙って見送り」より気づける |
| 待ちが長いと、遅れて始まる毎朝の点検がさらに遅くなる | 最大でも 50 分。点検の中身は変わらない |
| 毎朝の 1 本が、待っている間に置き換えで取り消される | 毎朝の 1 本は待ちの段で「動いている」状態なので置き換えの対象にならない。対象になるのは組の中で待つ側だけ（recon §3）。過去 14 回で取り消し 0 回（recon §2-1） |

## 7. 戻し方

- この PR の合流を戻す PR を出す（`git revert -m 1 <合流の記録>`）。本番のデータ・設定には触れないので、戻しは workflow ファイルだけ。

## 8. 測り方と維持の仕組み

- 守り手: `.github/workflows/prod-ui-check.yml`（毎朝と手動の点検は配備の終わりを最大 50 分待って点検し、待ち切れは Discord に知らせる）
- 測り方: K1・K2 を合流から 14 日後に `gh run list` と `gh run view --json jobs` で数える（予約を立てる）。
- 維持: 「点検が動いていない」は今までどおり GitHub の実行一覧で見る（ADR-1051 守り方）。待ち切れは Discord に出る。

## 9. 外部・過去事例の参照と我々への応用

- GitHub の文書（Context7 `/websites/github_en_actions`、2026-11-13 確認）: schedule は混む時間に遅れ、捨てられることもある。concurrency の待ちは既定 1 本で、新しいものが古いものを置き換える。
- 他社の数値つきの事例は使わない。本件は自分の repo の実測（recon §2）で判断でき、外の事例が判断を変えないため。
- 過去事例（社内）: 11/4・11/7 の毎朝の点検は 10 分待ちのあと動けた。11/12 は 10 分で足りず見送った（recon §2-1）。配備が続く最長は 47.5 分だった（recon §2-3）。応用: 1 回だけの 10 分待ちをやめ、1 分ごとに確かめ直して最大 50 分待つ。

## 10. 審査（同じ AI による自己審査。独立した第二者の審査ではない）

- 判定: 設計合格（APPROVE）。§2 の成功条件は PO 承認済み（2026-11-14）。
- 確かめたこと:
  - recon の行番号を `git show origin/main:.github/workflows/prod-ui-check.yml | cat -n` で照合した。
  - 50 分・110 分の根拠が recon §2-3 の実測と §4-1 の足し算で説明できる。
  - 待ち切れのときに速さの記録が動いてしまう穴（`always()`）を見つけ、§4-4 でふさいだ。
  - 失敗した段の outputs に頼らず outcome を使う（GitHub の文書で確かめた値）。
- 未解決: なし（案 B の効果は別件として残す）。
