<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — app-update-notice（新しい版のお知らせ）

**対象ADR**: ADR-1016（ほか ADR-144、ADR-067、ADR-027）  
**recon**: docs/handoff/app-update-notice/recon.md  
**日付**: 2026-10-29  
**担当**: Planner（Opus 設計担当）

状態: 設計審査済み（Opus 自己審査・APPROVE）／PO 実装承認済み（2026-10-29）／実装中（PR 起票時）

---

## 目的と PO の決定

- 困りごと: スマホのホーム画面に置いたアプリは、開き直しても前の画面が残る。新しい版を本番に出しても古いまま動き続ける。2026-10-29 に PO の実機で見つかった。アプリを完全に閉じて開き直すと直ることも PO が確かめた。
- PO の決定（2026-10-29、選択肢「1」と「実装」）: 新しい版が出ていたら、画面の上に「新しい版があります・更新」と小さく出す。押すと新しくなる。自動では読み込み直さない（書きかけの返信を消さないため）。
- 今の姿は recon（docs/handoff/app-update-notice/recon.md）にまとめた。版を確かめる仕組みは無い。

---

## 外部・過去事例の参照と我々への応用

- 事例1: 2026-10-29 PO 実機（リードをまとめる操作がスマホのアプリで出ず、完全に閉じて開き直すと出た）→ 我々への応用: 開き直さない限り古い版が動き続ける実測。この設計の出発点。
- 事例2: ADR-1016 の「裏にいる間は保留し、表に戻ったら1回取り直す」流儀（frontend/src/hooks/useRealtimeRefresh.ts）→ 我々への応用: 版の確かめも同じ流儀（戻ったとき・裏では止める・間引き）にそろえる。試験の型も同じものを使う。
- 事例3: 閲覧ページの1分ごとの自動更新（frontend/src/pages/viewer/useViewerAutoRefresh.ts）→ 我々への応用: データの取り直しでは画面の版は変わらない。版の古さは別に扱う。閲覧ページは今回の対象外。
- 外部事例は使っていない。理由: 社内の実測だけで設計が成り立ち、外部の数値を成功の証明に使わないため。

---

## 変えること

1. 版の確かめ方: 今の画面が読み込んだ main の js の名前と、入口を cache: "no-store" で取り直して見つけた main の js の名前を比べる。違えば新しい版がある。
   - 理由: ビルド・Dockerfile・nginx・deploy.yml を変えずに済む。入口は既に no-cache で、名前はビルドごとに変わる。
   - 今の名前は document の script 要素（type=module で assets の main を指すもの）から取る。取れない（開発サーバーなど）ときは何もしない。
2. 確かめる時: アプリが裏から表に戻ったとき（visibilitychange で visible）と、表に出ている間の10分ごと。どちらも前回から60秒以内なら確かめない。裏にいる間は確かめない。
3. 新しい版を見つけたら確かめるのをやめ、知らせを出したままにする。閉じるボタンは置かない。
4. 知らせ: 画面の上の中央に小さく出す。中身は「新しい版があります」の文と「更新」ボタン（金型 Button）。押すと window.location.reload() を1回呼ぶ。
   - 置き場所: App.tsx の Toaster の隣（PC・スマホ・殻の無い画面すべてに出る）。
   - 見た目: 既存の金型（Callout の info と Button）の組み合わせ。色・余白・z-index は token だけ（ADR-067）。z-index は var(--z-toast)。上の余白は calc(env(safe-area-inset-top, 0px) + var(--space-2))。position: fixed には既存例どおり fixed-ok の注記。
   - スマホ幅（〜767px）では左右に余白を取って横いっぱい。ボタンの高さは 44px 以上。
   - Storybook の見張り（check:stories）に合わせ、見た目だけの AppUpdateNoticeView と stories を置く。
5. 文言（t() 経由、ja/en 同じキー）: appUpdate.message「新しい版があります」/「A new version is available」、appUpdate.reload「更新」/「Reload」。
6. 失敗したとき（通信できない・入口の形が違う）: 何も出さず次の時を待つ。エラーを画面に出さない。

