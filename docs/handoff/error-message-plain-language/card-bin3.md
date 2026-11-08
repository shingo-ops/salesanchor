---
mode: handoff
---
# 実装カード 便3: 「〇〇が見つかりません」を、名前を残した理由コードにする（ADR-1071 A2 の2回目）

親: [design.md](./design.md) §12。ADR: [ADR-1071](../../adr/ADR-1071-plain-language-error-messages.md)。

- 状態: カード作成済み（2026-11-08 Opus）。
- 実装承認: PO 2026-11-08 の選択「1」（「この文と名前で決まり、作り始める」。選ぶと、作る・確かめる・本番に出すまでを Opus が進める）。マージと本番への反映の GO は Opus が委任（ADR-1003）に基づき別に出す。
- 担当: クラウドの Sonnet（実装）。Opus は審査・PR 作成・GO・マージ判断。
- 読んだ節: docs/handoff/design-partner-card-ops/guards/ の 00-common.md・03-file.md・04-worktree.md・10-executor.md
- 区分: サーバーの失敗の応答の detail の文字列・画面の API の受け口・文言・試験。migrations・deploy.yml・本番 scripts/・.github/ は触らない。
- 作業する枝: `release/error-text-bin3-not-found-design`（設計の文書とこのカードが載って push 済み）。新しい枝は作らない。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5 の照合結果）

| 番号 | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲む | ○ |
| 2 | PR は Opus が作る（担当は PR を作らない） | ○（§6） |
| 3 | 報告の宛先（完了報告の本文に生出力を全文） | ○（§7） |
| 4 | 1便1目的（design §12-10 の 198 か所の「見つかりません」だけ。f 文字列・状態番号の違うもの・PDF は直さない） | ○ |
| 5 | 既存の枝の起点を明示（origin/release/error-text-bin3-not-found-design） | ○（§5 手順1） |
| 6 | 書式は実例で示す（作るコードを全部書く。名前と文は design §12-4・§12-5 から台本で入れる） | ○（§3） |
| 7 | 合格基準を出力まで縛る（触るファイル以外 0） | ○（§5 手順7・9・10） |
| 8 | 件数の判定には名前を出す手順を対で置く | ○（§5 手順3・4） |
| 9 | 出力量に上限のないコマンドを使わない | ○（`| tail -N`） |
| 10 | 報告様式3点（停止の3点・受領と終端の合図・冒頭の便名） | ○（§7） |
| 11 | 行番号を停止条件にしない（前後の文で探す。台本は「行＋今の文」が両方合うときだけ直す） | ○（§3） |
| 12 | 停止は不可逆・本番影響のものだけ。数の食い違いは記録して続行 | ○（§4） |
| 13 | 委任文の定型4点（sleep 禁止・Write/Edit で書く・PR は作らない・フックに止められたら言い換えない） | ○（§4） |

## 1. 目的（便3 で起きること）

- サーバーの 198 か所（65 ファイル）の「〇〇が見つかりません」を、`not_found:<対象>` の文字列に置き換える（design §12-10 の表が正）。状態番号は変えない。
- 画面の API の受け口（`frontend/src/lib/api.ts` の2か所）で `not_found:` で始まるコードを受けたら、design §12-4 の型の文に §12-5 の名前を入れた文（画面の言語）を出す。表に無い対象は名前なしの文。ほかは今までどおり。
- W1 の基準値を 647 → 449 に下げる。

## 2. 触るファイル（これ以外は触らない）

| # | ファイル | 新規/変更 |
|---|---|---|
| 1 | `backend/app/routers/` の下の 65 ファイル（§3-1 の台本が置き換えたファイルだけ） | 変更（detail の文字列だけ） |
| 2 | `backend/tests/error_detail_baseline.json` | 変更（台本で書き出す。手で直さない） |
| 3 | `backend/tests/test_staff_me.py` | 変更（1 行） |
| 4 | `backend/tests/test_api_error_reason_sync.py` | 変更（全文を §3-7 にする） |
| 5 | `frontend/src/lib/apiErrorReason.ts` | 変更（全文を §3-3 にする） |
| 6 | `frontend/src/lib/apiErrorReason.test.ts` | 変更（全文を §3-6 にする） |
| 7 | `frontend/src/lib/api.ts` | 変更（import 1 行・関数 1 つ・2 か所） |
| 8 | `frontend/src/lib/api.httpError.test.ts` | 変更（試験を足す） |
| 9 | `frontend/src/locales/ja.json`・`frontend/src/locales/en.json` | 変更（§3-5 の台本で `apiError` に足す） |
| 10 | `frontend/tests-e2e/order-commission.spec.ts`・`order-financial.spec.ts`・`order-purchase.spec.ts`・`order-shipping.spec.ts` | 変更（見本の detail の文字列だけ。§3-9） |

## 3. 作る中身（design §12 が正。食い違えば design に従い、報告に書く）

### 3-1 サーバーの文の置き換え（台本で行う。ファイルごとに手で直さない）

台本 `/tmp/replace_bin3.py`（Write で作る。リポジトリには入れない）。design.md §12-10 の表の各行（ファイル:行・今の文・新しい detail）について、その行で始まる `HTTPException(...)` の detail（`detail=` か 2 つ目の位置引数）の文字列が「今の文」と一致するときだけ置き換える:

