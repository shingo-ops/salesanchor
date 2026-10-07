# recon: LLM使用量ダッシュボードのコスト表示を円（JPY）換算にする

## 対象
`frontend/src/pages/super-admin/components/LlmUsageSection.tsx`（LLM使用量台帳 ADR-1004 のダッシュボードタブ）。
origin/main `5f311c726e9e4089427456dd35313cd363db1cec`（PR #3907 マージ後）時点のコード。

## PO指示
2026-10-01、PO承認「よい」。設計者（Opus）の提案: LLM使用量コストを現在の為替レートで円表示する。

## 着手前ADR検索（`git grep -i -l "llm.usage\|fx-rate\|app_fx_rates" docs/adr/` の結果）
- `docs/adr/ADR-1004-llm-usage-ledger.md` — このセクション自体の由来（`public.llm_usage_events`）。本変更はこのADRの対象コンポーネントの表示整形のみで、スキーマ・API契約には触れない。
- `docs/adr/ADR-148-fx-rate-ssot.md` — 為替レート SSOT の定義。`docs/adr/FEATURE-INDEX.md` には `fx`/`llm`/`usage` に対応するエントリなし（grep 0件）。

## 為替レート SSOT（ADR-148）

### テーブル
`public.app_fx_rates`（通貨ごとに1行、`backend/app/tasks/fx_rate_updater.py` が Celery Beat で1日2回 06:00/18:00 JST に UPSERT）。

### 読み取りAPI
`backend/app/routers/fx_rate_admin.py:35-70`
```python
class FxRateResponse(BaseModel):
    currency: str
    rate_jpy: float
    fetched_at: str
    updated_at: str


@router.get(
    "/fx-rate/{currency}",
    response_model=FxRateResponse,
    tags=["fx-rate"],
)
async def get_fx_rate(
    currency: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """public.app_fx_rates から指定通貨の現在レートを返す。

    行が存在しない場合は 404 を返す。
    """
    result = await db.execute(
        text(
            "SELECT currency, rate_jpy, fetched_at, updated_at "
            "FROM public.app_fx_rates "
            "WHERE currency = :cur"
        ),
        {"cur": currency.upper()},
    )
    row = result.mappings().first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"為替レートが未取得です: {currency.upper()}",
        )
    return FxRateResponse(
        currency=row["currency"],
        rate_jpy=float(row["rate_jpy"]),
        fetched_at=row["fetched_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )
```
- 認可: `get_current_user` のみ（`require_super_admin` ではない）。ログイン済み全ユーザーが読める（ファイル冒頭コメント `backend/app/routers/fx_rate_admin.py:9` 「読み取りは全ログイン済みユーザーが可（為替は秘匿でない）」）。
- 書き込み（`POST /super-admin/fx-rate/refresh`）は `require_super_admin` のみ。本変更では触らない。
- レスポンスフィールド名: `currency`, `rate_jpy`, `fetched_at`, `updated_at`（すべて文字列/数値、ISO日時文字列）。

### 本番の現在値（PO提供・2026-09-30時点）
USD `rate_jpy = 157.3812`、`fetched_at = 2026-09-30 21:00 UTC`。

## フロントエンドの既存クライアント有無

`git grep -rn "fx-rate" frontend/src` の結果、共有クライアント/hookは**存在しない**。各ページが個別に `api.get<FxRate>("/fx-rate/...")` を直接呼んでいる:

- `frontend/src/pages/super-admin/FxRatePage.tsx:20-25, 40`
  ```tsx
  interface FxRate {
    currency: string;
    rate_jpy: number;
    fetched_at: string;
    updated_at: string;
  }
  ...
  const data = await api.get<FxRate>("/fx-rate/USD");
  ```
- `frontend/src/pages/quote-detail/QuoteDetailPage.tsx:19, 105`（`interface FxRateResult` + `api.get<FxRateResult>(`/fx-rate/${quote.currency}`)`）

→ 本変更も同じパターン（コンポーネント内に `interface FxRate` を定義し `api.get` を直接呼ぶ）を踏襲した。新規の共有クライアント／hookは作らない（YAGNI、既存に合わせる）。

## LlmUsageSection.tsx の現状（コスト表示箇所の棚卸し、origin/main時点）

- `makeCurrencyFormatter`（旧: `frontend/src/pages/super-admin/components/LlmUsageSection.tsx:265-273`）: USD固定（`style: "currency", currency: "USD", minimumFractionDigits: 4, maximumFractionDigits: 4`）。
- `formatCompactNumber`（旧: `:292-294`）: 言語のみでロケール整形、通貨単位なし（`notation: "compact"`）。全チャートの `YAxis tickFormatter` として `compactTick`（`:362`）で共通使用。
  - コストチャート（日次・月次の使いみち別積み上げ棒）のY軸ティックも `compactTick` を使っており、**単位（$記号）が付かない**（PO指定の既知の課題）。
- `formatChartCurrency`（旧: `:480`）: コストチャートの `Tooltip formatter` のみに適用（`formatCurrency(value, t)`）。Y軸ティックには適用されていない。
- コスト表示箇所の一覧（`grep -n "cost_usd\|formatCurrency" frontend/src/pages/super-admin/components/LlmUsageSection.tsx` で確認）:
  1. サマリーヒーロー（`:511`、旧 `formatCurrency(data.total.cost_usd, t)`）
  2. 使いみち別テーブル `cost_usd` 列（旧 `:416`）
  3. 日別テーブル `cost_usd` 列（旧 `:454`）
  4. モデル別テーブル `cost_usd` 列（旧 `:473`）
  5. 日次費用（使いみち別）積み上げ棒チャート（`dailyByPurposeData`、データ値＋Tooltip）
  6. 月次費用（使いみち別）積み上げ棒チャート（`monthlyByPurposeData`、データ値＋Tooltip）
  - 非コストチャート（リクエスト数・エラー数・モデル別トークン/リクエスト推移）は `cost_usd` を扱わないため対象外。

## テスト現状
`frontend/src/pages/super-admin/components/LlmUsageSection.test.tsx`:
- `beforeEach` で `vi.mocked(api.get).mockResolvedValue(response)` としており、**URLを問わず同じ `response` を返す**モック構成。本変更で `api.get` の呼び出しが2本（llm-usage + fx-rate/USD）になった際、既存のこのモックは両方に同じ `response`（`rate_jpy` フィールドなし）を返すため、実装側で `typeof fx.rate_jpy === "number"` のガードが必要（既存テスト "formats cost as a USD currency string" 等を壊さないため）。
- 既存テスト19件はすべて `$0.0021`（USD表示）を前提にしている → fx-rate 未モック時は USD フォールバックのままである必要がある。

## i18n（着手前の `usage` 配下の既存キー、ja.json/en.json 4478-4527行）
`analysisRules.dashboard.usage.*` 配下に `fx` オブジェクトは存在しない（新規追加が必要）。
