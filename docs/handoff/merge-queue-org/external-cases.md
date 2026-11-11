# merge queue と gitleaks CLI 移行：外部事例の調査結果

調査日: 2026-11-11 / 役割: 調査役（外部事例・読むだけ）/ 製品コード・設計書は未変更

## 0. 調査の限界（先に読む）

- この実行環境は github.com 以外の多くのホストを開けなかった（名前が引けない）。開けなかったもの: github.blog、trunk.io、docs.github.com、lethain.com（Uber論文PDF）、uber.com、plaid.com、leaddev.com、samsara.com、goliathdata.com、nirvanatech.com、blog.acolyer.org。bex.co は検索に出ず開けていない。
- 依頼の A の例（GitHub社ブログ・Trunk の Caseware 事例・Uber 論文）は**開けていない**。規則「開けたページだけを使う」により、それらの数値は書かない。URL だけを「未開封の候補」として 6 節に残す。
- 開けたのは github.com 上のページだけ。GitHub の PR/Issue/Discussion は WebFetch で開いた（gh は使っていない）。
- preflight（executor-preflight.sh）は api.github.com 不達と gh 認証で FAIL だった。このクラウド環境は gh を使わない設計で、今回は git と WebFetch だけで足りるため続行した（PR 操作なし）。
- 各ページの数値は WebFetch の要約抽出で得たもの。原文との突き合わせ（再読）は未実施。「著者」が空のものは「記載なし」。
- 日付は各ページの表示どおり。実在確認はページを開けたことのみ。

## A. 導入の成功事例（開けたページ内のもの）

結論: 依頼の例のとおりの「測定値つき成功事例」は**開けず、見つからず**。開けたページで成功に近いものは次の 3 件（いずれも数値の裏づけは弱い）。

### A-1. stevecad/camlib Issue #148（導入決定。導入後の実測なし）
- 出典: https://github.com/stevecad/camlib/issues/148 / 2026-11-09 / 作者 10-X-eng / Closed（PR #155 で対応）
- いつ: 2026-11-09 のバッチ。どこ: camlib の main。誰: 10-X-eng。
- 何を: 必須チェックを通した PR 同士が合体すると壊れる事例が 2 組（#142+#146 はコンパイル不可、#139+#143 は判断の食い違い）。直列の「最新化→CI」が N 件で N 回かかる。
- なぜ: 直列の最新化リベースをやめ、合体結果を 1 回で確かめるため。
- どうやって: `on:` に `merge_group` を追加。ブランチルールでキュー必須。squash。グループ化 ALLGREEN、1 バッチ最大 5 件、待機 5 分。既存の必須チェック 6 件は維持。Allow auto-merge を有効にして「Merge when ready」で自動投入。
- どれだけ: 設定値のみ（5 件・5 分・必須 6 件・衝突 2 組）。導入後の削減量は**数値なし**。
- 成功要因: `merge_group` を CI に足し、必須チェックを変えずにキュー必須化した順序。
- 未確認点（原文に明記）: 失敗バッチの分割動作は運用で確認が必要。`AGENTS.md` へのキュー説明は完了確認できない。
- 限界: 規模は小さく、導入直後で効果の実測なし。私たちの「必須16件・1日数十PR」より桁が小さい。