```python
"""便3: design.md §12-10 の表を正として、198 か所の detail を not_found:<対象> に置き換える。

引数: <repo>（backend/ と docs/ の親）
- 表の各行（ファイル:行・今の文・新しい detail）について、その行で始まる HTTPException(...) の
  detail= の文字列リテラルを AST で探し、値が「今の文」と一致するときだけ、そのリテラルの範囲を
  "not_found:<対象>" に置き換える。一致しない行は置き換えずに MISMATCH として出す。
"""
import ast
import re
import sys
from collections import defaultdict
from pathlib import Path

repo = Path(sys.argv[1])
design = (repo / "docs/handoff/error-message-plain-language/design.md").read_text(encoding="utf-8")
sec = design.split("### 12-10.", 1)[1]
ROW = re.compile(r"^\| (backend/app/[^:|]+\.py):(\d+) \| [^|]* \| ([^|]+?) \| `(not_found:[a-z0-9_]+)` \|$", re.M)
rows = ROW.findall(sec)
print("table rows", len(rows))

by_file = defaultdict(list)
for f, line, old, new in rows:
    by_file[f].append((int(line), old.strip(), new))

done = 0
mismatch = []
for f, items in sorted(by_file.items()):
    p = repo / f
    src = p.read_text(encoding="utf-8")
    lines = src.split("\n")
    tree = ast.parse(src)
    calls = defaultdict(list)
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and getattr(n.func, "id", getattr(n.func, "attr", None)) == "HTTPException":
            calls[n.lineno].append(n)
    edits = []
    for line, old, new in items:
        found = None
        for c in calls.get(line, []):
            # detail は detail= か、2つ目の位置引数（HTTPException(404, "…")）
            cands = [kw.value for kw in c.keywords if kw.arg == "detail"] + c.args[1:2]
            for v in cands:
                if isinstance(v, ast.Constant) and v.value == old:
                    found = v
        if found is None or found.lineno != found.end_lineno:
            mismatch.append(f"{f}:{line} {old}")
            continue
        edits.append((found.lineno, found.col_offset, found.end_col_offset, new))
    # 同じ行に2つ以上あっても壊れないよう、後ろから置き換える（col は UTF-8 のバイト位置）
    for ln, a, b, new in sorted(edits, reverse=True):
        raw = lines[ln - 1].encode("utf-8")
        lines[ln - 1] = (raw[:a] + f'"{new}"'.encode("utf-8") + raw[b:]).decode("utf-8")
        done += 1
    p.write_text("\n".join(lines), encoding="utf-8")
print("replaced", done, "files", len(by_file), "mismatch", len(mismatch))
for m in mismatch:
    print("MISMATCH", m)
```

期待（Opus が `510fc3579` の写しで流した値）: `table rows 198`・`replaced 198 files 65 mismatch 0`。違っても止まらず、数と MISMATCH の行を報告に書く。

### 3-2 `backend/tests/test_staff_me.py`

`assert "staff" in body["detail"] or "見つかりません" in body["detail"]` の 1 行を `assert body["detail"] == "not_found:my_staff_profile"` にする。ほかは変えない。

### 3-3 `frontend/src/lib/apiErrorReason.ts`（全文をこのとおりにする）

