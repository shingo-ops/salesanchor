<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ。リポジトリ外のパスはバッククォートを付けない -->
# Phase 3 設計 — Opus の権限の自律管理（台帳と週次点検）ADR-1034

**状態**: 設計審査済み 第6版（便1 の Reviewer 指摘で §2-2 R0 と §4-3 record の確かめを直し、Architect 差分審査4回目で APPROVE。LOW 1 反映済み。その後 Reviewer 再審査の指摘で改2〜改6、改6 を Architect 差分審査で APPROVE）。便1 は #4544 でマージ済み。改7（PO の `!` の同意の照らし方）は審査前。
**現在地**: `docs/handoff/permission-delegation/recon.md`
**関連 ADR**: `docs/adr/ADR-1011-permission-self-maintenance.md`（`SM-` の文の週次保守。本件はその「範囲外」の allow の部分を改める）／`docs/adr/ADR-1033-conversation-consent-ticket.md`（週次点検の定期実行と同意の台帳を共有）／`docs/adr/ADR-1003-go-delegation-to-opus.md`

## 1. 目的（PO の言葉）

「日々の業務中にopusが必要と感じたら権限を追加しても良い……定期実行で追加した許可や削除した許可、意図や理由を確認していまの権限が適切かどうかを確認する仕組みを設けて管理しながらPDCAを回して」（recon §4）。

PO に見える変化:
- Opus が仕事の途中で許可の文を足し引きしても、PO に許可を求めない（保留4項目を除く）。
- 毎週月曜の点検で、先週の足し引きが理由つきで記録されているか、足した効果があったかを確かめ、異常があるときだけ PO に知らせる。

## 2. 対象と対象外

### 2-1. Opus が自分で足し引きしてよいもの（「通常」）

次の2か所の「許可の文」だけ。必ず道具 `scripts/dev/perm-change.py apply` を通す（§4-1）。autoMode.allow は自然な文章で範囲を機械で絞れないため、`SM-` 以外の文の add は常に保留（R0）とし、remove だけを通常とする（`SM-` は ADR-1011 の週次保守のまま）。
- ~/.claude/settings.json の permissions.allow
- 本店のリポジトリの .claude/settings.local.json の permissions.allow

外す（remove）は権限を狭める方向なので、保留の目印に当たっても通常として扱う。ただし autoMode.allow の例外の文（ADR-1011 の例外の文と、§4-6 で足す例外の文）は外せない（保留 R4）。

### 2-2. 保留4項目（PO の確認が要る。PO 決定 2026-10-19）

道具が「足す」文を次の順で判定し、1つでも当たれば保留にして反映しない。判定は大文字小文字を区別しない。

| 記号 | 中身 | 目印（足す文に含まれたら保留） |
|---|---|---|
| R0 | 広すぎる許可（R1〜R3 を言い換えで素通りさせない） | 下の「R0 にしない形」のどれにも当てはまらない文すべて（第6版 改3 で、どの道具も受け入れの形だけを通す形に反転）／perm-change を含む文／target が autoMode.allow の add すべて |
| R1 | 本番データの削除 | 語: delete / drop / truncate / prune / 削除 / 消去、句: `rm -r` / `rm -rf` / `volume rm`。先頭の語（パスを外した名前）が rm で `*` を含む文（`-r` の有無を問わない）。および 語: ssh / psql / prod / prod1 / prod2 / 本番、句: `docker compose exec` を含む文のうち、下の「読み取りの印」が無いもの |
| R2 | main への直接の書き込み | 語: push / main / develop / ruleset、句: `reset --hard` / `branch -D` / `gh pr merge` / `Branch Protection`。`--force` と `-f` は同じ文に push があるときだけ当たり |
| R3 | 秘密情報 | 語: secret / secrets / token / tokens / key / keys / password / passwd / credential / credentials、句: `.env` / `gh secret`、日本語: 鍵 / 合言葉 / 秘密 |
| R4 | 見張りを弱める変更 | 語: hook / hooks / guard / gate / bypass / skip / soft_deny / defaultMode / permission / permissions / settings、句: `Self-Modification` / `.claude/scripts` / `agent-tokens`、日本語: 例外 / 見張り / 許可 |

**R0 にしない形**（第6版 改3。次のどれか1つに当てはまる文だけ R0 にしない。当てはまっても R1〜R4 の判定は別に行う）
- 共通の形: 文全体が `道具名(中身)` で、`(` の前に空白が無く、中身は空白以外の文字を1つ以上含む。道具名だけの文（`Bash`・`Edit`・`Read`・`WebSearch`・`mcp__<サーバー>` など）は、下の MCP の場合を除いて R0。
- (a) `Bash(中身)`（第6版 改6。`*` の有無にかかわらず受け入れの一覧だけを通す）: 次の2つをどちらも満たすときだけ R0 にしない。
  1. 中身のどこにも `;`・`&`・`|`・`>`・`<`・`` ` ``・`$`・改行が無い（命令の連結・出力先の指定・変数の差し込みを止める）。
  2. 中身の先頭の語の並びが、下の「Bash の受け入れの一覧」のどれかと先頭から一致する。`*` を含む文は、最初の `*` より前の語の並びが一覧の語と過不足なく一致する（`*` が語の途中にある `grep foo*` は、その語を含めずに前の語の並び `grep` で比べる。`grep *` より狭いので通る）。`*` を含まない文は、一覧の語の後に続く語が `-` で始まらない語（ファイル名やブランチ名などの引数）か、一覧の語だけで終わる。中身に引号（`"`・`'`）や `\` があれば R0。受け入れの一覧と比べる先頭の語は書かれたままの名前で比べ、パスや末尾の数字・`.` は外さない（`/` を含む先頭の語は一覧に当たらず R0）。パスを外して比べるのは R1 の rm の判定だけ。
  - 一覧に無い命令（実行役・包み役・find・awk・docker・git -c・gh api なども含む）は、`*` が無い決まった文でもすべて R0。実行役を並べて止める形をやめ、狭い受け入れに反転した（改5 の差分審査 REVISE で、拒否の一覧は抜けが残り続けると分かったため）。
  - 前提（公式の文書 code.claude.com/docs/en/permissions「Compound commands」、2026-10-19 確認）: Claude Code は `&&`・`||`・`;`・`|`・`|&`・`&`・改行で命令を分け、許可の文は分けた命令ごとに一致する必要がある。`Bash(grep *)` は `grep x ; id` を許さない。1. の記号の条件は許可の文そのものを見る二重の守り。
- (b) `Edit`・`Write`・`MultiEdit`・`NotebookEdit` の `(パス)`: リポジトリから見た相対パスで、`~`・`/` で始まらず、`/` で終わらず、`..`・`.git/`・`*`・`$` を含まず、`.claude`・`.codex`・`.salesanchor-tools`・`agent-console` も含まない。さらに、途中に `/` を1つ以上含み、最初の段が受け入れの一覧（`docs`・`frontend`・`backend`）にあり、どの段も `.` で始まらない（許可の文は名前だけだとどの深さにも当たるおそれがあるため）。`~/.zshrc`・`~/Library/LaunchAgents/x.plist`・`~/.gitconfig`・`.git/config`・`config`・`.zshrc`・`.husky/pre-commit`・`scripts/permit-danger.sh` はすべて R0。
- (c) `Read`・`Grep`・`Glob` の `(中身)`: 中身は問わない（読み取り。ADR の受け入れたリスク）。
- (d) `WebFetch(domain:<名前>)`: 名前に `*` を含まない。
- (e) MCP の道具: `mcp__<サーバー>__<道具>` の名前だけの文で、サーバーが読み取り専用の受け入れ一覧（はじめは `context7` だけ）にある。サーバー名と道具名は英数字・`_`・`-`。一覧に無いサーバー（例: `mcp__github__merge_pull_request`）は R0。
- 受け入れの一覧（(a) の Bash の受け入れの一覧、(b) の最初の段の一覧、(e) のサーバーの一覧）は道具の中の辞書1つに置き、一覧に足す変更は R4。

