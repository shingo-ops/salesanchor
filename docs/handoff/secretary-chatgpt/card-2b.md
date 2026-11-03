# 実装カード 段2b: 「AI の担当」タブの表を読みやすくする（ADR-1058）

## なぜ
- 2026-11-04 PO が本番の画面写真を添えて「長々と書いてあるから全体的に潰れてる　仕事→役割に変更」と指示。
- 写真で見えた事実: 表が10列あり、「仕事」「モデル」の列が1〜数文字ごとに折り返して縦に伸びている。右の列（直近24時間の失敗・最後の失敗の理由・ChatGPT のログインの更新日・切り替え）は横スクロールしないと見えず、秘書の行の「変える」ボタンが最初の画面に出ていない。
- 原因（実物）: frontend/src/pages/super-admin/components/AiJobsSection.tsx:160-207 が10列を並べ、見出しは折り返さない（frontend/src/components/DataTable.css:44 `white-space: nowrap`）が中身は折り返す（DataTable.css:53-58 に nowrap なし）。見出しの長い列が幅を取り、中身の短い列が押し潰される。

## 決めたこと（Opus の設計判断。見せる情報は減らさない）
1. 言葉の「仕事」を「役割」に替える（ja）。en は Job → Role。
2. 列を10から8に減らす。情報は消さずに1つのセルにまとめる。
   - 「AI」と「モデル」→「AI・モデル」1列（既存の choiceLabel で `Gemini・gemini-3.1-flash-lite`）
   - 「直近24時間の回数」と「直近24時間の失敗」→「直近24時間」1列（`70 回（失敗 0）`）
   - 「最後の失敗の理由」と「ChatGPT のログインの更新日」はそのまま残す
3. 「切り替え」列を「ログイン」の次（4列目）に動かし、最初の画面で「変える」が見えるようにする。
4. 文字の列は全部、金型 DataTable の `ellipsis: true` で1行に収める（新しい CSS は書かない）。
5. 見出しを短くする（下の表）。

## 触るファイル（この3つと試験1つだけ）
- frontend/src/pages/super-admin/components/AiJobsSection.tsx
- frontend/src/pages/super-admin/components/AiJobsSection.test.tsx
- frontend/src/locales/ja.json
- frontend/src/locales/en.json

## 触らない
- backend 一式・openapi.json・DataTable.tsx/.css（金型は変えない）・AnalysisDashboardPanel.tsx・CSS ファイル全部
- 変えた記録の表（historyColumns）は、列の見出しキー colJob の言葉が「役割」に替わるだけで、コードは触らない

## 1. AiJobsSection.tsx の jobColumns（現 160-207 行）を次に置き換える

```tsx
  const jobColumns: DataTableColumn<AiJob>[] = [
    { key: "job_key", header: t("analysisRules.dashboard.aiJobs.colJob"), ellipsis: true, renderCell: (row) => jobLabel(row.job_key, t) },
    {
      key: "model",
      header: t("analysisRules.dashboard.aiJobs.colAiModel"),
      ellipsis: true,
      renderCell: (row) => choiceLabel({ provider: row.provider, model: row.model }, t),
    },
    {
      key: "login_ok",
      header: t("analysisRules.dashboard.aiJobs.colLogin"),
      ellipsis: true,
      renderCell: (row) =>
        row.login_ok ? (
          <Badge variant="success" size="sm">{t("analysisRules.dashboard.aiJobs.loginOk")}</Badge>
        ) : (
          <Badge variant="danger" size="sm">
            {row.login_reason ? loginReasonLabel(row.login_reason, t) : t("analysisRules.dashboard.aiJobs.loginNg")}
          </Badge>
        ),
    },
    {
      key: "switchable",
      header: t("analysisRules.dashboard.aiJobs.colAction"),
      ellipsis: true,
      renderCell: (row) =>
        row.switchable ? (
          <Button variant="secondary" size="sm" onClick={() => openChange(row)}>
            {t("analysisRules.dashboard.aiJobs.change")}
          </Button>
        ) : (
          t("analysisRules.dashboard.aiJobs.notSwitchable")
        ),
    },
    { key: "last_ok_at", header: t("analysisRules.dashboard.aiJobs.colLastOk"), ellipsis: true, renderCell: (row) => formatAt(row.last_ok_at, t) },
    {
      key: "count_24h",
      header: t("analysisRules.dashboard.aiJobs.col24h"),
      align: "right",
      ellipsis: true,
      renderCell: (row) => t("analysisRules.dashboard.aiJobs.count24h", { count: row.count_24h, failed: row.failed_24h }),
    },
    {
      key: "last_error_code",
      header: t("analysisRules.dashboard.aiJobs.colLastError"),
      ellipsis: true,
      renderCell: (row) =>
        row.last_error_code
          ? t("analysisRules.dashboard.aiJobs.lastErrorWithAt", {
              reason: errorCodeLabel(row.last_error_code, t),
              at: formatAt(row.last_error_at, t),
            })
          : t("analysisRules.dashboard.aiJobs.none"),
    },
    {
      key: "login_refreshed_at",
      header: t("analysisRules.dashboard.aiJobs.colLoginRefreshed"),
      ellipsis: true,
      renderCell: (row) => formatAt(row.login_refreshed_at, t),
    },
  ];
```