```ts
import i18n from "../i18n";

/**
 * サーバーが失敗の応答の detail に文字列で返す、画面に共通の理由コード → 文言キーの対応表（ADR-1071 便2）。
 *
 * frontend/src/lib/api.ts が、detail がこの表のコードのときだけ i18n の文を ApiError.message にする。
 * 表に無いコードは今までどおり detail をそのまま message にする（コードを比べている画面を壊さないため）。
 * 新しいコードを足すときは、この表に 1 行と、ja.json・en.json の apiError に文を足す。
 * 突き合わせの試験: apiErrorReason.test.ts（画面側）・backend/tests/test_api_error_reason_sync.py（サーバー側）。
 */
export const API_ERROR_REASON_KEYS: Readonly<Record<string, string>> = {
  no_fields_to_update: "apiError.noFieldsToUpdate",
  conflict_constraint: "apiError.conflictConstraint",
};

/** detail が表のコードなら文言キー、そうでなければ null */
export function apiErrorReasonKey(detail: unknown): string | null {
  if (typeof detail !== "string") return null;
  return Object.prototype.hasOwnProperty.call(API_ERROR_REASON_KEYS, detail)
    ? API_ERROR_REASON_KEYS[detail]
    : null;
}

/** サーバーの「見つからない」の detail の頭（ADR-1071 便3）。後ろに対象のコードが付く（例 not_found:lead） */
export const NOT_FOUND_PREFIX = "not_found:";

/**
 * 「見つからない」の対象 → 名前の文言キーの対応表（ADR-1071 便3・design §12-5）。
 * 新しい対象を足すときは、この表に 1 行と、ja.json・en.json の apiError.notFoundTarget に名前を足す。
 * 突き合わせの試験は API_ERROR_REASON_KEYS と同じ 2 つ。
 */
export const NOT_FOUND_TARGET_KEYS: Readonly<Record<string, string>> = {
  lead: "apiError.notFoundTarget.lead",
  order: "apiError.notFoundTarget.order",
  company: "apiError.notFoundTarget.company",
  condition: "apiError.notFoundTarget.condition",
  product: "apiError.notFoundTarget.product",
  contact: "apiError.notFoundTarget.contact",
  alias: "apiError.notFoundTarget.alias",
  invoice: "apiError.notFoundTarget.invoice",
  supplier_master: "apiError.notFoundTarget.supplier_master",
  team: "apiError.notFoundTarget.team",
  bot: "apiError.notFoundTarget.bot",
  my_staff_profile: "apiError.notFoundTarget.my_staff_profile",
  calendar_event: "apiError.notFoundTarget.calendar_event",
  quote: "apiError.notFoundTarget.quote",
  order_purchase: "apiError.notFoundTarget.order_purchase",
  payment_fee_setting: "apiError.notFoundTarget.payment_fee_setting",
  product_category: "apiError.notFoundTarget.product_category",
  supplier: "apiError.notFoundTarget.supplier",
  role: "apiError.notFoundTarget.role",
  status: "apiError.notFoundTarget.status",
  unit: "apiError.notFoundTarget.unit",
  order_financial: "apiError.notFoundTarget.order_financial",
  order_shipping: "apiError.notFoundTarget.order_shipping",
  staff: "apiError.notFoundTarget.staff",
  condition_definition: "apiError.notFoundTarget.condition_definition",
  product_format: "apiError.notFoundTarget.product_format",
  quantity_unit: "apiError.notFoundTarget.quantity_unit",
  distribution_target: "apiError.notFoundTarget.distribution_target",
  line_import_job: "apiError.notFoundTarget.line_import_job",
  calendar_owner: "apiError.notFoundTarget.calendar_owner",
  conv_log: "apiError.notFoundTarget.conv_log",
  channel_master: "apiError.notFoundTarget.channel_master",
  goal: "apiError.notFoundTarget.goal",
  inventory_offer: "apiError.notFoundTarget.inventory_offer",
  message: "apiError.notFoundTarget.message",
  notice: "apiError.notFoundTarget.notice",
  notification_channel: "apiError.notFoundTarget.notification_channel",
  own_inventory: "apiError.notFoundTarget.own_inventory",
  product_master: "apiError.notFoundTarget.product_master",
  dex_entry: "apiError.notFoundTarget.dex_entry",
  knowledge_rule: "apiError.notFoundTarget.knowledge_rule",
  note_master: "apiError.notFoundTarget.note_master",
  product_kind: "apiError.notFoundTarget.product_kind",
  product_line: "apiError.notFoundTarget.product_line",
  tcg_series: "apiError.notFoundTarget.tcg_series",
  tcg_type: "apiError.notFoundTarget.tcg_type",
  tenant: "apiError.notFoundTarget.tenant",
  weight_class: "apiError.notFoundTarget.weight_class",
  archive_target: "apiError.notFoundTarget.archive_target",
  archive: "apiError.notFoundTarget.archive",
  badge: "apiError.notFoundTarget.badge",
  close_reason: "apiError.notFoundTarget.close_reason",
  deal: "apiError.notFoundTarget.deal",
  message_label: "apiError.notFoundTarget.message_label",
  meta_page: "apiError.notFoundTarget.meta_page",
  role_commission: "apiError.notFoundTarget.role_commission",
  purchase_order: "apiError.notFoundTarget.purchase_order",
  order_item: "apiError.notFoundTarget.order_item",
  user: "apiError.notFoundTarget.user",
  shift: "apiError.notFoundTarget.shift",
  shipping_zone: "apiError.notFoundTarget.shipping_zone",
  shipping_rate: "apiError.notFoundTarget.shipping_rate",
  staff_join_invite: "apiError.notFoundTarget.staff_join_invite",
  staff_report: "apiError.notFoundTarget.staff_report",
  discord_routing: "apiError.notFoundTarget.discord_routing",
  knowledge_link: "apiError.notFoundTarget.knowledge_link",
  team_member: "apiError.notFoundTarget.team_member",
};

/**
 * detail が `not_found:<対象>` なら画面の言語の文、そうでなければ null。
 * 表に無い対象は名前なしの文（apiError.notFoundUnknown）。コードの生の値は画面に出さない。
 * detail をそのまま i18n.t に渡さない（":" は i18next の名前空間の区切りのため）。
 */
export function notFoundMessage(detail: unknown): string | null {
  if (typeof detail !== "string" || !detail.startsWith(NOT_FOUND_PREFIX)) return null;
  const target = detail.slice(NOT_FOUND_PREFIX.length);
  if (!Object.prototype.hasOwnProperty.call(NOT_FOUND_TARGET_KEYS, target)) {
    return i18n.t("apiError.notFoundUnknown");
  }
  return i18n.t("apiError.notFound", { target: i18n.t(NOT_FOUND_TARGET_KEYS[target]) });
}

/** 共通の理由コード（便2）か「見つからない」（便3）なら画面の言語の文、どちらでもなければ null */
export function apiErrorReasonMessage(detail: unknown): string | null {
  const key = apiErrorReasonKey(detail);
  if (key) return i18n.t(key);
  return notFoundMessage(detail);
}
```

### 3-4 `frontend/src/lib/api.ts`

- import の行 `import { apiErrorReasonKey } from "./apiErrorReason";` を `import { apiErrorReasonMessage } from "./apiErrorReason";` にする。
- `async function request<T>(` の行の直前（空行 1 つを空けて）に次の関数を足す:

```ts
/** 失敗の応答の detail から ApiError.message を作る（request と requestForm の共通・ADR-1071） */
function errorMessageFromDetail(detail: unknown, status: number): string {
  // 共通の理由コード・「見つからない」のコードなら画面の言語の文、
  // それ以外の文字列ならそのまま、dict なら detail フィールドを優先
  const reasonMessage = apiErrorReasonMessage(detail);
  if (reasonMessage) return reasonMessage;
  if (typeof detail === "string") return detail;
  return (detail as { detail?: string } | null | undefined)?.detail || i18n.t("common.httpError", { status });
}
```

