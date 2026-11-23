# 実装カード 便1: 画面操作の見張り（chrome-op-guard）部屋 P だけ

- 発行: Claude Opus（設計担当）2026-11-23
- 設計: docs/handoff/browser-operation-delegation/design.md §4〜§8（正本）。このカードと設計が食い違えば作業を止めて BLOCKED: で返す。
- ADR: docs/adr/ADR-1085-browser-operation-delegation.md（Draft のまま。触らない）
- PO 承認: 2026-11-23「1,このセッションでは素人にも分かるように…PRマージ、デプロイまで完走させてくれ。」（実装承認）
- 枝: release/chrome-op-guard（origin/main 起点）。

## 0. 作る物（これ以外のファイルを触らない）

| # | ファイル | 新規/変更 |
|---|---|---|
| 1 | docs/handoff/browser-operation-delegation/hooks/chrome_op_guard.py | 新規（PreToolUse） |
| 2 | docs/handoff/browser-operation-delegation/hooks/chrome_op_record.py | 新規（PostToolUse） |
| 3 | docs/handoff/browser-operation-delegation/hooks/tiers.json | 新規（区分の正本） |
| 4 | docs/handoff/browser-operation-delegation/hooks/chrome_common.py | 新規（1と2が共有する: tiers 読み・URL 整形・タブ状態の読み書き・ロック） |
| 5 | docs/handoff/browser-operation-delegation/chrome-consent-line.py | 新規（同意票の1行を作る台本） |
| 6 | docs/handoff/browser-operation-delegation/po_chrome_settings.py | 新規（settings.json に登録2件を足す/外す/確かめる） |
| 7 | docs/handoff/browser-operation-delegation/po-apply-chrome-guard.sh | 新規 |
| 8 | docs/handoff/browser-operation-delegation/po-rollback-chrome-guard.sh | 新規 |
| 9 | scripts/dev/chrome-guard-tests.py | 新規（T1〜T15・T17〜T19） |
| 10 | scripts/dev/consent-audit.py | 変更（「画面操作」の節だけ足す） |
| 11 | .github/workflows/agent-hooks-test.yml | 変更（paths に1行・job を1つ足す） |
| 12 | docs/handoff/browser-operation-delegation/README-hooks.md | 新規（置き場・取り付け・戻し方の説明。短く） |

触らない: docs/handoff/conversation-consent/hooks/consent_check.py（読み込んで使うだけ）・ADR・design.md・~/.claude の本物・settings.json の本物。

## 1. 取り付け後の置き場（本物）

- ~/.claude/scripts/chrome-op-guard/{chrome_op_guard.py, chrome_op_record.py, chrome_common.py, tiers.json}
- 同意の判定は既に取り付け済みの ~/.claude/scripts/consent_check.py を使う。見張りは `os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "consent_check.py")` を importlib で読む（この1か所だけ。環境変数で場所を変えられる作りにしない）。読めなければ止める（exit 2）。
- 試験はこの並びを一時ディレクトリに作る（`<tmp>/scripts/consent_check.py` と `<tmp>/scripts/chrome-op-guard/...`）。

## 2. tiers.json（形と最初の値）

```json
{
  "version": 1,
  "tools": {
    "tier1": ["read_page","get_page_text","find","tabs_context_mcp","tabs_create_mcp","tabs_close_mcp","read_console_messages","read_network_requests","resize_window","list_connected_browsers","select_browser","switch_browser"],
    "tier2": ["javascript_tool","file_upload","upload_image","gif_creator","form_input"],
    "special": ["navigate","computer","browser_batch"]
  },
  "computer_actions": {
    "tier1": ["screenshot","scroll","scroll_to","zoom","wait","hover"],
    "tier2": ["left_click","right_click","double_click","triple_click","type","key","left_click_drag"]
  },
  "page_affecting": ["navigate","computer:left_click","computer:right_click","computer:double_click","computer:triple_click","computer:type","computer:key","computer:left_click_drag","form_input","javascript_tool","file_upload","upload_image","browser_batch"],
  "local_exception": [{"scheme":"http","host":"localhost","port":5173},{"scheme":"http","host":"127.0.0.1","port":5173},{"scheme":"http","host":"[::1]","port":5173}],
  "tier3_urls": [ ... 下の表 ... ],
  "secret_patterns": ["sk-ant-[A-Za-z0-9_-]{10,}","sk-[A-Za-z0-9]{20,}","ghp_[A-Za-z0-9]{30,}","github_pat_[A-Za-z0-9_]{20,}","gho_[A-Za-z0-9]{30,}","AKIA[0-9A-Z]{16}","xox[abpr]-[A-Za-z0-9-]{10,}","AIza[0-9A-Za-z_-]{35}","-----BEGIN [A-Z ]*PRIVATE KEY-----"]
}
```

