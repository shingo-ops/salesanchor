本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

# CARD-LINE-STOCK-SAVE-01

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、03-file.md、04-worktree.md、05-pr.md、10-executor.md、11-lint.md。
照合結果: 実在する専用作業台を指定。新しい作業台の作成・自動回収・PR操作は含めない。実装内容はdesign §15の第1便に固定。コマンドは各手順のcd接頭辞から実行する。

担当: POがこのカードを渡した実装役。設計担当自身は実行しない。受領確認としてカードID・作業台・4ファイルの範囲を最初に返す。
目的: 根拠のない抽出値を拒否し、「①」を1と保持し、「10→残3」を103へ変換しない部品を作る。
設計審査: 同一AIによる第1便限定APPROVE（design §11）。全体設計も自己審査APPROVEだが、本カードの実装許可は第1便だけ。実装移行のPO原文記録はdesign §15。マージ/本番GOではない。
作業台: /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-contract
ブランチ: release/line-stock-contract
このカードを引き渡す時点で設計担当は編集を終了する。受領者が正規にこの作業台を利用できる場合だけ続行する。所有制御の拒否を解除しない。

許可: 検収済み以下4ファイルの同一内容コピーと検証、指定4ファイルだけのコミット、同ファイルの部品試験、読み取り調査。実装は手順4で指定する範囲に限り、実装方法の選択は設計契約内で行う。
変更ファイル: backend/app/services/tcg_stock_evidence.py、backend/app/services/tcg_stock_quantity.py、backend/tests/stock_contract/test_stock_evidence.py、backend/tests/stock_contract/test_stock_quantity.py。
禁止: 既存製品コード・設定・依存・DB・migration・CI・scripts・secretsの編集、既存呼出元への接続、外部AI/Sheets/本番アクセス、文書/台帳/GO記録の編集、push/PR/マージ、サブエージェント起動。他者の変更を戻さない。

手順1: 必須preflight
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-contract && ./scripts/dev/executor-preflight.sh
    期待する出力: PREFLIGHT OK。成功した場合のみ次へ。

手順2: 状態確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-contract && git status --short --branch
    期待する出力: release/line-stock-contractで未保存変更0。親の文書commit後に開始する。

手順3: 正式設計の内容一致を確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-contract && shasum -a 256 docs/handoff/tcg-import-latest-only/design.md
    期待する出力: 2b72ecd0a7425d026c82a09e58c5c43db81e7476b0aaf15846ab6fc091f7472f。一致した場合のみ次へ。

手順4: 同内容コピー。編集は禁止。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-contract && python3 - <<'COPY'
from pathlib import Path
import hashlib,json
src=Path('/Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design')
r=Path.cwd()
files=json.loads((r/'docs/handoff/tcg-import-latest-only/probe-20260913.json').read_text())['stage1_component_review']['files_sha256']
expected={'backend/app/services/tcg_stock_evidence.py','backend/app/services/tcg_stock_quantity.py','backend/tests/stock_contract/test_stock_evidence.py','backend/tests/stock_contract/test_stock_quantity.py'}
assert set(files)==expected
for name,digest in files.items():
    assert not (r/name).exists(),name
    assert hashlib.sha256((src/name).read_bytes()).hexdigest()==digest,name
for name,digest in files.items():
    p=r/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((src/name).read_bytes())
    assert hashlib.sha256(p.read_bytes()).hexdigest()==digest,name
    assert all(line==line.rstrip() for line in p.read_text().splitlines()),name
print('4/4 copied, hash and whitespace matched')
COPY
    期待する出力: 4/4 copied, hash and whitespace matched。元の4ファイルも他者の変更も戻さない。

手順5: 部品テスト
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-contract/backend && python3.12 -m unittest discover -s tests/stock_contract -p 'test_*.py' -v
    期待する出力: 0件収集でなく、両モジュールの6試験群が収集され全成功。全backend試験やAI精度の合格とは報告しない。

手順6: 新規部品の型検査
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-contract/backend && /private/tmp/line-stock-check-py312/bin/mypy --cache-dir /private/tmp/line-stock-worker-mypy app/services/tcg_stock_evidence.py app/services/tcg_stock_quantity.py
    期待する出力: 新規2モジュールの型エラー0。親がPython3.12の隔離環境に既存固定版を用意する。実在しない場合は停止。
    全体make lint-ciは手順9で実行する。前便の失敗を成功へ読み替えない。

手順7: 差分形式
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-contract && git diff --check
    期待する出力: 既存の追跡済みファイルの差分エラー0。本コマンドだけで新規4ファイルを検査済みとしない。

手順8: 範囲検査
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-contract && git status --short --untracked-files=all
    期待する出力: 指定4ファイルだけが新規。その他の差分0。成功した場合のみ次の保存手順へ。

失敗・不明・契約矛盾・権限拒否があれば該当操作で停止し、コマンドと生出力全文を返す。許可の自己発行やチェック変更で回避しない。
報告: CARD ID、実際のブランチとHEAD、変更4ファイル全文、各検証のコマンド/生出力、未実施の検証を区別する。商品A〆でB維持、日付表示、実PG、UI、3シート配信はこのカードでは未検証と明記する。

手順9: 必須静的検査
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-contract/backend && PATH=/private/tmp/line-stock-check-py312/bin:$PATH RUFF_CACHE_DIR=/private/tmp/line-stock-save-ruff MYPY_CACHE_DIR=/private/tmp/line-stock-save-full-mypy make lint-ci > /private/tmp/line-stock-save-lint.log 2>&1
    期待する出力: exit0。ログ全文を親へ返す。mypy警告とBandit内部エラーを隠さない。
手順10: ステージ
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-contract && git add backend/app/services/tcg_stock_evidence.py backend/app/services/tcg_stock_quantity.py backend/tests/stock_contract/test_stock_evidence.py backend/tests/stock_contract/test_stock_quantity.py
    期待する出力: exit0。
手順11: 差分形式
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-contract && git diff --cached --check
    期待する出力: 指摘0。
手順12: 保存
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-contract && git commit -m 'feat: add source-grounded stock evidence and quantity components'
    期待する出力: 4ファイルだけのcommit成功。
手順13: 実在検算
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-contract && git log -1 --format=fuller --stat
    期待する出力: 実SHAと4ファイル。ここで停止して親へ返す。push/PRは次カード。
END OF CARD