- `request` の中の `if (!res.ok) {` のかたまり（`const reasonKey = apiErrorReasonKey(detail);` があるところ）を次にする:

```ts
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        const detail = body?.detail;
        throw new ApiError(errorMessageFromDetail(detail, res.status), res.status, detail);
      }
```

- `requestForm` の中の `if (!res.ok) {` のかたまり（`const reasonKey = apiErrorReasonKey(detail);` があるところ）を次にする:

```ts
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    const detail = (errBody as { detail?: unknown }).detail;
    throw new ApiError(errorMessageFromDetail(detail, res.status), res.status, detail);
  }
```

- 終わったら `cd <repo> && git grep -n "apiErrorReasonKey" -- frontend/src | tail -10` を流す。合格: `frontend/src/lib/apiErrorReason.ts` と `frontend/src/lib/apiErrorReason.test.ts` の中だけ。
- ほかの所は変えない。型の都合で `i18n.t(...)` が通らないときは、止まらずに最小の直し（例 `String(i18n.t(...))`）をし、報告に書く。

### 3-5 文言（台本で足す。手で書かない）

台本 `/tmp/add_locale_bin3.py`（Write で作る。リポジトリには入れない）。design §12-4 の 2 つの文と §12-5 の 67 の名前を、ja.json・en.json の `apiError` の最後の行（`"conflictConstraint": ...`）の後ろに文字として差し込む（ほかの行は変えない）:

```python
"""便3: design.md §12-4・§12-5 を正として、ja.json・en.json の apiError に文と 67 の名前を足す。

引数: <repo>。apiError の最後の行（"conflictConstraint": ...）の後ろに、文字として差し込む（ほかの行は変えない）。
"""
import json
import re
import sys
from pathlib import Path

repo = Path(sys.argv[1])
design = (repo / "docs/handoff/error-message-plain-language/design.md").read_text(encoding="utf-8")
s4 = design.split("### 12-4.", 1)[1].split("### 12-5.", 1)[0]
s5 = design.split("### 12-5.", 1)[1].split("### 12-6.", 1)[0]
tmpl = dict(
    (k, (ja, en))
    for k, ja, en in re.findall(r"^\| `apiError\.(notFound|notFoundUnknown)` \| ([^|]+?) \| ([^|]+?) \|$", s4, re.M)
)
rows = re.findall(r"^\| `not_found:([a-z0-9_]+)` \| ([^|]+?) \| ([^|]+?) \| \d+ \|", s5, re.M)
print("templates", len(tmpl), "targets", len(rows))
for lang, col in (("ja", 0), ("en", 1)):
    p = repo / f"frontend/src/locales/{lang}.json"
    text = p.read_text(encoding="utf-8")
    anchor = re.compile(r'^(    "conflictConstraint": "[^"\n]*")\n(  \}\n\}\n?)\Z', re.M)
    m = anchor.search(text)
    if not m:
        print("ANCHOR NOT FOUND", lang)
        sys.exit(1)
    lines = [m.group(1) + ","]
    lines.append(f'    "notFound": {json.dumps(tmpl["notFound"][col], ensure_ascii=False)},')
    lines.append(f'    "notFoundUnknown": {json.dumps(tmpl["notFoundUnknown"][col], ensure_ascii=False)},')
    lines.append('    "notFoundTarget": {')
    body = [f"      {json.dumps(c)}: {json.dumps((ja if col == 0 else en), ensure_ascii=False)}" for c, ja, en in rows]
    lines.append(",\n".join(body))
    lines.append("    }")
    new = text[: m.start()] + "\n".join(lines) + "\n" + m.group(2)
    data = json.loads(new)
    print(lang, "notFoundTarget", len(data["apiError"]["notFoundTarget"]), "top keys", len(data))
    p.write_text(new, encoding="utf-8")
```

期待（Opus が `510fc3579` の写しで流した値）: `templates 2 targets 67`・`ja notFoundTarget 67 top keys 125`・`en notFoundTarget 67 top keys 125`。`ANCHOR NOT FOUND` が出たら BLOCKED。

### 3-6 `frontend/src/lib/apiErrorReason.test.ts`（全文をこのとおりにする）

試験のファイルに日本語を直接書かない（`eslint` の `local/no-japanese-literal` で止まるため。日本語の期待値は ja.json から読む）。