computer の action の全部の名は、道具の定義の enum（2026-11-23 Opus が道具の定義で確かめた 13 個: left_click, right_click, type, screenshot, wait, scroll, key, left_click_drag, double_click, triple_click, zoom, scroll_to, hover）と同じ。表に無い action は止める。

tier3_urls の各項目は `{"host": "<小文字の完全一致>", "path_regex": "<^ から始まる正規表現>", "why": "<日本語の短い理由>"}`。host が "*." で始まれば、その後ろと一致するか「.後ろ」で終わるホストに当てる。path_regex が "^/" なら全部のパス。最初の一覧:

| host | path_regex | why |
|---|---|---|
| pay.google.com | ^/ | 支払い |
| payments.google.com | ^/ | 支払い |
| admin.google.com | ^/(u/\d+/)?ac/(billing\|subscriptions\|payment) | Workspace の請求・プラン |
| myaccount.google.com | ^/(u/\d+/)?(signinoptions\|apppasswords\|delete-services-or-account\|security-checkup/.*password) | パスワード・2段階認証・削除 |
| dash.cloudflare.com | ^/[^/]+/(billing\|subscriptions)\|^/profile/(api-tokens\|billing\|authentication) | 請求・鍵・2段階認証 |
| github.com | ^/settings/(billing\|tokens\|personal-access-tokens\|security\|admin\|keys\|apps/authorizations)\|^/organizations/[^/]+/settings/(billing\|security) | 請求・鍵・2段階認証・削除 |
| console.anthropic.com | ^/settings/(billing\|keys\|plans) | 請求・鍵 |
| platform.claude.com | ^/settings/(billing\|keys\|plans) | 請求・鍵 |
| claude.ai | ^/settings/billing | 請求 |
| business.facebook.com | ^/billing_hub\|^/settings/(payment\|security) | 広告の支払い・2段階認証 |
| *.facebook.com | ^/(settings/payments\|security/2fac\|deactivate\|delete) | 支払い・2段階認証・削除 |
| *.paypal.com | ^/ | 支払い |
| dashboard.stripe.com | ^/ | 支払いの会社 |
| pay.ebay.com | ^/ | 購入 |
| *.ebay.com | ^/(chkout\|checkout\|mye/myebay/payment) | 購入・支払い |
| jp.mercari.com | ^/(purchase\|transaction/.+/pay\|mypage/(payment\|card\|bank)) | 購入・支払い・口座 |
| *.amazon.co.jp | ^/(gp/buy\|checkout\|gp/checkoutportal\|cpe/yourpayments\|ap/cnep) | 購入・支払い・パスワード |
| *.amazon.com | ^/(gp/buy\|checkout\|cpe/yourpayments\|ap/cnep) | 購入・支払い・パスワード |
| secure.sakura.ad.jp | ^/ | サーバーの契約 |
| console.cloud.google.com | ^/billing | 請求 |

（表の `\|` は正規表現の「または」。json には `|` で書く。）

## 3. chrome_op_guard.py（PreToolUse）

入力: 標準入力の hook の JSON（`tool_name`・`tool_input`・`session_id`・`transcript_path`・`agent_id`（あれば））。出力: 通すとき exit 0、止めるとき標準エラーに日本語の理由1行と exit 2。

1. 例外・JSON が読めない・tiers.json が読めない/形が違う → exit 2（T10）。
2. `tool_name` が `mcp__claude-in-chrome__` で始まらない → exit 0（関係ない）。頭を除いた名を `t` とする。
3. 部屋は常に "P"（便1）。`switch_browser`・`select_browser` は区分1だが記録に `room_changed: true`（T15）。
4. 判定（設計 §5 の表のとおり）:
   - `t` が tools.tier1 → 区分1。
   - `navigate`: url が "back"/"forward" → 区分2（T12）。それ以外は URL を整形（`https://` が無ければ足す・urllib.parse で分け、ホストを小文字・パスは unquote を2回まで）し、tier3_urls に当たれば exit 2（T1）。当たらなければ区分1。
   - `computer`: action が computer_actions.tier1 → 区分1。tier2 → 区分2。どちらにも無い → exit 2（T11）。
   - tools.tier2 → 区分2（T8・T9）。
   - `browser_batch`: actions の各項目を同じ判定に通す。区分3/止めるが1つでもあれば全体を exit 2（T7）。区分2が1つでもあれば全体を exit 2（設計 §5「1操作ずつ出し直す」。例外の手元のタブの押す操作も batch の中では区分2扱い・T17）。全部区分1なら通す。
   - 上のどれにも無い → exit 2（T13）。