**Bash の受け入れの一覧と比べ方**（第6版 改6。`:*` は ` *` と同じに扱う）
- パスと末尾の数字・`.` を外した名前（`/bin/rm`→rm）は R1 の rm の判定だけに使い、R1 は R0 より先に行う。受け入れの一覧とは書かれたままの名前で比べる（(a) の 2.）。
- 受け入れの一覧（(a) の 2. で使う）:
  `git status`・`git ls-files`・`git rev-parse`・`gh pr view`・`gh pr list`・`gh pr checks`・`gh pr diff`・`gh run view`・`gh run list`・`grep`・`wc`
- `*` は任意の引数に広がるため、出力先の指定や外部の命令を走らせる引数を持つもの（`git log/diff/show` の `--output`、`rg --pre` など）は一覧に入れない。
- 一覧は道具の中の辞書1つに置く。一覧に足す（R0 を外す範囲を広げる）変更は R4。一覧に無い正当な文は保留になり、PO の確認の道で足す。

照合のしかた:
- 大文字小文字を区別しない。
- 英語の「語」は、前後が英数字でないときだけ当たる（domain の main、keyword の key、navigate の gate は当たらない）。`_` と `-` は区切りとして扱う（api_key の key は当たる）。
- 「句」と日本語は部分一致で当たる。
- 読み取りの印（R1 を外す語の一覧。この表だけで判定する）: `--read-only`、`ai_ro`、`-F /dev/null`、`SELECT` を含み INSERT / UPDATE / DELETE / ALTER / DROP / TRUNCATE / COPY を含まない文。ただし印が効くのは `*` を含まない文だけ（`*` を含む文は印があっても R1）。
- 目印は「当たったら保留」に倒す（止めすぎを選ぶ）。一覧は道具の中の1か所（辞書1つ）に置き、試験で守る。

### 2-3. Opus が自分では変えないもの（すべて R4 扱い。変化があれば PO 記録が要る）

hooks の登録（~/.claude とリポジトリ側の両方）、permissions.deny / ask / defaultMode、skipDangerousModePermissionPrompt など確認を省く設定、autoMode.soft_deny / environment、~/.claude/agent-tokens.json の danger_ops、~/.claude/scripts/ のフック本体、ADR-1011 と §4-6 の例外の文。これらの変更は今までどおり「AI が台本を作り、PO が `!` で反映する」。

### 2-4. 対象外

即時の阻止（ConfigChange フック。将来の候補）／agent-console の役割設定／Codex の設定／追跡されているリポジトリの .claude/settings.json（PR と Reviewer で守られているため、点検は写すが照合は PR 番号の台帳行で行う。§4-3）。

## 3. 変更前後

| | 変更前 | 変更後 |
|---|---|---|
| 許可の文を足す道 | AI は変えない（ADR-1011）。必要なら PO の `!` | 通常は道具が「記録→反映」を1回で行う。保留は道具が止め、PO の `!` 台本を出す |
| 記録 | `SM-` の文だけ ADR-1011 の台帳 | ~/.claude/logs/permission-changes.jsonl に1行ずつ（理由・意図・期待する効果・見直し日） |
| 点検の範囲 | settings の allow と hooks、permits の名前 | §2-1・2-3 のすべて |
| 写しの更新 | `--permissions` のたびに上書き | 定期実行が渡す `--commit-snapshot` のときだけ |
| 判定 | 増減の件数だけ | 台帳に無い変化・PO 記録の無い保留の変化・台帳の過去行の欠けを異常にする |
| 許可券の発行 | 記録なし | agent-events.jsonl に permit_issued |
| 見直し | 無し | 見直し日を過ぎた権限を一覧にし、週次で残す／外すと効果を書く |

## 4. 技術 How

### 4-1. 道具（新規）`scripts/dev/perm-change.py`

副命令は4つ（apply・record・review・sync）。終了コードは 0=成功、1=引数・検証・書き込みの失敗、3=保留、4=版のずれを直せない・通信できない（設定は変えていない）。パスは道具の中で組み立て、引数で受けない（`scripts/dev/consent-audit.py:5` と同じ方針）。関数は試験のために home と now を引数で受ける。

**apply**（記録と反映を1回で行う）
```
python3 scripts/dev/perm-change.py apply --target user-allow|user-automode-allow|repo-local-allow \
  --op add|remove --item '<文>' --intent '<何のため>' --reason '<なぜ今>' --expected '<期待する効果>' [--review-days N]
```
1. 必須欄（intent・reason・expected）が空、review-days が 1〜30 の外 → exit 1（何も書かない）。
2. op=add なら §2-2 の判定。当たれば台帳に `{"result":"held","category":"reserved:Rn"}` の行を書き、PO 用の台本（§4-5）を標準出力に出して exit 3（反映しない）。
3. op=remove で対象が例外の文 → exit 3。
4. 対象ファイルを ~/.claude/logs/perm-backup/<時刻>/ に写してから、JSON として読み、該当の配列だけを足し引きし、一時ファイル→rename で書く。add で既にある、remove で無い → exit 0 で台帳に `result:"noop"`。
5. 書いた後に JSON として読み直し、配列に文がある／無いことを確かめる。だめなら控えから戻して exit 1。
6. 台帳に1行追記（下の形）。台帳の追記は ~/.claude/logs/permission-changes.lock を mkdir のロック＋trap で守る（macOS に flock が無いため）。

**record**（反映は別の手段で行った変更を記録だけする。PR でマージした追跡ファイルの変更、PO の `!` で反映した保留の変更）
- 引数: `--target <下の表の値> --op add|remove|modify --item-hash <8桁> --po-ref <形> [--intent --reason]`。文そのものではなく item_hash を受ける（PO の台本や PR の差分から写すため）。1行で1要素。PR の差分に要素が3つあれば3行書く。
- `--po-ref` が必須。形は `PR#<数字>` か `consent:<k1>:<k2>:<k3>`（同意の台帳の key の3要素を `:` でつないだもの）のどちらかだけ。それ以外は exit 1。

**target の値と §4-2 の写しのキーの対応**（apply・record 共通。この表を道具の中の辞書1つに置く）

| target | 写しのキー | apply で使えるか |
|---|---|---|
| user-allow | user:permissions.allow | ○ |
| repo-local-allow | repo-local:permissions.allow | ○ |
| user-automode-allow | user:autoMode.allow | remove のみ（`SM-` の文と例外の文は不可） |
| user-automode-allow-sm | user:autoMode.allow（`SM-` の文だけを受ける） | ×（record のみ。po_ref は ADR-1011 の文書 PR） |
| repo-allow | repo:permissions.allow | ×（record のみ。§4-7 手順1） |
| repo-hooks | repo:hooks | ×（record のみ。§4-7 手順1） |
| user-deny | user:permissions.deny | ×（record のみ。R4） |
| user-ask | user:permissions.ask | ×（同上） |
| user-defaultmode | user:permissions.defaultMode | ×（同上） |
| user-skip | user:skip_flags | ×（同上） |
| user-hooks | user:hooks | ×（同上） |
| user-automode-soft-deny | user:autoMode.soft_deny | ×（同上） |
| user-automode-env | user:autoMode.environment | ×（同上） |
| user-local-allow / user-local-deny / user-local-ask / user-local-defaultmode / user-local-skip / user-local-hooks / user-local-automode-allow / user-local-automode-soft-deny / user-local-automode-env | user-local: に続けて、上の user- の行と同じ後半（例: user-local-deny → user-local:permissions.deny） | ×（同上） |
| repo-local-hooks | repo-local:hooks | ×（同上） |
| danger-ops | danger_ops | ×（同上） |
| hook-files | hook_files | ×（同上） |