対象外: 自動の読み込み直し、閲覧ページ（別の入口）、Service Worker・manifest、nginx・Dockerfile・deploy.yml・backend の変更、コード分割を足したときの読み込み失敗への対処（今は lazy が0件）。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| K1: 名前が違うとき、表に戻った1回目の確かめで知らせが出る | 単体試験 `frontend/src/hooks/useAppUpdateCheck.test.ts`（K1） |
| K2: 名前が同じなら出ない。60秒以内の2回目は取りに行かない | 単体試験 `frontend/src/hooks/useAppUpdateCheck.test.ts`（K2、取りに行った回数を数える） |
| K3: 裏にいる間と、見つけたあとは取りに行かない。10分ごとに確かめる | 単体試験 `frontend/src/hooks/useAppUpdateCheck.test.ts`（K3） |
| K4: 今の名前が取れない・通信に失敗したとき、出さず例外も投げない | 単体試験 `frontend/src/hooks/useAppUpdateCheck.test.ts`（K4） |
| K5: 「更新」を押すと読み込み直しが1回。押さない限り呼ばれない | 単体試験 `frontend/src/components/AppUpdateNotice.test.tsx`（K5） |
| K6: 幅 390・1280 で上に出て、横のはみ出しが無く、ボタン 44px 以上 | CI 画面試験 `frontend/tests-e2e/visual-language/app-update-notice.spec.ts`（写真を PO に見せる） |
| K7: check:all と build が通り、ja と en のキー数が一致する | CI（npm run check:all、npm run build） |
| K8: この版を入れて一度完全に閉じて開き直したあと、次の本番の版で知らせが出て、押すと新しくなる | PO の実機（次の本番の版が出たとき） |

---

## 技術 How・KPI

- KPI: 本番に新しい版が出たあと、アプリに戻った人に知らせが出るまで最大でも次の確かめ1回（戻ったとき、または10分以内）。
- 技術選択: 入口の名前の比較（理由: ビルド・配り方を変えずに済み、壊れても知らせが出ないだけで済む）。

---

## 弊害・トレードオフ

- 入口の形が変わり名前が取れなくなる → 対策: 取れないときは何もしない（K4）。知らせが出ないだけで、壊れはしない。
- 入口を取りに行く回数が増える → 対策: 1人あたり10分に1回と戻ったとき（60秒に1回まで）。入口は約 1.3KB。
- 新しい金型に当たるか（ADR-144 §4）→ 対策: 既存の Callout と Button の組み合わせで、新しい色・部品の決まりを足さない。実装担当が条文（docs/adr/ADR-144-ui-component-governance.md の §4）を確かめ、当たらないと判断した。設計担当もこれを採る。
- 最初の1回はこの仕組みが古い画面に届かない → 対策: PO に一度だけ完全に閉じて開き直してもらう（K8）。
- 戻し方: この PR を revert する。DB・サーバーは変えないので画面だけが戻る。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | 版を確かめるフックと試験（K1〜K4） | Generator（Sonnet） |
| 2 | 知らせの部品・CSS・stories・試験（K5） | Generator（Sonnet） |
| 3 | App.tsx に置く、ja/en の文言 | Generator（Sonnet） |
| 4 | 画面試験（K6）と CI の写真を PO に見せる | Generator（Sonnet）／Opus |
| 5 | 審査・GO・マージ・本番の確認（K8 は PO 実機） | Opus |

---

## 維持の仕組み

- 守り手: frontend/src/hooks/useAppUpdateCheck.test.ts
- 守り手: frontend/tests-e2e/visual-language/app-update-notice.spec.ts
- 説明: 上の単体試験と画面試験が CI で毎回流れ、仕組みを壊す変更はここで止まる。入口が assets の main の js を読む形でなくなると知らせは出なくなる（壊れはしない）。Vite の入口名や frontend/nginx.conf の入口の保存の決まりを変える PR では、この設計書を見直す。

---

## 継続

- 完了後の監視: K8 を次の本番の版が出たときに PO の実機で確かめ、結果をこの設計書に追記する。
- 次フェーズへの引き継ぎ: 閲覧ページ（別の入口）に同じ知らせが要るかは、必要になったら別に決める。

---

## 設計審査（Opus 自己審査、独立した第二者レビューではない）

- 判定: APPROVE
- 確かめたこと: 既存の仕組みが無いこと（recon の不明点1）、入口の no-cache と版ごとに変わる名前（10:57 と 11:09 の実測）、置き場所が両方の殻に効くこと、受け入れ基準がすべて試験か実機で ○× にできること、ADR-144 §4 に当たらないこと。