### A-2. elsa-workflows/elsa-foundation Issue #3786（導入準備。有効化待ち）
- 出典: https://github.com/elsa-workflows/elsa-foundation/issues/3786 / 2026-11-03 起票（オーナー決定 11-04）/ 起票・担当 sfmskywalker / 本文は Claude Code 生成と明記
- いつ: 2026-11-03〜11-10。どこ: elsa-foundation の main。誰: sfmskywalker。
- 何を・なぜ: 作者が main を PR に取り込んで 2 層の CI を再実行するため、全 PR で CI が最低 2 回走る。必須チェックは非 strict で、古い土台でのマージが main を壊しうる。キューなら合体結果に 1 回。
- どうやって: `ci.yml` が `merge_group` で `Build & test`・`Generated maps fresh`・`Full tier` を報告。範囲判定に merge group の base/head を使う。**キュー内の実行を concurrency でキャンセルしない**。想定設定は Squash、Only merge non-failing、タイムアウト 90 分以上、グループサイズ 1。ruleset でのキュー有効化はオーナー作業で、Issue は有効化待ち。
- どれだけ: 設定値のみ。**効果の数値なし**。
- 成功要因（想定）: 必須 3 チェックすべてを `merge_group` で報告させる点。失敗要因は未発生（未有効化）。
- 限界: 有効化前で結果がない。計画段階の事例。

### A-3. community Discussion #46757「Pull Request Merge Queue Public Beta Feedback」の成功の声
- 出典: https://github.com/orgs/community/discussions/46757 / 2023-02-08 / 投稿者 willsmythe（GitHub 側 Maintainer）/ ページは途中で切れている
- 成功の声は少数: nwalters512（2023-02-10、`merge_group` の修正後に動いたと報告）、alex-statsig（2023-09-14、`push`・`pull_request`・`merge_group` の併用で動くと報告。ただし paths は `merge_group` で使えないと指摘）。
- どれだけ: 元投稿の反応 👍19・🎉42・❤️12 など。コメント 269 件・返信 404 件（表示時点）。タイムアウト上限は当初 127 で 500 エラー、修正後 360 分まで可（2023-02-10 の修正後）。
- 限界: 個人の感想中心で、効果の定量値は無い。
- 同じページの問題点は B-3 に記す。

## B. 導入の失敗・つまずき事例

### B-1. community Discussion #14333「Feedback on the Merge Queue (Beta)」
- 出典: https://github.com/orgs/community/discussions/14333 / 2022-04-05 / 投稿者 Gallimathias
- いつ: 3 月に試験導入、4/5 に投稿、その後 2023-03 までコメント。誰: 投稿者の会社。
- 何が起きた: 今は**オフにした**。(1) キューでの失敗原因が PR から見えない・成功したのに最終的に合流しないことに気づきにくい。(2) 必要レビュー数が PR 単位で変えられず、自動マージで 2 人必要な PR が 1 人承認で入る。(3) 直接マージできたはずの PR も再ビルドされ、**1 PR あたり約 30 分の追加待ち**。
- コメント: antonagestam（2022-07-04）は main への push 時の CI を省けば二重作業を減らせると提案。squash と併用するとキューで試した正確なコミットが main に入る保証が崩れると指摘。brianhenn（2023-02-22）は 2023-02 に試して導入を取りやめた。理由は強制 squash でメッセージ編集不可、CircleCI 連携の問題。
- 失敗要因: 可視性不足、レビュー設定の粒度、再ビルド増。GitHub の公式回答は確認できず。
- 限界: ベータ期（2022〜2023）の話で現行仕様と差がありうる。16 件必須の私たちにとっては「キューが最終結果を再ビルドする分、待ちが増える」点が参考。

### B-2. community Discussion #15254「Why does our Merge Queue get stuck?」
- 出典: https://github.com/orgs/community/discussions/15254 / 2022-04-20 / 投稿者 magnattic / Unanswered
- 何が起きた: 全チェック成功・先頭にいるのにキューが止まる。再登録・jump でも直らない。
- 報告された原因（コメント別）: 必須チェック未設定（magnattic、2022-07。必須を 1 つ設定すると動いた。**パスで動くワークフローを必須にすると止まる**ため merge-gatekeeper で回避）。`gh-readonly-queue/{base}/**` で CI が起動しない（antonagestam、2022-04）。キャッチオールのブランチ保護 `**/**`（danjamespearce、2022-05）。再利用ワークフローが "Starting job..." で止まる（AllDmeat、2023-04）。`merge_group` の CI が 1 件も起動せず先頭が AWAITING_CHECKS のまま（timherby、2026-07。先頭を外して再投入で復旧）。
- 回復手順（GitHub サポート案内、2022-04-27）: 先頭を削除 → キューをクリア → キューを無効化して再有効化。
- 失敗要因: 原因が複数で、グループ作成後に CI が起動したか見えない。sweepy84 は可視性不足を理由に導入を断念。
- 限界: 4 年分の雑多な報告で再現条件が揃っていない。ただし「必須チェックの CI が `merge_group` で起動しない」は私たちにも直結する。

