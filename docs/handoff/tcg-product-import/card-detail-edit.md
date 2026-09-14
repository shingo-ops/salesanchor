# CARD-DETAIL-01

読んだ節: design-partner.md §5.5、STANDARD-WORKFLOW §1〜§6、ADR-113 handoff、guards/11-lint.md L01〜L33。
受領確認: 本カードはCARD-DETAIL-01であり、末尾END OF CARDまで受領したことを確認する。
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
許可: design.mdのDETAIL-01契約に記載したファイルと台帳の実装・試験・記録、公式PR手順。
禁止: migration/運用/CI/secrets/認可変更、GOの創作、検問回避、他者の変更の上書き。
PO原文: 「離席するのでPRマージして本番デプロイまで完了させてくれ」。番号付きの承認文へ言い換えない。

照合1○ 記号はコード書式。2○ PRはready。3○ 完了報告に生出力全文。4○ 商品詳細編集1目的。
照合5○ 専用作業台作成済み。6○ 帳票パスは平打ち。7○ 合格は受入D1〜D7の試験結果で判定。
L32人手照合: 未確定の目印なし。設計のAPPROVEは自己審査、独立した第二者レビューではない。

手順1 作業状態確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-product-master-detail-edit && git status --short --branch
期待する出力: release/product-master-detail-edit。既存の本便設計文書以外の変更は記録し範囲を確認する。

手順2 実装
    design.mdのDETAIL-01 API・データ契約と画面契約を忠実に実装する。
    対象ファイルは同節の一覧、商品データ本体と語と監査の原子性を維持する。
    既存CSV取込・作品タブ・発売日順・ページング・認可の回帰を検証する。

手順3 検証
    cd /Users/tanizawashingo/worktrees/salesanchor/release-product-master-detail-edit/frontend && npm run build
    cd /Users/tanizawashingo/worktrees/salesanchor/release-product-master-detail-edit/frontend && npm run check:all
    Dockerが無いローカルではpytestを実行しない。実PGは既存CIで検証する。
    画面試験でD1〜D6、実PGでD4/D6/D7を確認し、失敗は製品修正して再検証する。

手順4 正式PR・本番反映
    検証後、公式のPR作成・マージ手順で本便を提出する。PRはreadyとして作成する。
    マージ直前はHEADとCIと承認記録を照合し、検査が承認を認めない場合は停止する。
    commit/push前後はgit logで収録コミットと対象ファイルを照合する。
    gh-pr-merge-safe.shの生出力全文を完了報告に残す。
    成功時は通常のデプロイ結果と配布資産/healthを確認する。本番商品を書き換える試験はしない。

報告: 本報告はカードCARD-DETAIL-01の実行結果である。実行した検証とCI報告を分けて記録する。
停止時: 停止した手順番号、最後に実行したコマンド、停止した理由をPOへの完了報告に生出力全文で残す。
状態: 設計/自己審査/実装/PR/マージ/デプロイを区別し、未実施を成功と称さない。

END OF CARD
