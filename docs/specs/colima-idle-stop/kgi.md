# KGI(○×で測る・数値化)

この文書は何か(専門用語なしの1行): このテーマの合格条件を、○×で判定できる数字にした一覧。

親: [README.md](./README.md)

正本は [design.md §1・§4](../../handoff/colima-idle-stop/design.md)。本表はその合格条件を PO が判定できる形で並べたもの。食い違えば design.md を直してから本表を合わせる。

| # | 合格条件 | 測り方 | 合格ライン | 結果 |
|---|---|---|---|---|
| K1 | 自動試験がすべて通る | `bash scripts/tests/test-colima-idle-stop.sh` | FAIL 0 | ○ PASS=42 FAIL=0（PR #4294） |
| K2 | 見回り役が 15 分ごとに登録されている | `plutil -lint` と `StartInterval` の値 | OK・900 | ○（PR #4294） |
| K3a | 設置した環境（launchd と同じ条件）で判定できる | plist と同じ環境変数で `--dry-run` | ログの reason が d（判定失敗）でない | ○ 2026-10-15（deploy/D2.txt） |
| K3 | 使われていない Docker が止まり、メモリが空く | 見回りの記録（状態ファイル）を「1900 秒前から未使用・今の ha.pid」に書き換えてから `launchctl kickstart` で見回りを1回起こし、ログと `colima status -p default` を見る（design.md §4 K3） | ログ `result=stop-ok`、`colima status` が停止を示す | ○ 2026-10-15（VM 0件、swap 4538M→2312M。証跡 /tmp/CC報告ファイル/ac-heavy/docker-idle/deploy/） |
| K4 | 止まった後、必要なときに戻せる | `colima start` の後に `docker ps` | salesanchor-postgres-1 が healthy | ○ 2026-10-15（同上） |
| K5 | 使っている最中は止めない | DB に接続したまま、状態ファイルを 1900 秒前にして見回りを1回起こす（design.md §4 K5） | ログ `result=busy`、Docker は動いたまま | ○ 2026-10-15（reason=c。同上） |
| K6 | 放っておけば、最後に使ってから 60 分以内に自然に止まる | ~/Library/Logs/colima-idle-stop.log で、未使用を初めて記録した行（`result=idle reason=- elapsed=0`）から `result=stop-ok` の行までの時間。見回りは 15 分ごとなので、最後に使った時刻はその行の最大 15 分前 | 45 分以内（＝最後の使用から 60 分以内） | ○ 2026-10-15（10:46:21 に未使用を初めて記録 → 11:16:37 に `result=stop-ok elapsed=1810`。約30分） |

KPI: 合格した KGI の数 ◯/7（2026-10-15 時点 7/7）。

30分と60分の関係: PO が y と答えた提案の「30分」は、未使用が続いた時間（判定の基準 1800 秒）。見回りは 15 分ごとなので、最後に使ってから実際に止まるまでは最大 60 分かかる（K6 の合格ラインはこちら）。