### B-3. community Discussion #46757 の問題点
- 出典: 同 A-3 の URL。
- 問題報告（投稿者・日付）: Methuselah96（2023-02-08）は `merge_group` が発火せず PR がキューに残る。dustinblanchard（同日）は完了済みチェックが pending のまま。marcind（同日）は PR タイトル検証など PR メタデータ依存のチェックがキューを停滞させる。RCheesley（2023-02-13）はチェックが時間内に出ず PR が未マージのままキューから外れる。jglick（2023-04-28）は Dependabot と組み合わせると競合・除外が起き、Go リポジトリで実用的でない。ro-savage（2024-09-09）は PR とキューで同じ必須テストを要求される仕様のため Enterprise からのダウングレードを検討。jakeatoms（2024-10-24）は投入時とマージ時で必須チェックを分けたい。sandstrom（2023-02-08 以降）はセミリニアマージ未対応で導入できない（2026-05 にも状況を問う投稿）。
- 失敗要因: トリガー不足、PR メタデータ依存チェック、仕様の硬さ。
- 限界: 元の投稿は 2023 年のベータ。現在の仕様で解消済みのものを確認していない。

### B-4. twisted/klein Issue #623（`merge_group` 未設定でキューが止まる）
- 出典: https://www.github.com/twisted/klein/issues/623 / 2023-05-31 / 作者 glyph / Open
- 何が起きた: キューが止まったまま。原因は GitHub Actions に `on: merge_group:` が無いこと。恒久策は書かれず、作者はキューを一時的に無効化して必要設定が分かるまで放置するとした。
- どれだけ: Issue 番号 #623。他に数値なし。
- 失敗要因: 必須チェックを出すワークフローに `merge_group` が無い。
- 限界: 小規模 OSS。ただし私たちの必須 16 件すべてに `merge_group` が要る、という確認項目の根拠になる。

### B-5. community Discussion #45899「Path filtering does not work for merge_group triggers」
- 出典: https://github.com/orgs/community/discussions/45899 / 2023-01-31 / 投稿者 wjglerum / Unanswered
- 何が起きた: `merge_group` で paths フィルタが効かず、本体とスキップ用のワークフローが両方動く。ブランチフィルタは効くとされる。「スキップされたが必須のチェック」の扱いを質問。
- 回避策（コミュニティ）: 先に変更判定ジョブ（dorny/paths-filter など）を置き、結果で本体を制御する（ステータスが 1 行増える）、またはシェルで判定。2026-05 時点でも要望が続き、ロードマップ上の扱いは未確認。GitHub の公式回答は見当たらない。
- 失敗要因: paths で絞った必須チェックがキューで未報告になる。
- 限界: コミュニティ報告。必須 16 件に paths 絞りがあるかは私たち側の確認事項。

### B-6. community Discussion #171941（必須チェックの名前・実行）
- 出典: https://github.com/orgs/community/discussions/171941 / 2025-09-01 質問、09-02 回答 / 投稿者 scariabpc / 回答者 unixreaper・leandromlmoreira
- 何が起きた: `merge_group` 用ワークフローは動くのに、キュー画面で必須として出ない。
- 回答の要点: ブロック要因として出るのはブランチ保護で必須に設定されたチェックだけ。必須にするのはファイル名でなくジョブ名で、直近 7 日以内に実行されている必要がある。`pull_request` でしか動かない必須チェックは、キューでは報告されず条件を満たせない。
- 失敗要因: 確かめの名前の不一致・`merge_group` 側で報告しない。
- 限界: 回答者の説明で、GitHub 公式文書での裏取り（docs.github.com）は開けず未確認。