```ts
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import i18n from "../i18n";
import ja from "../locales/ja.json";
import en from "../locales/en.json";
import {
  API_ERROR_REASON_KEYS,
  NOT_FOUND_TARGET_KEYS,
  apiErrorReasonKey,
  apiErrorReasonMessage,
  notFoundMessage,
} from "./apiErrorReason";

type Dict = Record<string, unknown>;
const lookup = (d: Dict, key: string): unknown =>
  key.split(".").reduce<unknown>((cur, k) => (cur && typeof cur === "object" ? (cur as Dict)[k] : undefined), d);

// CI checks out the whole repo and runs from frontend (precedent: src/features/discord-connect/discordConnectError.test.ts)
function readPyFiles(dir: string): string[] {
  const out: string[] = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...readPyFiles(p));
    else if (name.endsWith(".py")) out.push(readFileSync(p, "utf8"));
  }
  return out;
}

const sources = readPyFiles("../backend/app").join("\n");
const hasOwn = (o: object, k: string) => Object.prototype.hasOwnProperty.call(o, k);

describe("apiErrorReasonKey", () => {
  it("maps table codes to locale keys and returns null otherwise", () => {
    expect(apiErrorReasonKey("no_fields_to_update")).toBe("apiError.noFieldsToUpdate");
    expect(apiErrorReasonKey("conflict_constraint")).toBe("apiError.conflictConstraint");
    expect(apiErrorReasonKey("viewer_already_linked")).toBeNull();
    expect(apiErrorReasonKey("toString")).toBeNull();
    expect(apiErrorReasonKey({ reason: "no_fields_to_update" })).toBeNull();
    expect(apiErrorReasonKey(null)).toBeNull();
  });
});

describe("i18n", () => {
  it("has a non-empty ja and en text for every key", () => {
    for (const key of [...Object.values(API_ERROR_REASON_KEYS), ...Object.values(NOT_FOUND_TARGET_KEYS)]) {
      expect(lookup(ja as Dict, key), `ja:${key}`).toBeTruthy();
      expect(lookup(en as Dict, key), `en:${key}`).toBeTruthy();
    }
    for (const key of ["apiError.notFound", "apiError.notFoundUnknown"]) {
      expect(lookup(ja as Dict, key), `ja:${key}`).toBeTruthy();
      expect(lookup(en as Dict, key), `en:${key}`).toBeTruthy();
    }
  });
});

describe("backend sync", () => {
  it("every table code is used in backend/app", () => {
    expect(Object.keys(API_ERROR_REASON_KEYS).length).toBe(2);
    for (const code of Object.keys(API_ERROR_REASON_KEYS)) {
      expect(sources.includes(`"${code}"`), code).toBe(true);
    }
  });
});

describe("not_found:<target> (ADR-1071 bin3)", () => {
  afterEach(async () => {
    await i18n.changeLanguage("ja");
  });

  it("has 67 targets, each key named after its target", () => {
    expect(Object.keys(NOT_FOUND_TARGET_KEYS).length).toBe(67);
    for (const [target, key] of Object.entries(NOT_FOUND_TARGET_KEYS)) {
      expect(key).toBe(`apiError.notFoundTarget.${target}`);
    }
  });

  for (const lang of ["ja", "en"] as const) {
    const dict = (lang === "ja" ? ja : en) as Dict;

    it(`builds the ${lang} text for every target`, async () => {
      await i18n.changeLanguage(lang);
      const template = lookup(dict, "apiError.notFound") as string;
      expect(template).toContain("{{target}}");
      for (const [target, key] of Object.entries(NOT_FOUND_TARGET_KEYS)) {
        const name = lookup(dict, key) as string;
        const text = notFoundMessage(`not_found:${target}`);
        expect(text, `${lang}:${target}`).toBe(template.replace("{{target}}", name));
        expect(text).not.toContain("{{");
        expect(text).not.toContain("not_found");
      }
    });

    it(`uses the ${lang} text without a name for an unknown target`, async () => {
      await i18n.changeLanguage(lang);
      const unknown = lookup(dict, "apiError.notFoundUnknown");
      expect(notFoundMessage("not_found:zzz")).toBe(unknown);
      expect(notFoundMessage("not_found:toString")).toBe(unknown);
      expect(notFoundMessage("not_found:")).toBe(unknown);
    });
  }

  it("builds the en sentence for lead and an unknown target", async () => {
    await i18n.changeLanguage("en");
    expect(notFoundMessage("not_found:lead")).toBe("The lead could not be found. Reload the page and try again.");
    expect(notFoundMessage("not_found:zzz")).toBe(
      "What you were looking for could not be found. Reload the page and try again.",
    );
  });

  it("leaves other details to the caller", () => {
    for (const d of ["not_found", "company_not_found", "viewer_already_linked", "", null, 404, { detail: "x" }]) {
      expect(notFoundMessage(d)).toBeNull();
    }
    expect(apiErrorReasonMessage("viewer_already_linked")).toBeNull();
    expect(apiErrorReasonMessage("no_fields_to_update")).toBe(lookup(ja as Dict, "apiError.noFieldsToUpdate"));
    expect(apiErrorReasonMessage("not_found:lead")).toBe(notFoundMessage("not_found:lead"));
  });
});

describe("backend sync (bin3)", () => {
  const used = new Set(Array.from(sources.matchAll(/"not_found:([a-z0-9_]+)"/g), (m) => m[1]));

  it("every not_found target used in backend/app is in the table", () => {
    expect(Array.from(used).filter((t) => !hasOwn(NOT_FOUND_TARGET_KEYS, t))).toEqual([]);
  });

  it("every table target is used in backend/app", () => {
    expect(Object.keys(NOT_FOUND_TARGET_KEYS).filter((t) => !used.has(t))).toEqual([]);
  });
});
```

### 3-7 `backend/tests/test_api_error_reason_sync.py`（全文をこのとおりにする）

