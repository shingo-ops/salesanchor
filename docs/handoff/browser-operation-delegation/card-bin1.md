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

## 11. 差し戻しの直し（2026-11-23 審査役 REQUEST_CHANGES on f351f228f の5点＋1点。§3〜§7 より優先）

触るファイル: §0 の 1・4・7・9 だけ（chrome_op_guard.py・chrome_common.py・po-apply-chrome-guard.sh・chrome-guard-tests.py）。tiers.json・設計・ADR は触らない。

1. **batch の項目の読み方（§3-4 の置き換え）**: 道具の定義（Opus が 2026-11-23 に読んだ。各項目は `{name, input}`、両方 required）どおり、各項目は「鍵がちょうど `name` と `input` の2つ」「name は str」「input は dict」のときだけ読む。ほかの鍵（`tool`・`tool_name`・`tool_input`・`params`・`arguments`・`action` など）が1つでもある、またはどちらかが欠けた項目があれば batch 全体を止める（reason `bad_batch`）。name の頭に `mcp__claude-in-chrome__` が付いていれば外す。`"action" があれば computer とみなす` の決まりは消す。
2. **印を書けないとき止める（§3-9 の置き換え）**: ページに効く操作を通す直前に「不明」の印を書けなかった（ロック待ち3秒を超えた・状態ファイルが読めない・書けない）ときは exit 2（reason `state_write_failed`、文「chrome-op-guard: 操作の後の覚えを残せないため止めました。~/.claude/logs/chrome-tab-state.json を確かめてください」）。同意票はその時点で使用済みになるが、それでよい（止める側に倒す）。
3. **区分3の URL の整形を強くする（§3-4 navigate の整形の置き換え）**。parse_url で次をこの順に行う:
   - (a) ホスト名: urlsplit の hostname に unquote を2回 → `unicodedata.normalize("NFKC", …)` → `。`(U+3002)・`．`(U+FF0E)・`｡`(U+FF61) を `.` に → 小文字 → 末尾の `.` を外す → ASCII 以外が残れば各ラベルを `encodings.idna`（`"idna"` の codec）で ASCII にする。失敗したら None（止める）。IPv6（`[`…`]`）以外で、結果に `a-z 0-9 . -` 以外の文字があれば None（止める）。
   - (b) パス: unquote を2回 → `\` は既に `/` → 連続する `/` を1つにまとめる → RFC 3986 5.2.4 の remove_dot_segments で `.` と `..` をたたむ（根より上には出ない）。
   - (c) tier3_match のパスの正規表現は大文字小文字を区別しない（`re.IGNORECASE`）。
   - text は整形後の scheme・host・port・path で作る（今と同じ形）。local_exception の判定はこの整形後の値で今と同じ。
4. **手元の例外の `key` を狭める（§3-6 に足す）**: 手元の例外で区分1に下げるのは、`key` のときは `text` を空白で分けた各語に `+` が無く、`cmd`・`ctrl`・`control`・`meta`・`super`・`alt`・`option`・`command`・`win` のどれでもなく（大小区別なし）、`modifiers` が無いか空のときだけ。それ以外の `key` は区分2のまま（同意が要る）。アドレス欄へ移る道（cmd+l など）を塞ぐため。
5. **取り付けの台本（§7）**: po-apply-chrome-guard.sh:166-169 の「許可券が現れた」場合、戻しの台本の終了コードを見て、0 以外なら `ROLLBACK FAILED: 許可券があるため戻せません。許可券が消えてから bash <戻しの台本> <バックアップ> を実行してください` を出して exit 3。0 なら今どおり exit 1。
6. **試験（§6 に足す。既存の試験は残す）**:
   - T7・T17 の batch の試験を全部 `{"name": …, "input": …}` の形に直す。
   - T7 に足す: `name` と `tool` の両方を持つ項目（審査役の例 `{"name":"computer","tool":"read_page","input":{"action":"left_click",…}}`）が止まる／`input` が無い項目が止まる／本物の形の `{"name":"computer","input":{"action":"left_click",…,"action_summary":"x","tabId":1}}` が `batch_has_tier2` で止まる／`{"name":"mcp__claude-in-chrome__read_page","input":{}}` と `{"name":"computer","input":{"action":"screenshot"}}` の batch は通る。
   - T1 に足す（すべて止まる）: `https://github.com/a/../settings/tokens`・`https://dash.cloudflare.com/profile/x/%2e%2e/api-tokens`・`https://pay%2Egoogle.com/`・`https://ｐａｙ.google.com/`・`https://pay。google.com/`・`https://github.com/Settings/tokens`・`https://github.com//settings/tokens`。通る: `https://example.com/a/../b`・`https://github.com/shingo-ops/salesanchor`。
   - T17 に足す: 手元の確かめ済みのタブで `key` `text:"Enter"` は通る（区分1）／`text:"cmd+l"`・`text:"ctrl+l"`・`text:"Meta"`・`modifiers:"cmd"` 付きの `key` は同意なしで止まる。
   - 新しい T21: 状態ファイルのロック（`<偽HOME>/.claude/logs/chrome-tab-state.lock` の dir を今の時刻で作っておく）がある間、区分1の navigate（`https://example.com/`）が reason `state_write_failed` で止まる。ロックを外すと通る。