### B-7. smith-ai-lab/smith Issue #2241（古い `merge_group` 実行がランナーを占有）
- 出典: https://github.com/smith-ai-lab/smith/issues/2241 / 2026-11-04 / 作者 adam-r-kowalski / Closed（PR #2245）
- いつ・何が起きた: 2026-11-04 4:00、キューの並べ替えで消えたグループの実行がキャンセルされず、**5 件の古い実行**がランナーを占有。うち 1 件は無料枠 20 スロットのうち約 11 を使用。結果が有効な 2 件（#2231・#2175）が待たされ、**マージが 1 時間あたり 3〜4 件に低下**。オーナーが手動で古い実行を取り消すまで続いた。
- どうやって直した: `concurrency` のキーで `pr-<N>` を参照から切り出せないため、`ci.yml` に `queue-guard` ジョブを追加（`gh-readonly-queue/...` の参照が 2 回連続で消えたらキャンセル）。並べ替え試験は未実施。作業中の摩擦は約 15 分。
- 失敗要因: キュー並べ替え時の古い実行の放置、ランナー枠の小ささ。
- 限界: ホステッドランナーの無料枠 20 スロットが前提。私たちの構成（自前ランナーか否か）で影響が変わる。

### B-8. cfg-is/cfgms Issue #5972（キューで PR 済みの確かめを再実行）
- 出典: https://github.com/cfg-is/cfgms/issues/5972 / 2026-11-07 起票 / 作者 jrdnr / Closed（2026-11-08、PR #5985）
- 何が起きた: マージキューの `Native Build` が、PR で既に走る同じテストを再実行。2026-10-31 以降の merge_group 実行（直近 1000 件）で **2099 job-minutes（キュー全体のジョブ時間の 33.1%）**。過去 14 日間にキュー内で失敗して修正が要った事例のうち、その shard が検出したものは **0 件**。
- 対策: shard 2 を削除。`Build Gate` は `native-builds` と `postgres-integration` の両方に依存する形を維持。構造を検証するテストを追加して復活を防ぐ。PR 用ワークフローは変更しない。
- 失敗要因: PR と同じ確かめをキューで重複して流す設計。
- 限界: 2 時点の自己集計。私たちも必須 16 件をキューでも流すと同じ重複が出る可能性がある（要判断）。

### B-9. github/gh-stack Issue #502（REBASE キューで fast-forward でも CI 再実行）
- 出典: https://github.com/github/gh-stack/issues/502 / 2026-09-09 / 作者 grubmeshi / Open
- 何が起きた: `merge_method: REBASE` のキューが、親が既にキューの土台でも全コミットを書き換え、SHA が変わって上位 PR の約 15 分の必須チェックが再実行。スタック `main ← #101 ← #102` で 1 回の合流にテストが 3 回、上位 PR はキューから外れ手動で再投入。別イメージの公開でビルドキャッシュも再利用できず。
- 失敗要因: REBASE 方式の挙動。
- 限界: スタック PR 前提の事例。私たちが merge 方式をどうするかで当てはまり方が変わる。

## C. 会社名義へ移して gitleaks-action が落ち、CLI に替えた事例

共通の事実: 個人名義では無償、組織名義だとライセンスキーが要る。エラー文言は missing gitleaks license 系。v2 でも v3 でも同じ（Skolara #111 に「v3 でも `GITLEAKS_LICENSE` が必要」とある）。