5. 打つ文字（computer の `text`（type のとき）、form_input の `value`。bool・数は str() にする）にカード番号の形（空白とハイフンを除いた 13〜19 桁の数字の並びで Luhn が合う）か secret_patterns が当たれば、区分に関係なく exit 2（T5・T6）。記録には長さだけ。
6. 部屋 P の例外（設計 §4-2・§5）: `computer` の tier2 action と `form_input` のうち、`tabId` があり、状態ファイルで そのセッション＋tabId の住所が「確かめ済み」かつ local_exception に完全一致（scheme・host・port。port が無ければ http=80 扱いで当たらない）なら区分1に下げる（T17）。`javascript_tool`・ファイル系は下げない。
7. 区分2のとき:
   - `agent_id` キーがあれば止める（T14）。
   - computer/form_input で `action_summary` が無い・空 → 止める（T11）。`action_summary` に改行・`$`・バッククォート → 止める（T11）。
   - 「ページに効く操作の後の確かめ」: そのタブ（tabId 無しの操作ならセッションの全タブ）が「不明」なら止める（T18 最後の項目・設計 §5）。ただし navigate back/forward の行き先確かめもこの決まりに入る。
   - 1行を作る: `chrome <t> <action> <action_summary または url> 文字:<len>:<sha8> 回数:<repeat、無ければ1> 修飾:<modifiers、無ければ無し>`。action は computer なら action、navigate なら url の値（back/forward）、他は "-"。4つ目は computer/form_input なら action_summary、navigate なら url、javascript_tool なら "js"、ファイル系なら ref か "-"。文字は打つ文字（無ければ空文字）の UTF-8 の長さと sha256 の頭8文字（javascript_tool は text をその文字に使う）。この作り方を chrome_common.py の1関数 `consent_line(t, tool_input)` に置き、chrome-consent-line.py も同じ関数を呼ぶ（T19。書き写さない）。
   - `consent_check.check(hook_input, line, now)` が True なら通す。False なら止め、理由に「同意票に次の1行を書いて PO の『1』をもらってください: <line>」を出す（T2・T3）。
8. 通した・止めたに関係なく、`~/.claude/logs/chrome-ops.jsonl` に1行足す: ts・session・agent_id（あれば）・tool・action・url（navigate のときだけ）・room・tier（1/2/3）・decision（pass/block/consent_pass）・reason・text_len。打つ文字・action_summary の中身は書かない（T4・T5）。
9. ページに効く操作（tiers.json page_affecting）を通したら、そのタブを「不明」にする。tabId が無ければセッションの全タブを不明にし、`session_all_unknown` の印を立てる（T17・T18）。

## 4. chrome_op_record.py（PostToolUse）

- `tool_name` が `mcp__claude-in-chrome__tabs_context_mcp` のときだけ住所を覚える。`tool_response` は文字列・内容の塊の並び・`{"content": [...]}` のどれでも受ける。塊（`type == "text"` の text）を1つずつ全体を json.loads する。つなげない。正規表現で探さない。`availableTabs` が並び（list）の塊がちょうど1つのときだけ使う。2つ以上・0 → 何も覚えない。
- その塊の各項目について、`tabId` が int、`url` が str の項目を「確かめ済み・住所=整形した url・時刻」として覚える。同じ tabId が2つ以上あればそのタブは不明。
- `session_all_unknown` の印は、そのセッションの「不明」のタブが全部確かめ済みになったら外す。
- chrome-ops.jsonl に1行: type "tab_context"・session・`tab_context_parsed`（true/false）・tabs: [{tabId, url（整形済み）}]。返事の生の中身は残さない（T20）。
- 状態ファイル `~/.claude/logs/chrome-tab-state.json`、鍵は "<session_id>:<tabId>"。読み書きは `~/.claude/logs/chrome-tab-state.lock` の mkdir ロック（最大 3 秒待ち、取れなければ PreToolUse は止める・PostToolUse は書かずに終える）と trap 相当の finally で外す。書くときは一時ファイル＋os.replace。
- PostToolUse は何があっても exit 0（記録に失敗しても道具の返事を止めない）。

## 5. chrome-consent-line.py

`python3 chrome-consent-line.py '<tool_input の JSON>' <道具の短い名>` → 1行を標準出力。中身は chrome_common.consent_line と同じ（T19）。

