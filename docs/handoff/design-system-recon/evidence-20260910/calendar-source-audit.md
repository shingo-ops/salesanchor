# カレンダー色集約の実行条件（2026-09-10）

何の文書か: 次の色集約と今の検査規則が両立するかの確認記録。
親: [全体recon](../recon.md)。基準a5e5a250（PR3420マージ）。製品変更0、実装試験未実施。

| 観測事実 | 根拠 |
|---|---|
| 7分類×3属性=21固定値、異なる色20個。明暗とも固定値 | frontend/src/features/schedule/calendars.config.ts:19、calendar-source-audit.json |
| 表示4箇所、cssVar呼出8回、値の透過だけ | frontend/src/pages/schedule/SchedulePageImpl.tsx:212、645、715、798。calendars.config.ts:82 |
| 3色のAPI保存なし、categoryを保存 | frontend/src/pages/schedule/SchedulePageImpl.tsx:1020 |
| colorVarは定義外使用0。公開属性は削除しない | 全src検索、CalendarMeta。未使用7値もprobe必要 |
| 旧--cal-*42宣言は現在の色と異なる | frontend/src/tokens.css:381、548。単純接続は配色変更 |
| index.cssのhex増加をファイル単位で拒否 | scripts/check-design-token-ratchet.sh:50、68。tokens.cssだけ除外 |
| 色の正本はindex.css、tokens.cssは色以外 | docs/adr/ADR-067-design-token-enforcement.md:41、frontend/src/tokens.css:4 |

読み取り補助2担当の報告とrootによる実物確認を照合。20固有色のうち12色はindex.cssに存在しない（限定検査担当報告）。21用途を明暗に直定義する原案は42hex追加になり、configの削減では相殺されない。これは検査条件式からの判定で、製品を変更してCIを実行した結果ではない。旧calendar/design.mdのdark値・未定義blue-800参照も同値保持を満たさない。

判定: **REVISE（カレンダー便の実行契約）**。Planner確認後、同じAIがArchitectとして自己審査。独立した全体設計審査ではない。全体目標の撤回ではない。

CIの先行変更、除外追加、hex表記の変換による検査逃れ、不要色削除との相殺は採用しない。tokens.cssへ色を移す方法は正本の設計変更になるため、単に除外されているからとは判断しない。

推奨案（PO未決）: この色移管を保留し、既存トークンで実装できる共通部品を先行する。最後のCI設計で正本の検査契約と色移管を両立させる。順序合意を創作しない。

受入準備: 明暗×21=42解決値を固定期待値と比較、4描画箇所の背景/文字、id/順序/labelKey/primary保持。calendar専用test/specとcssVar/CALENDARSの試験参照は調査0。一般ナビ試験は色検証ではない。外部事例不要（自repoの保存先と検査の矛盾を解消する局所設計）。

記録作成時、最初の抽出は型interfaceを含めた正規表現で失敗し未保存。CALENDARS配列本文へ限定して再抽出し、7行/21属性/20固有値を確認した。未実施の製品試験を成功扱いしない。