### C-1. youpi-pg/YouPI-PG PR #53
- 出典: https://github.com/youpi-pg/YouPI-PG/pull/53 / 2026-10-20 提出・10-21 マージ / 作者 rajputomsingh / レビュー arungupta1526 / マージ developer-rs5
- 何が起きた: 全 PR で CI Stage 1（Gitleaks Secret Scan）が missing gitleaks license で失敗し、パイプライン全体が止まった。
- どうやって: ライセンスのシークレットは足さず（フォークの導入負担と自前運用方針のため）、公式リリースの CLI を直接取得。`.gitleaks.toml` の allowlist・`--redact`・`fetch-depth: 0` は維持。PR 差分を `base_ref..HEAD` でスキャン。レビュー後に **v8.30.1 へ更新・SHA256 検証追加・`sudo` を外した**。
- どれだけ: コミット 2、承認待ちの実行 2 件。チェックサムの値はページに無い。
- 成功要因: 版固定＋SHA256 検証、差分スキャン。限界: 小規模公開倉庫。

### C-2. editrace-app/Editrace PR #333
- 出典: https://github.com/editrace-app/Editrace/pull/333 / 2026-10-28 作成・同日マージ / 作者 calvinkafaiyuen / マージ・承認 anthonythanpoovong
- 何が起きた: `gitleaks/gitleaks-action@v2` が組織で `GITLEAKS_LICENSE` を要求し、`detect` が全 PR で失敗。`detect` に依存する他ジョブがスキップされ、最終 `ci-ok` が失敗。初出は PR #313。
- どうやって: CLI v8.30.0 を取得し sha256 検証（`.pre-commit-config.yaml` と版を揃える）。範囲は PR は base..head、push は before..after、比較対象なしは全履歴。検出 1 件でも失敗。シークレット不要。ライセンスの組織シークレットを足す案は、管理者権限・gitleaks.io のアカウント・有料プランが要りうるため不採用。
- どれだけ: マージ時 29 件中 28 件成功。リリースの checksum は Linux 版・Windows 版とも一致。漏れ 0 件（#313 の 10 コミット、main の直近 134 コミット、全 357 コミット）。偽のキーを仕込んだ試験で終了コード 1・検出 1 件。
- 注意点（原文）: 既存 PR は main を取り込むまで失敗が残る。古いワークフローは失敗ジョブの単独再実行でも使われる。
- 成功要因: 検知試験まで済ませた検証。限界: 全 357 コミットの小〜中規模。

### C-3. GEG-ETHZ/agent-harness-config Issue #4（URL は /pull/4 だが開くと Issue）
- 出典: https://github.com/GEG-ETHZ/agent-harness-config/pull/4 / 2026-10-19 起票 / 作者 Philipp Schädle（philippschaedle）/ 担当 Daniel Vogler・János Höner・Philipp Schädle
- 何が起きた: 個人名義の頃はライセンス不要で動いた。組織へ移管後、どの PR でも `secrets` ジョブが missing gitleaks license で失敗。
- 提案: バイナリを直接実行。版固定＋リリースの SHA-256 検証。コマンドは `gitleaks git . --redact --verbose --exit-code 1`。参考に geg-ops の `ci.yml` の方式。版は v8.30.1（pre-commit で既に固定のものと同じ）。
- 限界: ページは提案段階で、PR 本体の結果は読めていない。

### C-4. Nishfleet/siterep-public（Issue #6 ほか 3 倉庫の記載）
- 出典: https://github.com/Nishfleet/siterep-public/pull/6 / Issue #6 の作成日 2026-08-24 / 作者記載なし
- ページ内に複数の事例が並ぶ: aiconverter-app PR #187（2026-08-24 マージ。タイトルは Trust ページ文言で内容と不一致）、0509 リポジトリ PR #784、siterep-public のコミット 7fc06f7。いずれも gitleaks-action のライセンス要件を避け、`.github/workflows/secret-scan.yml` で v8.30.1 をバージョンと SHA-256 で固定して CLI を使用、`fetch-depth: 0` で全履歴を `gitleaks git` でスキャン。チェック名 `Gitleaks` は変えず、必須チェック名が変わらないようにした。PR #355 は docs だけの差分でもライセンスエラーで `Gitleaks` が失敗。
- どれだけ: 対象 3 倉庫、費用 $0。他に数値なし。
- 私たちへ: **チェック名を変えない**点は必須チェック名の不一致を避ける実例（B-6 と関連）。限界: 作者・詳細が薄い。