## 6. 試験 scripts/dev/chrome-guard-tests.py

`python3 -I -B scripts/dev/chrome-guard-tests.py <hooksのdir> <consent_check.pyのdir> <一時dir>`。偽の HOME（一時dir）だけを使う。各試験の結果を `PASS T<n> <名>` か `FAIL T<n> <名> <理由>` で1行ずつ出し、最後に `DONE pass=<n> fail=<n>`。fail>0 なら exit 1。設計 §7 の T1〜T15・T17〜T19 の各行の中身を全部入れる（T3・T17・T18 は作り物の会話記録を consent-unit-tests.py の型で作る）。T16・T20 は取り付け時なのでここには入れない。

## 7. 取り付けの台本（po-apply / po-rollback）

- 型は docs/handoff/conversation-consent/po-apply-consent.sh と同じ流れ: バックアップ（settings.json）→ 試作の試験（chrome-guard-tests.py）→ ~/.claude/scripts/chrome-op-guard/ に写す（権限 555）→ po_chrome_settings.py add で settings.json に 2 件足す（PreToolUse matcher `mcp__claude-in-chrome__.*` コマンド `python3 $HOME/.claude/scripts/chrome-op-guard/chrome_op_guard.py`、PostToolUse 同じ matcher で chrome_op_record.py。既存の登録は変えない。既にあれば足さない）→ T16 → 不合格なら自動で戻す（ROLLED BACK を出す）。
- T16: 本物の置き場の見張りに、区分3の URL（`https://dash.cloudflare.com/abc/billing`）の navigate の入力を流して exit 2、`https://example.com/` で exit 0、押す操作の同意なしで exit 2 を確かめる。偽の transcript を使い、本物の consent-used.jsonl を書かない（HOME を一時dirにして見張りを直接呼ぶ）。
- 既に取り付け済み（置き場と登録がある）なら「反映済み」と出して何もしない。`--update` で中身の違うファイルだけ入れ替える（試験不合格なら戻す）。
- rollback: 登録2件を外し、置き場を消し、settings.json が登録以外変わっていないことを確かめる。
- どちらも VOICEVOX_MUTED の確認と、許可券（danger-permit-*.json）が残っていたら中止、は consent の台本と同じ。

## 8. consent-audit.py「画面操作」の節

run_audit の最後（ABNORMAL の前）に、過去7日の chrome-ops.jsonl から:
- G2: tier3 の URL の型に当たる url が記録にあった件数（navigate の url と tab_context の tabs の url の両方）。0 が正常。
- G3: decision=consent_pass の件数と、同じ時刻±5秒の consent_consumed の件数の差。0 が正常。
- G4: 会話記録（projects/*/*.jsonl と pl_load_windows と同じ subagents の下）の `mcp__claude-in-chrome__` の tool_use の数と、chrome-ops.jsonl の pass/block/consent_pass の数の差。0 が正常。
- 取りこぼし: ページに効く操作のうち、その後にそのタブの tab_context が無いもの（各セッションの最後の1件は除く）。参考の数。
を `5. 画面操作: G2=%d G3=%d G4=%d 取りこぼし=%d` の形で出し、G2〜G4 が1以上なら abnormal に入れる。chrome-ops.jsonl が無いときは「記録なし（見張りの取り付け前）」と出して abnormal にしない。consent-unit-tests.py の既存の試験が通り続けること。

## 9. CI

agent-hooks-test.yml の paths に `'docs/handoff/browser-operation-delegation/**'` と `'scripts/dev/chrome-guard-tests.py'` を足す。job `chrome-guard-tests` を consent-unit-tests と同じ形で足し、`python3 -I -B scripts/dev/chrome-guard-tests.py docs/handoff/browser-operation-delegation/hooks docs/handoff/conversation-consent/hooks "$RUNNER_TEMP/chrome"` の出力に FAIL が無く DONE があることで判定する。

## 10. 終わりの条件と返し方

- 手元（クラウド）で `python3 -I -B scripts/dev/chrome-guard-tests.py ...` が fail=0、`python3 -I -B scripts/dev/consent-unit-tests.py docs/handoff/conversation-consent/hooks <tmp> <repo>` が FAIL 無し。生の出力の最後の 30 行を返事に貼る。
- commit は Write でメッセージのファイルを作って `git commit -F`。push は `git push -u origin release/chrome-op-guard` を単独で。PR は作らない（Opus が作る）。
- 返事の最後の行は `DONE` か `BLOCKED: <理由>` か `NEEDS_DECISION: <問い>`。設計と食い違う・分からないことは推測で埋めずに止める。