```python
"""画面の理由コードの表（frontend/src/lib/apiErrorReason.ts）とサーバーの突き合わせ（ADR-1071 便2・便3）。

サーバーだけを変えた PR でも、表とサーバーの理由コードがずれていないことを確かめる。
画面だけを変えた PR は frontend/src/lib/apiErrorReason.test.ts が同じことを確かめる。
DB・ネットワークは使わない。
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TABLE = REPO / "frontend" / "src" / "lib" / "apiErrorReason.ts"
APP_DIR = REPO / "backend" / "app"

# 便2 の表の行（例 `  no_fields_to_update: "apiError.noFieldsToUpdate",`）
_ROW = re.compile(r'^\s+([a-z0-9_]+): "apiError\.[A-Za-z0-9]+",?$', re.MULTILINE)
# 便3 の表の行（例 `  lead: "apiError.notFoundTarget.lead",`。キーと対象が同じ名前のものだけ）
_TARGET_ROW = re.compile(r'^\s+([a-z0-9_]+): "apiError\.notFoundTarget\.\1",?$', re.MULTILINE)
# サーバーの「見つからない」の detail（例 "not_found:lead"）
_APP_TARGET = re.compile(r'"not_found:([a-z0-9_]+)"')


def _table() -> str:
    return TABLE.read_text(encoding="utf-8")


def _codes() -> list[str]:
    return _ROW.findall(_table())


def _targets() -> list[str]:
    return _TARGET_ROW.findall(_table())


def _app_sources() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(APP_DIR.rglob("*.py")))


def test_table_rows_are_read():
    assert _codes() == ["no_fields_to_update", "conflict_constraint"]


def test_table_codes_are_used_in_app():
    sources = _app_sources()
    missing = [c for c in _codes() if f'"{c}"' not in sources]
    assert not missing, "表のコードがサーバーで使われていない: " + ", ".join(missing)


def test_not_found_table_rows_are_read():
    targets = _targets()
    assert len(targets) == 67
    assert len(set(targets)) == 67


def test_not_found_targets_match_app():
    used = set(_APP_TARGET.findall(_app_sources()))
    table = set(_targets())
    assert not used - table, "サーバーの not_found の対象が画面の表に無い: " + ", ".join(sorted(used - table))
    assert not table - used, "画面の表の対象がサーバーで使われていない: " + ", ".join(sorted(table - used))
```

### 3-8 `frontend/src/lib/api.httpError.test.ts`（足す）

ファイルの最後に次を足す（既存の試験・`catchApiError`・`stubDetail` は変えずに使う）:

```ts
describe("not_found:<target> texts (ADR-1071 bin3)", () => {
  afterEach(async () => {
    await i18n.changeLanguage("ja");
  });

  const expected = {
    ja: ja.apiError.notFound.replace("{{target}}", ja.apiError.notFoundTarget.lead),
    en: "The lead could not be found. Reload the page and try again.",
  };

  for (const lang of ["ja", "en"] as const) {
    it(`request: not_found:lead becomes the ${lang} text and keeps 404`, async () => {
      await i18n.changeLanguage(lang);
      stubDetail(404, "not_found:lead");
      const err = await catchApiError(() => api.get("/dummy"));
      expect(err.status).toBe(404);
      expect(err.message).toBe(expected[lang]);
      expect(err.responseDetail).toBe("not_found:lead");
    });
    it(`requestForm: not_found:lead becomes the ${lang} text and keeps 404`, async () => {
      await i18n.changeLanguage(lang);
      stubDetail(404, "not_found:lead");
      const err = await catchApiError(() => api.postForm("/dummy", new FormData()));
      expect(err.status).toBe(404);
      expect(err.message).toBe(expected[lang]);
      expect(err.responseDetail).toBe("not_found:lead");
    });
  }

  it("uses the text without a name for an unknown target", async () => {
    stubDetail(404, "not_found:zzz");
    const err = await catchApiError(() => api.get("/dummy"));
    expect(err.message).toBe(ja.apiError.notFoundUnknown);
    expect(err.responseDetail).toBe("not_found:zzz");
  });

  it("passes the old not-found codes through unchanged", async () => {
    for (const code of ["not_found", "company_not_found"]) {
      stubDetail(404, code);
      const err = await catchApiError(() => api.get("/dummy"));
      expect(err.message).toBe(code);
    }
  });
});
```

GET の 404 は送り直しの対象ではない（`RETRYABLE_STATUS` は 5xx）。試験が待つときは、止まらずに原因を報告に書く。

### 3-9 `frontend/tests-e2e/order-commission.spec.ts`・`frontend/tests-e2e/order-financial.spec.ts`・`frontend/tests-e2e/order-purchase.spec.ts`・`frontend/tests-e2e/order-shipping.spec.ts` の見本（Edit の replace_all で、4 ファイルそれぞれ）

| 今の文字列 | 新しい文字列 |
|---|---|
| `detail: "売上情報が見つかりません"` | `detail: "not_found:order_financial"` |
| `detail: "発送情報が見つかりません"` | `detail: "not_found:order_shipping"` |
| `detail: "仕入情報が見つかりません"` | `detail: "not_found:order_purchase"` |

期待: order-commission 3・order-financial 1・order-purchase 3・order-shipping 2、計 9 行。e2e は CI で走らない（`.github/workflows/e2e.yml` の `if: false`）。Mac でもクラウドでも流さない。

## 4. 担当の決まり（定型）