### C-5. ChiefGyk3D/git-your-ship-together Issue #90（対応 PR #94）
- 出典: https://github.com/ChiefGyk3D/git-your-ship-together/pull/90 / 2026-10-05 / 作者 ChiefGyk3D
- 何が起きた: 2026-10-05 に Hammunition スイートが Renegade-Penguin 組織へ移ると、最初の PR で gitleaks が失敗。`security.yml` は `GITLEAKS_LICENSE` を信頼できる ref（push など）でのみ取得する設計のため、**PR ではシークレットが取れず組織倉庫の PR が永久に通らない**。
- どうやって: アクションをやめ MIT の gitleaks バイナリを直接取得。版と sha256 はワークフローに固定し検証。Dependabot では更新できないため、最新タグとの照合をテストで行う。全履歴（`--log-opts="--all"`）を `gitleaks git` でスキャン、結果は SARIF で `codeql-action/upload-sarif` へ。README から `GITLEAKS_LICENSE` を消し、`id-token: write` も削除。完了条件: シークレット無しで PR が通る、`fixture/` の試験文字列を検出、README から言及が消える。
- どれだけ: Issue 総数 117。固定値の実数はページに無い。
- 私たちへ: **版固定は Dependabot が追えないので更新検知の仕組みが別に要る**。限界: 公開ツール系の小規模倉庫。

### C-6. locknessland/lockness-monorepo Issue #390（URL は /pull/390 だが開くと Issue）
- 出典: https://github.com/locknessland/lockness-monorepo/pull/390 / 2026-09-24 起票・同日クローズ / 作者 kevinkod
- 何が起きた: 9/4〜9/24 の **125 回の実行がすべて失敗**し、秘密情報スキャンが**一度も走っていなかった**（"organization. License key is required."）。
- どうやって: v8.30.1 を固定し sha256 をハードコードして使用前に検証。全履歴を、結果を伏せて表示。`ERR`/`FTL` 出力・「0 commits scanned」・漏れ件数不明のいずれでも失敗させる（fail closed）。`--ignore-gitleaks-allow` を付け、`.gitleaks.toml` があると実行拒否。公開ドキュメント用に fingerprint 指定の除外 4 件。`docs/testing.md` を更新。
- どれだけ: 初回の全履歴スキャン 1638 コミット・漏れ 0。検知確認（捨てブランチ）1639 コミット・検出 1 件、値はログに 0 回出現し、ブランチは削除済み。
- 残課題（原文）: 検出は公開後なので防止にはプッシュ保護などが要る。版の自動更新の仕組みは無い。
- 私たちへ: **「3 週間走らず失敗と気づかなかった」点が最大の教訓**。限界: 失敗が赤で出ていたのに放置された運用面の事例で、構成差が大きい。

### C-7. Youngshark-Tech/Skolara Issue #111（対応 PR #112。URL は /pull/111 で開くと Issue）
- 出典: https://github.com/Youngshark-Tech/Skolara/pull/111 / 2026-10-06 起票・同日クローズ / 作者 Roy-Wanyoike
- 何が起きた: 組織へ移管後、`gitleaks/gitleaks-action@v2` が組織ライセンスを要求。v3 でも `GITLEAKS_LICENSE` が要り、v2→v3 では直らない。同時に API ジョブのカバレッジ下限 8% が実測 7.8% を上回り失敗。
- どうやって: MIT の gitleaks v8.30.1 を SHA256 検証つきで取得し `gitleaks detect` で全履歴をスキャン。履歴上の 2 件は誤検知と判断して `.gitleaksignore` に理由つきで登録。カバレッジ下限を 7.5% に。変更は `ci.yml` と新規 `.gitleaksignore` のみ。受け入れ基準は main で全 9 ジョブ成功。
- 注意点: 本文にはバイナリの SHA256 の先頭が出ているが、ここには転記しない。
- 限界: 結果（全 9 ジョブ成功の確認）は読めていない。