7. 終わりの条件は §10 と同じ（chrome-guard-tests fail=0・consent-unit-tests FAIL 無し・生の出力の最後の30行）。commit は1つ、push は `git push origin release/chrome-op-guard` を単独で。

## 12. 2回目の差し戻しの直し（2026-11-23 審査役 REQUEST_CHANGES on 4979210d4 の3点。§3〜§11 より優先）

触るファイル: chrome_common.py・chrome_op_guard.py・tiers.json・po-apply-chrome-guard.sh・po-rollback-chrome-guard.sh・chrome-guard-tests.py の6つだけ。設計・ADR・ほかのファイルは触らない。

1. **`scheme:` の後ろの斜線の数で住所を取り違えない（§11-3 に足す）**。【事実】`https:/pay.google.com/` を今の parse_url に渡すと host が `https`、path が `/pay.google.com/` になり、区分3を素通りする（Opus が 4979210d4 の chrome_common.py で再現）。WHATWG URL の決まりでは http・https は「scheme:」の後ろの `/` と `\` の数によらず `scheme://` として読む。直し方: parse_url で、制御文字を外し `\` を `/` にした後・`_SCHEME_RE` の判定の前に、`^(https?):/*`（大小区別なし）に当たれば、その部分を `<小文字の scheme>://` に置き換える。http・https 以外の scheme の扱いは今のまま変えない（`localhost:5173/` のような「ホスト:ポート」を scheme と読まないため、置き換えは http・https に限る）。
2. **手元の例外の `key` は許す一覧だけにする（§11-4 の置き換え）**。【事実】F6・F5・BrowserBack・`ctrl-l`・Meta_L が §11-4 の決まりでは区分1に下がる（審査役が実測）。F6 は Chrome でアドレス欄に移るキー。直し方: tiers.json に `"local_plain_keys"` の並びを足し、値は `["Enter","Return","KP_Enter","Tab","Escape","Esc","Delete","Up","Down","Left","Right","ArrowUp","ArrowDown","ArrowLeft","ArrowRight","Home","End","Page_Up","Page_Down","PageUp","PageDown","space"]`。手元の例外で区分1に下げてよい `key` は、`text` を空白で分けた各語が（大小区別なしで）この並びのどれかと一致し、`modifiers` が無いか空のときだけ。それ以外はすべて区分2のまま。並びは見張りの中に書き写さず tiers.json から読む（区分の正本は tiers.json の1か所）。`_KEY_MODS` は消す。tiers.json を読む側に鍵の決まった一覧の点検があって新しい鍵で落ちるなら、推測で直さず NEEDS_DECISION: で止める。
3. **台本の変数のすぐ後ろに全角の字を置かない（§7・§11-5 に足す）**。【事実】macOS の bash 3.2 は UTF-8 の設定で `$rc（` の「（」の頭のバイトを変数名の一部として読み、`unbound variable` で台本ごと落ちる（審査役が実測。T16 不合格のとき戻さずに終わる）。直す行: po-apply-chrome-guard.sh の 88・90・92 行の `$rc` を `${rc}`、135 行の `$f` を `${f}`、po-rollback-chrome-guard.sh の 82 行の `$f` を `${f}`。ほかにも「`$` ＋名前のすぐ後ろが ASCII 以外の字」の所があれば同じく `${…}` にする。
4. **試験（§6 に足す。既存の試験は残す）**:
   - T1 に足す（すべて止まる）: `https:/pay.google.com/`・`http:/pay.google.com/`・`https:/github.com/settings/tokens`・`HTTPS:/pay.google.com/`・`https:pay.google.com`・`https:///pay.google.com/`。通る: `localhost:5173/`（今どおり手元の住所として読める）・`https:/example.com/`。
   - T17 に足す: 手元の確かめ済みのタブで `key` の `text` が `Tab`・`Escape`・`Down Down Enter` は通る（区分1）。`F6`・`F5`・`BrowserBack`・`ctrl-l`・`Meta_L` は同意なしで止まる（reason `no_consent`）。§11-6 の Enter・cmd+l・ctrl+l・Meta・modifiers=cmd の試験は残す。
   - 新しい T22（二度と同じ形を入れない見張り）: po-apply-chrome-guard.sh と po-rollback-chrome-guard.sh の全行を読み、正規表現 `\$[A-Za-z_][A-Za-z0-9_]*[^\x00-\x7f]` に当たる行が0件であること。台本の場所は chrome-guard-tests.py の引数の hooks の dir の1つ上の dir から求める。