ledger・tools_clean・permits の3キーには target が無い（§4-3 の A・B の照合に使わない）。

**起動時の確かめ**（apply / record / review / sync 共通。この順で行う）
1. 道具は `python3 -I -B` で起動される前提とし、`sys.flags.isolated` と `sys.flags.dont_write_bytecode` が立っていなければ exit 1（PYTHONPATH の影響と __pycache__ の作成を防ぐ。__pycache__ ができると、同じ場所を使う Mac の自動作業（recon §2）が「変更あり」で止まる）。
2. 自分のファイルの場所が ~/.salesanchor-tools/scripts/dev/perm-change.py でなければ exit 1（作業場所の写しで判定を消して走らせる道を閉じる）。
3. ~/.salesanchor-tools の `git remote get-url origin` が本リポジトリの GitHub の URL（道具の中の定数）でなければ exit 1。
4. `git status --porcelain --untracked-files=all` が空でなければ exit 1（変更があるときは同期もしない。Mac の自動作業と同じ条件）。
5. 基準の版 V を `git ls-remote origin refs/heads/main` で GitHub から取る（手元の origin/main は差し替えられるため基準にしない）。取れなければ exit 4。
6. HEAD が V でなければ、道具自身が同期する: `git fetch -q origin main` → 取れた FETCH_HEAD が V と同じことを確かめる（違えば exit 4。その間に main が進んだ場合で、V に揃え直さない）→ `git checkout -q --detach V` → 自分を同じ引数で起動し直す（`os.execv(sys.executable, [sys.executable, "-I", "-B", <自分のパス>, ...])`。起動し直したことを示す環境変数 `PERM_CHANGE_REEXEC=1` を立て、2回目も HEAD が V でなければ exit 4。無限に繰り返さない。この目印は「もう起動し直さない」判定にだけ使い、ほかの確かめを省く理由にしない）。fetch・checkout が失敗したら（他の自動作業と重なった index.lock など）exit 4。Mac の自動作業（disk-janitor・claude-archive）と同じ「変更が無いときだけ main に揃える」動きで、別の版へは動かさない。
7. 自分（perm-change.py）と consent-audit.py の sha256 が、`git show V:<パス>` の中身の sha256 と一致することを確かめる。違えば exit 1。
8. consent-audit.py の関数は、7 で照合した中身（読み直さない。照合と読み込みの間に自動作業が checkout しても照合済みのものを使う）から読み込む。`importlib.util.spec_from_file_location` で ~/.salesanchor-tools/scripts/dev/consent-audit.py を絶対パスで読む（`-I` では自分の場所が import の探し先に入らず、ファイル名にハイフンがあるため通常の import は使えない）。

**sync**（引数なし）: 上の 1〜7 だけを行い、揃っていれば `TOOLS_SYNCED=<V の先頭12桁>` を出して exit 0。週次点検の手順1で使う。

**review**（見直しの結果）
- `--hash <8桁> --decision keep|remove --effect '<観測した効果>' [--review-days N]`。remove のときは続けて apply --op remove を行う。

**台帳の1行**（JSON Lines）
`ts, actor("opus"|"po-script"), sub("apply"|"record"|"review"), target, op, item_hash, summary, intent, reason, expected_effect, review_by, category("normal"|"reserved:R0".."R4"), result("applied"|"held"|"noop"|"recorded"|"reviewed"), po_ref, prev_sha`

- item_hash: §4-2 の写しと同じ式。allow の文は `sha8(json.dumps(item, sort_keys=True, ensure_ascii=False))`（`scripts/dev/consent-audit.py:329` と同じ。共通の関数 `item_sha8` を consent-audit.py に置き、道具は起動時の確かめ 8 の方法で読む）。
- summary: 文の先頭80字。R3 の目印に当たる文は "[R3]" だけにする。
- prev_sha: 台帳の直前の行の sha256 の先頭16桁（1行目は "genesis"）。行が書き換え・削除されると鎖が切れる。

### 4-2. 点検の範囲を広げる `scripts/dev/consent-audit.py`

collect_permissions（`scripts/dev/consent-audit.py:319-343`）を広げる。写しのキーと各要素の式:

| キー | 中身 | 要素の式 |
|---|---|---|
| user:permissions.allow / deny / ask | ~/.claude/settings.json | `item_sha8(文)` |
| user:permissions.defaultMode | 同上 | `item_sha8(値)`（1要素） |
| user:skip_flags | 同上の skip で始まる最上位のキー | `item_sha8("<キー>=<値>")` |
| user:hooks | 同上 | 今の `event|matcher|sha8` のまま（:336） |
| user:autoMode.allow / soft_deny / environment | 同上 | `item_sha8(文)` |
| user-local:* | ~/.claude/settings.local.json の同じ項目 | 同上 |
| repo:permissions.allow / hooks | ~/.salesanchor-tools（週次点検の手順1で GitHub の main に揃えた版）の .claude/settings.json。本店の作業ツリーは他の作業で変わるため読まない | 同上 |
| repo-local:permissions.allow / hooks | 本店の .claude/settings.local.json | 同上 |
| danger_ops | ~/.claude/agent-tokens.json の danger_ops | `item_sha8(語)`（値そのものは出さない） |
| hook_files | ~/.claude/scripts/ 配下の通常ファイル（.backup を除く） | `<相対パスの sha8>|<中身の sha256 先頭8桁>` |
| ledger | 台帳 | `lines=<行数>`、`head=<最終行の sha256 先頭16桁>` の2要素 |
| tools_clean | ~/.salesanchor-tools | `head_on_main=<yes/no>`（HEAD が `git ls-remote origin refs/heads/main` の版の祖先か）、`dirty=<変更ファイル数>`、`tool_sha=<perm-change.py の sha256 先頭16桁>` の3要素 |

- 既存のキー名 `settings.json:permissions.allow` などは、新しいキーへ読み替える対応表を道具の中に持ち、初回の比較で「増減」にしない。
- permits（許可券のファイル名）は写しに残すが、照合（§4-3）の対象から外す。券は30分で消えるため。発行は permit_issued（§4-4）で見る。
- 前回の写しに無いキーは「初回」と表示し、異常にしない。

### 4-3. 照らし合わせ（run_permissions の拡張）