1. sleep で待たない。CI の結果は待たずに報告して終える（Opus が見る）。
2. ファイルの編集は Edit／Write のツールで行う。ヒアドキュメントや sed で書き換えない。例外: §3-1 と §3-5 は `/tmp` の台本で、基準値の JSON は §5 手順4 の台本で行う。
3. PR は作らない（Opus が作る）。push までで終える。
4. フックや自動判定に止められたら、言い換えて再試行しない。止まった手順・最後のコマンド・理由の原文を報告に書いて終える。
5. 止まるのは次だけ: 削除・`--force` が要る push・main への push・本番への接続が要る場面・§2 以外のファイルを直さないと進めない場面・このカードで BLOCKED と書いた場面。それ以外の数や行の食い違いは記録して続ける。
6. 秘密の値を画面にもファイルにも出さない。
7. Bash に psql の語を書かない。commit 文は `-m` で渡す。git は 1 命令ずつ流す。
8. 1 つの発言は 600 文字以内。長い報告は番号付きの発言に分ける。

## 5. 手順（1手順1コマンド。`<repo>` は担当の作業場所の絶対パス）

1. 作業場所を公式の台本で作る。`<main>` はクラウドが最初に置いたリポジトリの場所。次を 1 つずつ流し、出力を報告に書く。Bash ツールの timeout 引数は 600000 にする。
   - (1a) `cd <main> && git fetch origin release/error-text-bin3-not-found-design main`
   - (1b) `cd <main> && git branch --list release/error-text-bin3-not-found-design`。出力が空であること。空でなければ消さずに BLOCKED で終える。`git checkout -B` は使わない。
   - (1c) `cd <main> && bash scripts/new-worktree.sh release/error-text-bin3-not-found-design`。`--claude` は付けない。出力は head・tail などのパイプに通さない。
   - (1d) `ls -1d "$HOME/worktrees/salesanchor/release-error-text-bin3-not-found-design"` と `git -C <main> worktree list`。両方にその場所が出ること。出なければ BLOCKED。以後の `<repo>` はこの場所の絶対パス。
   - (1e) push 済みの枝の先頭に合わせる: `cd <repo> && git switch -C release/error-text-bin3-not-found-design origin/release/error-text-bin3-not-found-design`。続けて `cd <repo> && git rev-parse HEAD` と `cd <repo> && git rev-parse origin/release/error-text-bin3-not-found-design` を流し、2 つが同じことを報告に書く（違えば BLOCKED）。続けて `cd <repo> && git log --oneline -3`。rebase・reset はしない。
   - 台本が作る `.claude-pipeline/active-work.d/` の登録ファイルは git add しない。
2. 環境を作る（便2 と同じ）:
   - (2a) `python3.12 --version; echo rc=$?`。rc=0 なら `python3.12 -m venv /tmp/v312; echo rc=$?`、0 でなければ `uv venv --python 3.12 /tmp/v312; echo rc=$?`（これも 0 でなければ BLOCKED）。
   - (2b) `cd <repo>/backend && /tmp/v312/bin/python -m pip install -q -r requirements.txt -r requirements-dev.txt > /tmp/v312-pip.txt 2>&1; echo rc=$?` と `tail -30 /tmp/v312-pip.txt`（uv で作ったときは `uv pip install --python /tmp/v312/bin/python -q -r requirements.txt -r requirements-dev.txt`）。rc=0 でなければ BLOCKED。
   - (2c) `cd <repo>/frontend && npm ci > /tmp/npm-ci.txt 2>&1; echo rc=$?` と `tail -20 /tmp/npm-ci.txt`。rc=0 でなければ BLOCKED。
3. サーバーの置き換え: `/tmp/replace_bin3.py` を §3-1 のとおり Write で作り、`cd <repo> && /tmp/v312/bin/python /tmp/replace_bin3.py <repo> 2>&1 | tail -40`。続けて `cd <repo> && git diff --stat backend/app | tail -5`（期待: 65 files changed, 198 insertions(+), 198 deletions(-)）と `cd <repo> && git diff -- backend/app | grep -cE '^\+.*"not_found:[a-z0-9_]+"'`（期待: 198）。
4. 基準値を台本で書き出す: `cd <repo>/backend && /tmp/v312/bin/python tests/test_error_detail_guard.py --write-baseline` と `cd <repo> && git diff --stat backend/tests/error_detail_baseline.json | tail -3`。期待: `書き出し: ` の後の件数が 449（93 ファイル）。違っても止まらず、数を報告に書く。
5. §3-2〜§3-4・§3-6〜§3-9 を Edit／Write で作る。§3-5 は `/tmp/add_locale_bin3.py` を Write で作り、`cd <repo> && /tmp/v312/bin/python /tmp/add_locale_bin3.py <repo> 2>&1 | tail -10`。
6. 確かめ（それぞれ `| tail -N` で切る）:
   - (6a) `cd <repo>/frontend && node -e "for (const f of ['src/locales/ja.json','src/locales/en.json']) { const d=require('./'+f); const a=d.apiError; console.log(f, Object.keys(d).length, a.notFound, '|', a.notFoundUnknown, '|', Object.keys(a.notFoundTarget).length, a.notFoundTarget.lead, a.notFoundTarget.discord_routing); }"`
   - (6b) `cd <repo>/backend && /tmp/v312/bin/python -m pytest -q --no-cov -p no:cacheprovider -n 0 -rA tests/test_error_detail_guard.py tests/test_api_error_reason_sync.py 2>&1 | tail -30`。timeout 引数は 600000。合格: 7 つ passed・赤 0。
   - (6c) `cd <repo>/backend && /tmp/v312/bin/python -m pytest -q --no-cov -p no:cacheprovider -n 0 tests/test_staff_me.py tests/test_tenant_user_ref_guard_pg.py 2>&1 | tail -30`。DB が無くて skip や error になるときは、その出力をそのまま報告に書いて続ける（CI で見る）。
   - (6d) `cd <repo>/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/lib/api.httpError.test.ts src/lib/apiErrorReason.test.ts 2>&1 | tail -40`。合格: 赤 0。
   - (6e) `cd <repo>/frontend && npx tsc --noEmit -p tsconfig.json 2>&1 | tail -20; echo rc=$?`（tsconfig の名前が違えば `ls tsconfig*` を流し、app 用のものを使う）。
   - (6f) `cd <repo>/frontend && npx eslint src/lib/api.ts src/lib/apiErrorReason.ts src/lib/apiErrorReason.test.ts src/lib/api.httpError.test.ts 2>&1 | tail -20; echo rc=$?`
   - (6g) `cd <repo>/frontend && npm run check:i18n-missing-keys 2>&1 | tail -10` と `cd <repo>/frontend && npm run check:error-text-next-action 2>&1 | tail -10`。合格: どちらも赤 0。W2 の基準値は変えない。check:i18n-missing-keys が閲覧ページの辞書（`locales/viewer/`）に `apiError.notFound` などが無いと言ったら、辞書を足さずに BLOCKED（Opus が設計を直す）。
   - (6h) `cd <repo>/backend && /tmp/v312/bin/python -m ruff check app tests/test_api_error_reason_sync.py tests/test_staff_me.py 2>&1 | tail -20` と `cd <repo>/backend && /tmp/v312/bin/python -m ruff format --check tests/test_api_error_reason_sync.py 2>&1 | tail -5`。format が赤なら `ruff format tests/test_api_error_reason_sync.py` で直し、直したことを報告に書く。`app` には ruff format をかけない（CI は `ruff check app/` だけ）。