5. **直さないもの（審査役の「低い・参考」。理由つきで残す）**: `back ` などの空白・大文字つきの navigate（区分1の移動として通る。行き先は履歴の範囲で、同意なしに外へ何かを送る道ではない）。`www.github.com/settings/tokens` のような転送で区分3に着く道（設計 §5 が残る弱さとして受け入れ済み）。状態ファイルが `[]` の形のときに記録の行が残らない件（止める側に倒れており、通す道ではない）。
6. 終わりの条件は §10 と同じ。chrome-guard-tests は fail=0、consent-unit-tests は FAIL 無し、§12-4 の足した試験が全部 PASS 行に出ること。commit は1つ、push は `git push origin release/chrome-op-guard` を単独で。

## 13. 3回目の審査の中の指摘の直し（2026-11-23 審査役 APPROVE on 225dbb134 の指摘1。§3〜§12 より優先）

触るファイル: hooks/chrome_op_guard.py・hooks/tiers.json・scripts/dev/chrome-guard-tests.py の3つだけ。設計・ADR・ほかのファイルは触らない。

1. **ブラウザを切り替えたら、そのセッションの全タブの住所を「不明」にする**。【事実】手元の住所 `http://localhost:5173/` で確かめ済みのタブ 7 → `switch_browser {}` → `computer left_click tabId:7`（同意票なし）が exit 0 で通る（審査役の探り `SWITCH then click tab7 rc_click=0`、select_browser も同じ）。tabId はブラウザごとの番号なので、切り替え先の同じ番号のタブが外のサイトでも同意なしで押せる。設計 §7 の T15「switch_browser の後も部屋 P の扱いのまま（押す操作が同意票なしで止まる）」の趣旨に反する。直し方:
   - tiers.json の `page_affecting` の並びの最後に `"switch_browser"` と `"select_browser"` を足す。
   - chrome_op_guard.py の `_decide` の `if t in ("switch_browser", "select_browser"):` の所（今は `rec["room_changed"] = True` だけ）に `tab_id = None` を足す。入力に tabId があっても、セッションの全タブを不明にするため（`mark_unknown(sid, None)` の道を通す）。
   - 印を書けないときは、今の `state_write_failed` の道のとおり止める（区分1の道具でも止まる。止める側に倒す）。
2. **試験（T15 に足す。既存の T15 は残す）**:
   - 手元の確かめ済みのタブ 7（`ctx_reply(h, [tab(7, LOCAL)])`）→ `switch_browser {}` → `computer` の `click(7)`（同意票なし）が exit 2 で、記録の reason が `tab_unverified`。
   - 同じことを `select_browser {"deviceId": "d"}` でも確かめる。
   - `switch_browser {"tabId": 7}` のように tabId が付いていても、別のタブ 8（切り替え前に確かめ済みの手元の住所）への `click(8)` が exit 2・reason `tab_unverified`。
   - 切り替えの後に `ctx_reply(h, [tab(7, LOCAL)])` で確かめ直すと、手元のタブ 7 の `key` `Enter` が通る（reason `local_exception`）。
3. 終わりの条件は §10 と同じ。chrome-guard-tests は fail=0、consent-unit-tests は FAIL 無し、§13-2 の足した試験が全部 PASS 行に出ること。commit は1つ、push は `git push origin release/chrome-op-guard` を単独で。
4. **直さないもの（審査役の「低い・参考」。理由つきで残す）**: 戻しの後に settings.json に空の `"PostToolUse": []` が残る件（動きに影響なし）。T16-c が同意の判定より手前の tab_unverified で止まる件（止める側に倒れる）。`chrome://` への移動（区分3の一覧は PO 承認済みの範囲の外。便2で検討）。点区切りのカード番号（設計どおり）。`_CTRL_RE =re.compile` の空白（見た目だけ）。

## 14. 4回目の審査の差し戻しの直し（2026-11-23 審査役 REQUEST_CHANGES on 332655f10 の中1件。§3〜§13 より優先）

触るファイル: hooks/chrome_op_guard.py・scripts/dev/chrome-guard-tests.py の2つだけ。設計・ADR・tiers.json・ほかのファイルは触らない。