- 写しの更新は `--commit-snapshot` を付けたときだけ（定期実行だけが付ける）。付けないときは比べて表示するだけ。基準の写しは前回の定期実行の写し。
- ledger は C で、tools_clean は E でだけ判定し、permits（§4-2）とあわせて A・B の照合から外す。
- 残りの各差分（キー・増／減・要素）について、前回の写しの時刻以降の台帳の行（result が applied か recorded）を探す。対応は「target をキーへ読み替えた結果が同じ」かつ「item_hash が同じ」かつ「op が増減と同じ」。
- 異常の理由（1件1行、形を固定）:
  - `ABNORMAL_REASON=A <キー> <sha8>` 台帳に無い差分（UNLEDGERED）
  - `ABNORMAL_REASON=B <キー> <sha8>` §2-3 のキーの差分、または reserved の台帳行で、po_ref が次の条件を満たさないもの:
    - `PR#n`: 下の「record の行の確かめ」の `PR#n` の条件（取り込まれた差分で確かめ、mergedAt が対応する held の行より後）。ただし B の対象では、`PR#n` を受け付けるのは target が repo-allow・repo-hooks のときだけ。それ以外の保留の項目は PO 本人の同意（`consent:`）だけで説明できる（Opus は委任により自分で PR をマージできるため、PR では PO の確認の証にならない）。
    - `consent:<k1>:<k2>:<k3>`: 同意の台帳（`scripts/dev/consent-audit.py:213-220` の match_ledger_keys が読む3要素の key）に同じ3要素の行があり、used_at が held の行より後。
      - 鍵の形（改7）: k1 は64桁の16進、k2 は「1」の timestamp、k3 は 1〜10 の十進数。`parse_consent_ref` は `consent:([0-9a-f]{64}):(.+):([1-9]|10)` で受け、k3 を整数にして返す（フックは台帳に `[sha, H.timestamp, opnum]` を opnum が整数で書く。`docs/handoff/conversation-consent/hooks/consent_check.py` の 10.）。形が合わない po_ref は確かめを通らない。
      - 改7（PO の `!` で台本を走らせた場合）: 同意の台帳の行は AI の Bash がフックで同意を使ったときにしかできないため、PO が `!` で走らせた台本の record には行が無い。台帳に同じ3要素の行が無いときだけ、次の (a)〜(e) がすべて揃えば台帳の行と同じに扱う（used_at の代わりに k2 の時刻を使う）。判定は「1」を起点にし、フック（consent_check.py の `_check_inner` の 4.〜6.）と同じ並びを求める。
        - (a) 会話の記録（~/.claude/projects/*/*.jsonl）の1つのファイルに、timestamp が k2 で、`is_human` かつ `is_typed_one` で `isSidechain` でない行 H がある（`scripts/dev/consent-audit.py` の is_human・is_typed_one を使う）。
        - (b) 同じファイルで H より前の、最後の `isSidechain` でない assistant の行の中身がすべて text で、最後の text の sha256 が k1。
        - (c) (b) の行と H の間に、`is_human` の行も compact の行も無い。
        - (d) その text が parse_ticket と同じ形（見出し1つ・`1. 上の同意票の操作を実行する` で始まる選択肢の行1つ・操作の番号が重ならない）を通り、`操作<k3>: ` の行の操作が次のどれかで始まる: `bash ~/.salesanchor-tools/docs/handoff/permission-delegation/po-register-delegation.sh `、`bash ~/.salesanchor-tools/docs/handoff/permission-delegation/po-unregister-delegation.sh `、`bash ~/CC報告ファイル-keep/permission-delegation/po-apply-`。
        - (e) record の行の ts が k2 より後で、k2 から 24 時間以内。
      - 1回だけの制限（下）と、同意票の本文に item_hash があることの確かめ（「record の行の確かめ」。used を k2 に置き換える）は、台帳の行がある場合と同じに効く。
      - 会話の記録が見つからない（移された・消えた）ときは確かめを通らず、B として PO に知らせる（止めすぎに倒す）。
    - 同じ po_ref は台帳の record の行で1回だけ使える（2回目以降は B）。PR は1つの PR に要素が複数あるため「po_ref と item_hash の組」で1回。この1回の制限は held の有無にかかわらず、すべての record の行に効く。
  - **record の行は category（normal でも reserved でも）や held の行の有無にかかわらず、すべて次の確かめを通ったときだけ差分の説明に使う**（第6版。通らない record の行は無いものとして扱う。その差分は、§2-3 のキーなら常に B、それ以外は held の行があれば B、無ければ A）:
    - `consent:`: 上の条件に加え、3要素の sha が一致した同意票の本文に item_hash（8桁）がある（どの文の変更への同意かを結び付ける）。held の行が無いときは「used_at が前回の写しの時刻より後」。
    - `PR#n`: `gh pr view n --json state,mergedAt,mergeCommit` で MERGED、mergedAt が前回の写しの時刻より後（held の行があればその行より後）、mergeCommit が ~/.salesanchor-tools の V の祖先（`git merge-base --is-ancestor`）。そのうえで、取り込まれた中身（`git diff <mergeCommit>^1 <mergeCommit>`。PR の本文は後から書き換えられるので使わない）について target ごとに:
      - repo-allow・repo-hooks: `.claude/settings.json` の差分の足した行か消した行に、その要素の文（JSON の文字列）がある。
      - user-automode-allow-sm: 今の user:autoMode.allow のうちその item_hash の文が `SM-<番号>` で始まり、`docs/handoff/design-approval-ticket/permission-ledger.md` の差分の足した行にその `SM-<番号>` がある。
      - それ以外: 差分の足した行のどこかに item_hash（8桁）がある。
    - gh か git が使えなければ確かめは通らない。
    - 追跡されたリポジトリの settings.json（repo:）の差分は、§4-7 の手順1で定期実行が書く PR 番号の record で照合し、上の repo-allow・repo-hooks の条件（settings.json の差分にその要素の文）で確かめる。
  - `ABNORMAL_REASON=C ledger <sha8>` 台帳の鎖（prev_sha）が切れている、または行数が前回の写しより減った、または前回の head の行が見つからない
  - `ABNORMAL_REASON=D permit <件数>` permit_issued(by=ai) のうち、同じ時刻の前後30分に同意の消費（consent_consumed）も台帳の行も無いもの
  - `ABNORMAL_REASON=E tools <小分類>` ~/.salesanchor-tools について、小分類は次の4つ: `dirty`（変更・追跡外のファイルがある）、`stale`（HEAD が `git ls-remote origin refs/heads/main` の版の祖先でない）、`sha`（perm-change.py・consent-audit.py の sha がその版の同じファイルと違う）、`offline`（ls-remote が取れない）
- 理由行は ABNORMAL= の行より前に出す。既存の `PERMISSION_CHANGES=` と `ABNORMAL=` の1行ずつの形は変えない（ABNORMAL は今の条件に A〜E を OR で足す）。
- 見直し日を過ぎ、review の行が無い権限を `REVIEW_DUE=<sha8>,<sha8>...`（無ければ `REVIEW_DUE=0`）で出す。異常ではない。
- rc は今のまま 0。点検の担当は rc ではなく出力の行で判定する（Python の例外で落ちた場合は ABNORMAL= の行が出ないので、それを異常とする）。

### 4-4. 許可券の発行を記録 `scripts/permit-danger.sh`

- 券を書いた直後に ~/.claude/logs/agent-events.jsonl へ `{"type":"permit_issued","op_sha8":<sha8>,"by":"ai"|"human","ts":<UTC>}` を1行追記する（既存の行の type の書き方に合わせる）。
- by: 環境変数 CLAUDECODE があれば "ai"。PO の `!` でも立つため、"ai" は「AI か PO の `!`」の意味（recon §3、ADR 受け入れたリスク）。
- 券の作り方・期限・消費は変えない。追記に失敗しても券の発行は止めない（標準エラーに1行出す）。

### 4-5. 保留のときに出す PO 用の台本

道具は exit 3 のとき、~/CC報告ファイル-keep/permission-delegation/po-apply-<時刻>.sh を書き、パスを出す。中身は「控えを取る→同じ JSON 書き換え→読み直し→`perm-change.py record --po-ref consent:<鍵>`」（PR#n は使わない。同意票の本文に item_hash を書き、PO の「1」で得た鍵を台本の引数で受ける。target が repo-allow・repo-hooks のときだけ PR#n も可）。台本・routine.json・本書の手順で道具を呼ぶときは、必ず PDL-1 と同じ形（`cd ~/.salesanchor-tools && python3 -I -B scripts/dev/perm-change.py <副命令> ...`）で書く（本書で `perm-change.py record` などと略しているのもこの形の意味）。Opus は ADR-1033 の同意票の形でこの台本の実行を PO に聞く。

### 4-6. Opus が道具を通せるようにする（PO の `!` 1回）

Claude Code の自動判定は、AI が自分の許可を変えることを止める（recon §3 (b)）。PO 決定に沿って、autoMode.allow に次の例外の文を1つ足す。足すのは PO が `!` で実行する台本 `docs/handoff/permission-delegation/po-register-delegation.sh`（便1に含める）。

> PDL-1: Running exactly `cd ~/.salesanchor-tools && python3 -I -B scripts/dev/perm-change.py apply|record|review|sync ...` is allowed (only that directory; the tool itself verifies the origin URL, a clean tree, and its own content against GitHub main via `git ls-remote`, and when the tree is clean it fetches and checks out exactly that GitHub main commit, as the existing Mac maintenance jobs do). Any other change under ~/.salesanchor-tools — editing files, changing git config or refs yourself (fetch, update-ref, checkout, reset) — is not covered and remains Self-Modification. This tool itself refuses broad, destructive, push, secret, and guard-related entries and records every change; this is the owner's delegation under ADR-1034. Directly editing settings files with Edit, Write, sed, or other tools is still Self-Modification.

台本は ADR-1011 の登録台本（`docs/handoff/design-approval-ticket/po-register-self-maintenance.sh`）と同じ順で、控え→追加→読み直し→台帳に `record --po-ref consent:<鍵>` を書く。鍵は台本の第1引数で受け（`consent:` で始まらなければ何も変えずに終わる）、Opus は実行を聞く同意票（ADR-1033）の本文に PDL-1 の item_hash を書き、PO の「1」の後にその鍵を入れた `!` の1行を示す。外す台本 `docs/handoff/permission-delegation/po-unregister-delegation.sh` も同じ形にする。

改7: 鍵は `consent:<同意票の本文の sha256>:<PO の「1」の timestamp>:<操作の番号>`。PO の `!` は同意の台帳に行を作らないので、§4-3 の改7 の確かめで照らす。PO に聞く前に、Opus は ~/.salesanchor-tools の HEAD に `scripts/dev/perm-change.py` があることを確かめる。無ければ（便1 のマージ直後は無い）Mac の自動作業（recon §2 の claude-archive・disk-janitor。時刻は recon §2）が origin/main に揃えるのを待つ。PO の `!` の1行は `bash ~/.salesanchor-tools/docs/handoff/permission-delegation/po-register-delegation.sh consent:<鍵>` とし、台本は ~/.salesanchor-tools の版を使う。

### 4-7. 週次点検の手順の更新（agent-console id bb581a6f）

便1マージ後に Opus が ac-routine で promptText を差し替える。差し替える本文はリポジトリの `docs/handoff/permission-delegation/routine.json` を正とする（公開して困る内容を含まないことを Reviewer が確認する）。足す手順（この順で行う）:
1. 点検の前に `perm-change.py sync` で ~/.salesanchor-tools を GitHub の main に揃える（Opus は git の fetch・checkout を自分で打たない。PDL-1）。sync が exit 1 でも手順2の点検は走らせ、`E tools dirty/sha` として報告する。exit 4 なら5分おいて1回だけやり直し、それでも 4 なら手順3で `E tools offline/stale` として報告する。前回の点検以降に main へ入った `.claude/settings.json` の変更を sync が出した `TOOLS_SYNCED=<V>` の版で `git log --first-parent <V> --since=<前回> -- .claude/settings.json` で拾い、各コミットの PR 番号と、そのコミットで増減した要素（§4-2 の式の item_hash）ごとに `perm-change.py record --target repo-allow|repo-hooks --op add|remove --item-hash <8桁> --po-ref PR#n` を書く。
2. 点検のコマンドに `--commit-snapshot` を付けて実行する。
3. `ABNORMAL_REASON=` が1行以上なら PO へ3行の型で報告。ただし `E tools offline` と `E tools stale` だけのときは、手順1からもう1回やり直し、残った場合だけ報告する（点検の途中で main が進んだ・通信が途切れただけの誤報を減らす）。
4. `REVIEW_DUE` の各権限について、~/.claude/logs/permission-denied.jsonl の該当コマンドの件数（足す前の4週と足した後）と使われた形跡を見て、keep / remove を決め、`perm-change.py review` で書く。
5. 点検の出力を ~/CC報告ファイル-keep/consent-weekly/<日付>.txt に写す（/tmp は消える）。前回のファイルの `ledger head` と今回の写しの値を並べて残す。

### 4-8. Opus の日々の手順

1. 権限不足で止まったら、足す文を最小の形で決める（コマンド名1語＋何でも、にしない）。
2. `perm-change.py apply --op add ...` を実行する。exit 0 なら続行。exit 3 なら同意票で PO に台本の実行を聞く。exit 1 なら標準エラーの理由を読み、欄の不足なら直して1回だけやり直す。場所・URL・sha・変更ありの理由なら止めて PO に報告する（道具の置き場所が崩れている）。exit 4 なら5分おいて1回やり直し、それでも 4 ならその権限は足さずに作業を続け、終わりの報告に1行書く。
3. 自動判定に止められたら言い換えず、PO に台本の実行を聞く。
4. 設定ファイルを Edit / Write / sed で直接直さない。

## 5. KPI

| KPI | 基準値 | 目標 | 測り方 |
|---|---|---|---|
| K1 台帳に無い権限の変化 | 初回点検（2026-10-26 以降）の値 | 毎週 0 件 | `ABNORMAL_REASON=A` の行数 |
| K2 保留の変化で PO 記録が無いもの | 同上 | 毎週 0 件 | `ABNORMAL_REASON=B` の行数 |
| K3 台帳の鎖の切れ | - | 常に 0 件 | `ABNORMAL_REASON=C` の行数 |
| K4 見直し期限切れの放置 | - | 2週続けて同じ sha8 が出る件数 0 | 前週と今週の `REVIEW_DUE` の共通部分 |
| K5 権限不足で止まる回数 | 導入前4週の ~/.claude/logs/permission-denied.jsonl の件数（便1後の初回点検で数えて記録） | 8週後に週あたりで減っている | 同ファイルの週ごとの件数 |

## 6. 外部・過去事例の参照と我々への応用

- 直接の数値根拠を持つ外部事例は用いない。理由: 「AI が自分の権限を足し引きし、事後に台帳で点検する」形の公開事例で、件数や効果の実測値を確認できたものが無い（未確認）。設計の正しさは §8 の受け入れ試験と K1〜K5 の実測で確かめる。
- 過去事例（本リポジトリ）: ADR-1011 の台帳（`docs/handoff/design-approval-ticket/permission-ledger.md`）は 2026-10-13 から、`SM-` の文の足し引きを理由つきで残せている。本件は「変える前に書く・週次で照らす」の型を通常の許可の文に広げ、さらに「書くことと変えることを同じ道具で1回に行う」ことで書き忘れを起きにくくする。台帳は公開リポジトリではなく ~/.claude/logs に置く（許可の文に内部の道筋が入るため）。

## 7. 弊害とリスク

1. 点検は事後なので、§2-3 の項目が道具を通らずに変わった場合は最長1週間見つからない。対処: 直接の書き換えは自動判定が止める（例外の文は道具の実行だけを許す）。将来 ConfigChange フックで即時に止める案を残す。
2. 目印の取りこぼし。対処: R0 で広い形を止め、目印は止めすぎに倒す。4週ごとに当たりすぎ・漏れを見直す（§11）。目印を減らす変更は R4。
3. 台帳の書き換え。対処: prev_sha の鎖と、写しの lines / head、keep に残す点検結果の三か所で照らす（K3）。
4. PO の `!` と AI を区別できない。対処: permit_issued(by=ai) は同意の消費か台帳の行で説明できれば正常とする（D）。
5. 道具の不具合で設定ファイルが壊れる。対処: 書く前の控え・一時ファイル→rename・読み直しで失敗なら戻す。A3 で試験。
6. 秘密の値が台帳や出力に写る。対処: summary は R3 で伏せる。danger_ops と hooks はハッシュだけ。
7. ADR-1011 との食い違い。対処: ADR-1034 で ADR-1011 の範囲外のうち「`SM-` 以外の allow」を改め、ADR-1011 の備考に1行足す。`SM-` の変更は ADR-1011 の手順のまま、道具の record（target user-automode-allow-sm、po_ref は ADR-1011 の文書 PR 番号）で台帳に載せ、A にしない。
8. 導入直後の数週は、既存の po-apply 台本（ADR-1011・ADR-1033 ほか）が台帳に record を書かないため、PO が反映した変更が A として出る。対処: 初回は §4-2 の「初回」の扱いで基準の写しを取るだけにする。その後に既存の台本で反映する変更は、Opus が同意票（本文に item_hash）で PO に聞き、consent で record する。それでも移行の間に出た A/B は PO に報告して確かめる。以後の新しい台本は §4-5 の形で record を含める。
9. ~/.salesanchor-tools は Mac の自動作業4つ（recon §2）と共有。週次の更新は同じ手順・同じ条件（変更なし）で行うので、それらの前提を崩さない。道具が __pycache__ を作ると自動作業が止まるため `-B` を必須にする（§4-1）。

## 8. 受け入れ基準

試験は `scripts/dev/permission-delegation-tests.py`（新規）。すべて一時 HOME と一時の本店ディレクトリで行い、本物の ~/.claude に触れない。

| 基準 | 検証方法 |
|---|---|
| A1 必須欄の欠け・review-days 範囲外・record の po_ref の形違いは exit 1 で何も書かない | 試験: 各ケースで exit と台帳の行数が変わらないこと |
| A2 通常の add / remove が user-allow・repo-local-allow で、remove が user-automode-allow で反映され、台帳に applied の行が1行増える | 試験: JSON を読み直して配列の中身と台帳の行を確認 |
| A3 書いた後の読み直しに失敗すると控えから戻り exit 1 | 試験: 書き込み関数を失敗させて元のファイルと同じ sha256 |
| A4 R0〜R4 の目印の例（各記号3つ以上、大文字・日本語を含む）を add すると exit 3・反映なし・held の行・台本のパスが出る。例外の文の remove も exit 3 | 試験 |
| A5 §4-2 の各キー（ledger・tools_clean・permits を除く）で、台帳に無い増減を1件ずつ作ると `ABNORMAL_REASON=A`（§2-3 のキーは B）と `ABNORMAL=yes` | 試験（キーの数だけ） |
| A6 台帳にある増減は A にならず `ABNORMAL=no` | 試験 |
| A7 po_ref が次のどれかなら B: PR が MERGED でない／mergedAt が held より前／取り込まれた差分に item_hash が無い（本文にだけある場合を含む）／target が repo-allow・repo-hooks 以外の保留の項目に `PR#n`／`consent:` の3要素が同意の台帳に無い／同意票の本文に item_hash が無い／used_at が held より前／同じ po_ref の2回目。逆に、§4-6 の登録台本が書く PDL-1 の record（同意票の本文に item_hash のある consent）は B にならない | 試験（gh の呼び出しは関数で差し替え、mergeCommit は A17 の一時の git リポジトリで作る） |
| A8 台帳の途中の行を書き換える・行を消すと C | 試験 |
| A9 見直し日を過ぎた行が REVIEW_DUE に出て、review の行があれば出ない | 試験（now を関数の引数で与える） |
| A10 permit-danger.sh で permit_issued が1行増え、CLAUDECODE の有無で by が ai / human。説明の無い by=ai は D | 試験（一時 HOME） |
| A11 初回（前回の写しに無いキー）と旧キー名からの読み替えは異常にならない | 試験 |
| A12 `--commit-snapshot` を付けない実行では写しが変わらない | 試験: 実行前後の写しの sha256 |
| A13 R3 の目印に当たる文の summary は "[R3]" だけで、文の中身が台帳・出力のどこにも出ない | 試験: ファイル全体を検索 |
| A14 既存の consent-audit の試験がすべて通る | 既存の試験を同時に実行し失敗 0 |
| A15 定期実行 bb581a6f の promptText が routine.json の promptText と一致 | Opus が ac-routine の一覧出力から promptText を取り出し、sha256 を比べる |
| A16 PO の `!` 台本の後、例外の文 PDL-1 が autoMode.allow に1件だけあり、Opus の `perm-change.py apply` の試し（害の無い文の add と remove）が自動判定に止められない | 反映後に Opus が実行し、台帳の applied 2行を確認 |
| A17 道具の起動時の確かめ: (1) exit 1 になる状態 — ~/.salesanchor-tools 以外から起動／`-I -B` なしで起動／origin の URL が違う／作業ツリーに変更や追跡外のファイルがある（consent-audit.py だけを書き換えた場合を含む。同期もしない）。手元でコミットして HEAD を進めた場合は、同期で V に戻ってから照合するので (3) と同じく exit 0 で、HEAD が V・2ファイルの sha が V と一致することを確かめる。(2) exit 4 になる状態 — ls-remote が取れない／fetch が失敗する／ls-remote と fetch の間に main が進んで FETCH_HEAD が V と違う。(3) exit 0 になる状態 — main が1つ進んだだけ（悪意なし）なら道具が自分で揃えて起動し直し（回数を数えて1回だけ）、HEAD が V になる／手元の origin/main を `git update-ref` で別の版に差し替えただけでも、基準が ls-remote なので結果は変わらない。(4) `-I -B` で起動して consent-audit.py の関数が読める。(5) 週次点検は dirty・stale・sha・offline のそれぞれで `ABNORMAL_REASON=E tools <小分類>` | 試験（一時の git リポジトリを GitHub 役の bare リポジトリと組んで再現。origin の URL の定数は試験のときだけ差し替えられるよう関数の引数で受ける） |
| A18 R0 の例（`Bash(python3 scripts/*)`・`Bash(bash ~/worktrees/*)`・perm-change を含む文・autoMode.allow の add）が exit 3。読み取りの印があっても `*` を含む文（`Bash(ssh -F /dev/null prod1 *)`・`Bash(psql ai_ro -c "SELECT * FROM x")`）は保留（R0、rm 以外は R0 の判定が先）で exit 3。第6版 改2 の反例（`Edit`・`Write`・`Read`・`WebFetch`・`Edit(*)`・`Write(*)`・`Edit(/Users/x/.claude/CLAUDE.md)`・`Edit($HOME/.claude/CLAUDE.md)`・`NotebookEdit(**)`・`Bash()`・`Bash( )`・`Bash (curl *)`・`mcp__playwright`）と、改3 の反例（`Edit(~/.zshrc)`・`Write(~/Library/LaunchAgents/x.plist)`・`Edit(~/.gitconfig)`・`Edit(.git/config)`・`Edit(../x)`・`Edit(docs/)`・`Edit(//etc/hosts)`・`Edit(config)`・`Edit(.zshrc)`・`Edit(.husky/pre-commit)`・`Edit(scripts/permit-danger.sh)`・`Edit(docs/.hidden/x)`・`Bash(bash scripts/permit-danger.sh)`・`Bash(python3 scripts/dev/consent-audit.py)`・`Bash(./scripts/permit-danger.sh)`・`WebFetch(domain:*)`・`WebSearch`・`mcp__github__merge_pull_request`・`mcp__playwright__browser_click`）がすべて R0。`Edit(docs/handoff/x.md)`・`Read(docs/**)`・`WebFetch(domain:docs.python.org)`・`mcp__context7__query-docs` は R0 にならない。止めすぎの例（`*` の無い `-F /dev/null` の ai_ro の文、domain・keyword・navigate を含む文）が R1〜R4 に当たらない。第6版の反例（`Bash(gh api *)`・`Bash(gh api:*)`・`Bash(docker compose *)`・`Bash(git -C /x *)`・`Bash(git -c x=y *)`・`Bash(g*)`・`Bash( *)`・`Bash(**)`・`Bash(osascript -e *)`・`Bash(sudo -n *)`・`Bash(command -p *)`・`Bash(awk -f *)`・`Bash(curl -X POST *)`・`Bash(launchctl load *)`・`Bash(python3.12 -c *)`・`Bash(/bin/bash -c *)`・`Bash(ls *)`・`Bash(git config --global *)`・`Bash(git log --oneline *)`・`Bash(git log --output=x *)`・`Bash(cp -f *)`・`Bash(gh alias set *)`・`Bash(rg --pre x *)`・`Bash(security dump-keychain *)`・`Bash(gh pr view extra *)`）がすべて R0、`Bash(rm -v *)`・`Bash(/bin/rm -f *)` が R1。受け入れの例（`Bash(gh pr view *)`・`Bash(git status *)`・`Bash(grep *)`・`Bash(gh run list:*)`）は R0 にならない。改5 の反例（`Bash(grep * ; id)`・`Bash(wc * | sh)`・`Bash(grep * > x)`・`Bash(PYTHONPATH=x python3 y)`・`Bash(command python3 x)`・`Bash(time bash x)`・`Bash(nohup sh x)`・`Bash(ls && bash x)`・`Bash(ls; python3 x)`・`Bash(curl x | sh)`・`Bash(echo $(id))`）がすべて R0。改6 の反例（`Bash(find docs -exec sh docs/x {} +)`・`Bash(awk -f docs/x f)`・`Bash(open docs/x)`・`Bash(launchctl load docs/x)`・`Bash(git -c core.pager=x log)`・`Bash(git z)`・`Bash(gh alias set z x)`・`Bash(echo $HOME)`・`Bash(wc -l docs/x)`・`Bash(git status --porcelain)`・`Bash(/tmp/x/grep foo bar)`・`Bash(./gh pr view 1)`・`Bash(docs/tools/grep foo bar)`・`Bash(grep foo "-r")`）がすべて R0。`Bash(git status)`・`Bash(gh pr view 4544)`・`Bash(grep foo docs/x)` は R0 にならない | 試験 |
| A19 held の行が無い record の行（category normal）で、po_ref が確かめを通らないもの（存在しない PR・未取り込み・本文にだけ item_hash を書き足し差分に無い PR・差分の台帳に別の SM 番号しか無い PR・SM- でない文に user-automode-allow-sm・settings.json の差分にその文が無い PR で repo-allow・前回の写しより前の consent・本文に item_hash が無い無関係な同意票の consent・同じ PR と item_hash の組の2回目）は差分の説明にならず `ABNORMAL_REASON=A`。通るものは A にならない | 試験（gh は偽の応答に差し替え、mergeCommit と `git diff`・`merge-base` は A17 の一時の git リポジトリを使い回す） |
| A20（改7）同意の台帳に行の無い `consent:` は、§4-3 改7 の (a)〜(e) が揃えば説明に使え、どれか1つでも欠ければ使えない。通る例: 揃った正しい例1件、台帳の行（k3 が整数）がある従来の道。通らない例: sha の合う同意票が無い／同意票が「1」の後にある／同意票と「1」の間に人の入力か compact がある／直前の assistant の行が sidechain／「1」が sidechain・AI の行・「1」以外／同意票に見出しか選択肢の行が無い／`操作<k3>:` の行が無い／操作が決まった台本で始まらない（別件の po-apply 台本を含む）／k3 が数字でない・k1 が64桁でない／record が k2 より前か 24 時間より後／同意票に item_hash が無い／同じ po_ref の2回目 | 試験（一時の home に会話の記録の jsonl を作る。試験の補助関数 consent_ref の k3 は整数に直す） |

## 9. 計画票

| 便 | 中身 | 担当 | 触るファイル |
|---|---|---|---|
| 便1 | §4-1〜4-5 の実装と試験、§4-6 の台本2本、routine.json | Sonnet（実装カード） | `scripts/dev/perm-change.py`（新規）、`scripts/dev/consent-audit.py`、`scripts/permit-danger.sh`、`scripts/dev/permission-delegation-tests.py`（新規）、`docs/handoff/permission-delegation/po-register-delegation.sh`（新規）、`docs/handoff/permission-delegation/po-unregister-delegation.sh`（新規）、`docs/handoff/permission-delegation/routine.json`（新規） |
| 便1後 | PO の `!` で例外の文を登録（A16）、定期実行の差し替え（A15）、初回点検で K1〜K5 の基準値 | PO（`!` 1回）と Opus | リポジトリ外 |

## 10. 戻し方

- PO が `docs/handoff/permission-delegation/po-unregister-delegation.sh` を `!` で実行し、例外の文を外す（以後、道具は自動判定で止まる）。
- 便1 の PR を revert する。台帳ファイルは残しても害は無い。
- 定期実行の手順は ADR-1033 の版に戻す。差し替える前に、今の定期実行の設定を ~/CC報告ファイル-keep/permission-delegation/routine-before.json に控えておき、それを ac-routine で入れ直す。
- 道具が足した許可の文を戻すときは、台帳の applied の行を新しい順に `perm-change.py apply --op remove` する。

## 11. 維持の仕組み（継続）

- 守り手: 週次点検の定期実行（agent-console「同意と権限の週次点検」id bb581a6f、毎週月曜 09:30）と、その結果を読む Opus。
- 道具の動作は `scripts/dev/permission-delegation-tests.py` で守る。
- 4週ごとに K1〜K5 を ~/CC報告ファイル-keep/consent-weekly に並べ、目印の当たりすぎ・漏れを見直す（PDCA の Check と Act）。目印を減らす・広げる変更は R4 なので PO の確認を取る。

## 12. 審査

- 第1版: Architect（Opus、読み取りのみ）REVISE。HIGH 5・MEDIUM 7・LOW 2。すべて本第2版で反映（HIGH1→§2-1・§7-7、HIGH2→§2-3・§4-2、HIGH3→§2-2 R0、HIGH4→§4-1 record・§4-3 B、HIGH5→§4-3 `--commit-snapshot`・A12、MEDIUM6→§4-1 item_hash、7→§4-2 permits、8→§4-3 出力形、9→§4-3 rc、10→§4-1 関数の引数、11→§4-1 prev_sha・§4-2 ledger、12→recon §3 を抽象化、LOW13→A15、14→§5 K5）。
- 第2版: REVISE。HIGH 3・MEDIUM 3・LOW 2。第3版で反映（HIGH1→§4-1 起動時の確かめ・PDL-1 を ~/.salesanchor-tools に限定・§4-2 tools_clean・§4-3 E・A17、HIGH2→R0 に実行役＋何でも・perm-change・A18、HIGH3→autoMode.allow の add は常に R0、MEDIUM4→§4-1 consent の形・§4-3 B の条件・A7、5→照合のしかた・読み取りの印・A18、6→repo: を ~/.salesanchor-tools で読む・§4-7 手順4、LOW7→§10、8→§7-8）。
- 第3版: REVISE。HIGH 2・MEDIUM 4・LOW 3。第4版で反映（HIGH1→§4-1 基準を ls-remote・§4-3 E・PDL-1 に git の参照の変更を範囲外と明記・A17、HIGH2→読み取りの印は `*` の無い文だけ・A18、MEDIUM3→§4-7 `--first-parent`、4→§4-1 target の表と record の引数、5→`-I -B`・consent-audit.py の sha・A17、6→§4-3「A〜E」・A2、LOW7→§4-7 手順1、8→§7・§8 の並び、9→recon §2・§7-9）。
- 第4版: REVISE。HIGH 1・MEDIUM 5・LOW 2。第5版で反映（H1→§4-1 起動時の確かめを順番つきにし、変更が無いときは道具自身が GitHub の main に揃えて起動し直す・副命令 sync・exit 4・§4-7 手順1・§4-8 手順2・PDL-1、M1→§4-2 repo: と tools_clean を ls-remote 基準に、M2→§4-1 target の表を1行1キーに、M3→§4-3 ledger・tools_clean・permits を A・B から外す・A5、M4→§4-1 確かめ 8 で importlib、M5→A17 を exit 1/4/0 に分けて update-ref だけは結果が変わらないことを試す、L1→§4-5 呼び方の形、L2→§4-3 E の小分類・§4-7 手順3）。
- 第5版: **APPROVE**（2026-10-19、Architect＝Opus の読み取り審査。同一 AI による自己審査で、独立した第二者レビューではない）。MEDIUM 1・LOW 4 を本書に反映（MEDIUM1→§4-1 確かめ 6 の FETCH_HEAD 不一致は exit 4、LOW1→目印 `PERM_CHANGE_REEXEC=1`、LOW2→確かめ 8 は照合済みの中身を使う、LOW3→§4-7 手順1 は `<V>` で履歴を引く、LOW4→sync が exit 1 でも点検を走らせる）。A17 (2) に「fetch の間に main が進んだ」、(3) に「起動し直しは1回」を足す。
- 第6版（便1 の Reviewer REQUEST_CHANGES を受けた設計の直し、2026-10-19）: HIGH-1 held の無い record で A/B を消せる→§4-3 で record の行はすべて po_ref を確かめる・A19。MEDIUM-1 R0 の穴→§2-2 R0 を「狭いと示せなければ R0」に反転・実行役の一覧・rm は R1・A18 に反例。MEDIUM-2・LOW-1〜6 は実装の直し（card-bin1.md 追補）。第6版の Architect 差分審査 REVISE（HIGH-a 本文は後から書き換えられる→取り込まれた差分で確かめる／HIGH-b consent と item_hash の結び付け／MEDIUM SM 番号の結び付け／MEDIUM-a rm のパス／MEDIUM-b 実行役の拒否リスト→受け入れリストへ反転／LOW 1回の制限の範囲）をすべて反映。再審査 REVISE（B の PR#n の古い文・A7・repo: の注記・A19 の試験の材料）を反映し、あわせて「Opus が自分でマージした PR で保留の項目を説明できる」穴を、B の対象の PR#n を repo-allow・repo-hooks に限ることで閉じた（残りは ADR の受け入れたリスク）。再々審査 REVISE（PDL-1 の登録記録が B になる・§4-5 の台本の文）を、登録・外す台本と保留の台本の po_ref を consent に揃えて反映（A7 に1件）。
- 第6版 改2（便1 の Reviewer 再審査 REQUEST_CHANGES、2026-10-19）: MEDIUM-A R0 が Bash 以外の広い許可（道具名だけ・Edit/Write の `*` や絶対パスの .claude・括弧の形の崩れ）を止めない→§2-2 に「文の形」と Bash 以外の R0 を追加、A18 に反例。LOW-A §2-3 のキーは record が通らなくても常に B。LOW-B A18 の ssh/psql の文を R0 に。LOW-C ADR の R0 の説明を揃えた。LOW-D は PR 本文の直し。
- 第6版 改3（改2 の Architect 差分審査 REVISE）: MEDIUM-1 Edit 系が拒否の文字列並べのまま→相対パスの受け入れ形に反転。MEDIUM-2 Bash 以外の `*`→WebFetch は domain の名前に `*` 不可、ほかは受け入れ形のみ。MEDIUM-3 MCP の道具名に危険語が無いと素通り→読み取り専用サーバーの受け入れ一覧（context7）。LOW サーバー名の `-` を許す。§2-2 R0 を「R0 にしない形」の一覧に統一。改3 の差分審査 REVISE（(b) の名前だけの文がどの深さにも当たるおそれ→途中に `/`・最初の段の一覧・`.` 始まりの段なし／固定の Bash の実行役とパス先頭→R0／(c)(d) の組み合わせと ADR の R0 説明→ADR／(e) の道具名の文字）を反映（改4）。改4 は Architect 差分審査で APPROVE。任意の LOW（試験の命令とコードの書き換えの組み合わせ）は ADR の受け入れたリスクに1行足した。
- 第6版 改5（便1 の Reviewer 再審査 APPROVE の申し送り MEDIUM 2件）: `*` を含む Bash の文が `*` より後を見ない／`*` の無い文が先頭の語しか見ない→(a) に「中身に `;`・`&`・`|`・`>`・`<`・`` ` ``・`$(`・改行、先頭の語の `=` は R0」と包み役（command・time・nohup ほか）を実行役に追加。A18 に改5 の反例。文書の個人のパスを `~` に置き換え。
- 第6版 改6（改5 の Architect 差分審査 REVISE: 実行役の一覧が第6版より狭い・find -exec・awk -f・git -c・gh alias など、拒否の一覧では抜けが残る）: (a) を `*` の有無にかかわらず Bash の受け入れの一覧だけを通す形に反転。記号の条件は `$` 全体に広げた。実行役の一覧は不要になり外した。Claude Code が連結した命令を分けて照合することを公式の文書で確かめ、前提として (a) に書いた（Context7 は月の上限で使えず、公式の文書を直接確認）。 改6 の差分審査 REVISE（一覧と比べる先頭の語をパスを外して比べると同じ名前の別のプログラムが通る→書かれたままで比べる・引号と `\` は R0・A18 に例）を反映。
- 第6版 改7（便1 マージ後、PO への登録の依頼の準備で Opus が見つけた穴、2026-10-19）: 同意の台帳の行は AI の Bash がフックで同意を使ったときにしかできない（`docs/handoff/conversation-consent/hooks/consent_check.py` の `_check_inner` の 10.）。PO の `!` で走らせる台本の `consent:` は台帳に行が無く、点検で必ず通らない→§4-3 に会話の記録で照らす道（改7）を追加・A20。あわせて、便1 のマージ直後は ~/.salesanchor-tools に道具が無いので、Mac の自動作業が揃えるのを待ってから PO に聞く手順を §4-6 に追加。
  - 改7 の Architect 差分審査 REVISE: HIGH-1 同意票と「1」の並びを縛らず PO の別の「1」を流用できる→「1」を起点にフックと同じ並び（(a)〜(c)）を求める。MEDIUM-1 k3 が台帳では整数・点検では文字で一致しない→鍵の形を固定し k3 を整数で比べる。MEDIUM-2 ADR-1034 の PO 記録の定義と食い違う→ADR-1034 What 4・受け入れたリスクを改める。LOW-1 `po-apply-` の部分一致→先頭一致の3つに絞る。LOW-2 A20 の反例を追加。LOW-3 自動作業の時刻を recon に根拠付きで記録、記録が消えたときは B に倒す。