並び（8列）: 役割／AI・モデル／ログイン／切り替え／最後に動いた日時／直近24時間／最後の失敗の理由／ログインの更新日。

## 2. 言葉（analysisRules.dashboard.aiJobs の中。ja と en で同じキー）

| キー | ja 変更前 → 変更後 | en 変更前 → 変更後 |
|---|---|---|
| title | 仕事ごとの AI の担当 → 役割ごとの AI の担当 | AI assigned to each job → AI assigned to each role |
| colJob | 仕事 → 役割 | Job → Role |
| colLastOk | 最後にうまく動いた日時 → 最後に動いた日時 | Last success（変えない） |
| colLoginRefreshed | ChatGPT のログインの更新日 → ログインの更新日 | ChatGPT login refreshed → Login refreshed |
| colAction | 切り替え（変えない） | Switch（変えない） |
| colAiModel（新規） | AI・モデル | AI / model |
| col24h（新規） | 直近24時間 | Last 24h |
| count24h（新規） | {{count}} 回（失敗 {{failed}}） | {{count}} calls ({{failed}} failed) |
| colProvider・colModel・colCount24h・colFailed24h | 削除（どこからも使われなくなる） | 削除 |

削除の前に `git grep -n "aiJobs.colProvider\|aiJobs.colModel\|aiJobs.colCount24h\|aiJobs.colFailed24h" -- frontend/src` で使い先が AiJobsSection.tsx だけ（置き換え後は0件）であることを確かめる。他に使い先があれば削除せず止まって報告。

en の count24h は i18next の複数形の決まりに当たらないよう、キー名は count24h のまま `{{count}}` を使う。i18next が `count` で複数形キー（count24h_one など）を探して見つからない場合は count24h が使われる。試験で en の表示が `70 calls (0 failed)` になることを確かめる。

## 3. 試験（AiJobsSection.test.tsx）
- 既存の試験が見出しや列の数・順番に依存していれば、新しい8列に合わせて直す。
- 次を足す:
  - 見出しに「役割」「AI・モデル」「直近24時間」が出て、「仕事」が出ない
  - 秘書の行（switchable: true）で「変える」ボタンが4列目のセルにある
  - 回数のセルが `70 回（失敗 0）` の形
  - 新しいキー colAiModel・col24h・count24h が ja と en の両方にある

## 4. 確かめ（実装担当が手元で流す）
- `npm run test:unit -- AiJobsSection` が全部 pass
- `npx tsc --noEmit -p frontend` で触った2ファイルに型の誤り0件
- `npm run check:i18n-missing-keys`・`npm run lint`・UI governance（`bash scripts/dev/check-before-submit.sh` に含む）が通る
- `bash scripts/dev/check-before-submit.sh` 終了コード0

## 5. 受入（PO が本番の画面で○×）
| 基準 | 確かめ方 |
|---|---|
| K1 見出しと表題に「仕事」が無く「役割」になっている | 「AI の担当」タブを開いて目で見る |
| K2 どのセルも1行に収まり、1〜数文字ごとの折り返しが無い | 同じ画面（幅 1100px 前後のブラウザ） |
| K3 横スクロールせずに、秘書の行の「変える」ボタンが見える | 同じ画面 |
| K4 「変える」を押すと選ぶ画面が開く（前と同じ） | 押して、「やめる」で閉じる |

## 戻し方
この PR を revert する（backend・DB は触らないので画面だけ元に戻る）。