### C-8. bex.co のブログ（2026-10-02）
- 見つからず（開けず）。検索にも出なかった。

## 5. 根拠の強さ（A・B・C）

- **A（成功事例）: 弱。** 依頼の例（GitHub 社ブログ・Trunk・Uber）が開けず、開けた 3 件は導入決定・準備・感想で、効果の実測値が無い。
- **B（失敗事例）: 強。** 同じ原因（`merge_group` 未設定・paths 絞り・名前不一致・古い実行の放置・重複実行）が、別々の人から 9 件、日付つきで確認できた。ただし多くはコミュニティの報告で、GitHub 公式文書では裏取りしていない。
- **C（gitleaks CLI 移行）: 強。** 7 件で原因（組織名義はライセンス要）と対処（CLI を版固定・sha256 検証）が一致。数値の細部は要約抽出で、原文再読は未実施。

## 6. 未開封の候補（数値は書かない。許可ホストが増えたら開く）

- GitHub 社: https://github.blog/engineering/engineering-principles/how-github-uses-merge-queue-to-ship-hundreds-of-changes-every-day/
- Trunk の Caseware 事例（**売り手の主張**）: https://trunk.io/customers/caseware
- Uber 論文 Keeping Master Green at Scale（EuroSys '19）: https://www.uber.com/blog/research/keeping-master-green-at-scale
- GitHub 公式の必須チェックの障害解説: https://docs.github.com/en/enterprise-cloud@latest/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks
- 検索結果に出た他の候補: Plaid の merge queue、LeadDev の CI 半減記事、Samsara（導入して取りやめ）、Goliath Data（GitHub のキューから自作へ）
- 必要な許可ホスト: github.blog、docs.github.com、trunk.io、uber.com、lethain.com、plaid.com、leaddev.com、samsara.com、goliathdata.com、bex.co

## 7. 「続けさせる仕組み（機械の見張り）」に当たる外部の工夫

| 工夫 | 出どころ | 内容 |
|---|---|---|
| 構造を検証するテスト | cfgms #5972 | 重複 shard の復活や依存の弱体化があれば失敗させる |
| 最新版との照合テスト | git-your-ship-together #90 | Dependabot が追えない固定版を、テストで最新タグと照合 |
| fail closed | lockness-monorepo #390 | ERR/FTL、0 commits scanned、件数不明で失敗。.gitleaks.toml があれば実行拒否 |
| 検知の実証 | Editrace #333・lockness #390 | 偽の鍵や試験文字列を仕込んで検出と終了コードを確認 |
| 古い実行の自動キャンセル | smith #2241 | queue-guard が消えた gh-readonly-queue 参照の実行を取り消す |
| 必須チェック名を変えない | siterep-public #6 関連 | CLI 移行後もチェック名 Gitleaks を維持 |
| merge-gatekeeper | community #15254 | パスで動くワークフローを必須にせず 1 つの門番に集約 |
| 変更判定ジョブ | community #45899 | paths を使わず先に判定ジョブを置く |
| 手動キャンセル手順の削除 | smith #2241 | 手順書から手作業の記述を消す |

私たちへの含意（推測を含む）: 「版固定の更新検知」「fail closed」「検知の実証」「キュー内の重複確認」「`merge_group` と必須チェック名の一致確認」を機械の見張りにする案が外部事例と整合する。採否は設計役が判断する。