1. **browser_batch の後は、いつもセッションの全タブを「不明」にする**。【事実】`browser_batch {"actions":[{"name":"select_browser",...}], "tabId":99}` や `{"actions":[{"name":"navigate","input":{"url":"https://example.com/","tabId":7}}], "tabId":99}` の後に、確かめ済みの手元のタブ 7 を同意票なしで `click(7)` すると exit 0・reason `local_exception` で通る（審査役の探り P5・P5b、225dbb134 でも同じ）。原因は chrome_op_guard.py:130 の `tab_id = tab_id_of(ti)` が batch 自身の上の段の `tabId`（道具の定義に無い欄）を読み、:238 の `mark_unknown` がそのタブ1つしか不明にしないこと。batch の中身は切り替え・移動・別のタブへの操作を含みうるので、上の段の番号は信じない。直し方: `_decide` の `if t in ("switch_browser", "select_browser"):` の段のすぐ後に、`if t == "browser_batch":` で `tab_id = None` を足す（注釈は「batch の中身は別のタブや切り替えを含みうるので、上の段の tabId は使わずセッションの全タブを不明にする」）。ほかの判定（中身の区分・区分2が混じれば止める等）は変えない。
2. **試験（T15 に足す。既存の試験は残す）**:
   - 確かめ済みの手元のタブ 7 → `browser_batch {"actions":[{"name":"select_browser","input":{"deviceId":"d"}}], "tabId":99}`（exit 0）→ 同意票なしの `click(7)` が exit 2・reason `tab_unverified`。
   - 確かめ済みの手元のタブ 7 → `browser_batch {"actions":[{"name":"navigate","input":{"url":"https://example.com/","tabId":7}}], "tabId":99}`（exit 0）→ 同意票なしの `click(7)` が exit 2・reason `tab_unverified`。
   - batch の中の項目の形は、既存の T の batch の試験と同じ書き方に合わせる（中身の名前の欄が `name` でなければ既存の書き方に従う）。batch そのものが exit 0 にならないときは推測で直さず NEEDS_DECISION: で止める。
3. 終わりの条件は §10 と同じ。chrome-guard-tests は fail=0、consent-unit-tests は FAIL 無し、§14-2 の足した試験が PASS 行に出ること。commit は1つ、push は `git push origin release/chrome-op-guard` を単独で。

## 15. 5回目の審査の中の指摘の直し（2026-11-23 審査役 APPROVE on acf31b4c1 の中1件。§3〜§14 より優先）

触るファイル: hooks/chrome_op_guard.py・hooks/chrome_op_record.py・scripts/dev/chrome-guard-tests.py の3つだけ。設計・ADR・tiers.json・ほかのファイルは触らない。

1. **タブ番号は1以上の整数だけを番号として使う**。【事実】`navigate {"url":"https://example.com/","tabId":0}`（または `-1`）の後、確かめ済みの手元のタブ 7 の `click(7)` が exit 0・reason `local_exception` で通る（審査役の探り probe2 の A の3・4行目）。【未確認】拡張が tabId 0 を「無し」と読んで最初のタブを動かすかは確かめていない。分からないので止める側に倒す。直し方:
   - chrome_op_guard.py の `tab_id_of` で、`isinstance(v, int) and not isinstance(v, bool) and v > 0` のときだけ v を返し、それ以外は None を返す（None のときは今どおりセッションの全タブを不明にする・tabId の無い区分2の決まりに従う）。
   - chrome_op_record.py:61 の availableTabs の項目の条件にも `and it.get("tabId") > 0` を足す（0 以下の番号のタブは確かめ済みにしない）。
2. **試験（T15 に足す。既存の試験は残す）**:
   - 確かめ済みの手元のタブ 7 → `navigate {"url":"https://example.com/","tabId":0}` → 同意票なしの `click(7)` が exit 2・reason `tab_unverified`。
   - 同じことを `tabId: -1` でも確かめる。
   - `ctx_reply(h, [tab(0, LOCAL)])` の後、`click(0)`（同意票なし）が exit 2（確かめ済みにならない）。
3. 終わりの条件は §10 と同じ。chrome-guard-tests は fail=0、consent-unit-tests は FAIL 無し、§15-2 の足した試験が PASS 行に出ること。commit は1つ、push は `git push origin release/chrome-op-guard` を単独で。
4. **直さないもの（審査役の「低い・参考」）**: 返事の届く順番の時間差で確かめ済みが付け直される道（Claude Code が Chrome の道具を順番に流すなら起きない・設計 §5 の残る弱さ）。頭の大小が違う道具名（登録の matcher に当たらず、道具名は Claude Code が付ける）。サブエージェントの手元のタブの押す操作（設計どおり）。