7. 予備（置き換え以外の差が無いことの確かめ）:
   - (7a) `cd <repo> && git diff origin/main -- backend/app | grep -E '^[-+][^-+]' | grep -vE '"not_found:[a-z0-9_]+"|見つかりません' | tail -10`（合格: 出力が空）。
   - (7b) `cd <repo> && git diff origin/main -- frontend/tests-e2e | grep -E '^[-+][^-+]' | grep -vE 'not_found:order_(financial|shipping|purchase)|(売上|発送|仕入)情報が見つかりません' | tail -10`（合格: 出力が空）。
   - (7c) `cd <repo> && git diff origin/main --stat -- frontend/src/locales | tail -3`（期待: 2 files changed, 144 insertions(+), 2 deletions(-)）。
8. `cd <repo> && git add backend/app backend/tests/error_detail_baseline.json backend/tests/test_staff_me.py backend/tests/test_api_error_reason_sync.py frontend/src/lib/apiErrorReason.ts frontend/src/lib/apiErrorReason.test.ts frontend/src/lib/api.ts frontend/src/lib/api.httpError.test.ts frontend/src/locales/ja.json frontend/src/locales/en.json frontend/tests-e2e/order-commission.spec.ts frontend/tests-e2e/order-financial.spec.ts frontend/tests-e2e/order-purchase.spec.ts frontend/tests-e2e/order-shipping.spec.ts`
9. `cd <repo> && git diff --cached --stat | tail -90` を報告に書く。合格: 変えたファイルが §2 のものだけ（backend/app は手順3 の台本が直した 65 ファイルだけ）。
10. commit: `cd <repo> && PATH=/tmp/v312/bin:$PATH git commit -m "feat(errors): not_found:<target> reason codes with named messages (ADR-1071 bin3)" -m "Co-Authored-By: Claude Sonnet <noreply@anthropic.com>"`。timeout 引数は 600000。続けて `cd <repo> && git log --oneline -3` と `cd <repo> && git diff origin/main...HEAD --name-only | tail -90` を報告に書く。合格: 設計の文書（`docs/handoff/error-message-plain-language/` の下）と §2 のものだけ。
11. push: `cd <repo> && PATH=/tmp/v312/bin:$PATH git push -u origin HEAD`。timeout 引数は 600000。出力の全文を報告に書く。続けて `cd <repo> && git ls-remote origin release/error-text-bin3-not-found-design` と `cd <repo> && git rev-parse HEAD` を報告に書き、一致を確かめる。

## 6. PR

担当は作らない。Opus が push を確かめてから、`### 標準ワークフロー確認` と `### GO記録` を入れて作る。

## 7. 報告（完了報告の本文に、次をこの順で全部含める）

1. 冒頭の1行: 本報告はカード 便3（card-bin3、「見つかりません」の理由コード化）の実行結果である。続けて、受領確認: カード末尾の合図 END OF CARD（END-OF-CARD-ERRMSG-BIN3）まで読んだ。
2. 手順1〜11 の各コマンドの生出力（省略しない。`tail` で切った範囲はそのまま）。
3. 置き換えの数（手順3）・基準値の件数（手順4）・文言の数（手順5）。
4. §3 と違う作り方をした所の一覧（無ければ「無し」）。
5. 止まった場合は「止まった手順の番号／最後に実行したコマンド／止まった理由の原文」。
6. 最後の行は `DONE`、`BLOCKED: 理由`、`NEEDS_DECISION: 問い`（理由・問いは文で書く） のどれか1つ。

END OF CARD（END-OF-CARD-ERRMSG-BIN3）
