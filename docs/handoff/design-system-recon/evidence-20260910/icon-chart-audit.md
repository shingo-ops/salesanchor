# アイコン・グラフの読み取り照合

報告元: /root/frontend_definition_audit。設計担当が受領した報告の転記であり、独立した設計審査ではない。製品変更なし。
基準: 設計HEAD 6e1335725bb8dfdf390125c4caf5a93f705f4821。設計担当による最新main照合23413b10f29228ffce7c7bf0813649b1910cf6bbまでfrontend差分0。

- constants/iconSizes.ts:9 と tokens.css:214以降は14/16/20/24/48の5値を二重定義。
- constants/icons.tsx:22の通常size型はnumber|string。:97の変換関数は既定24をwidth/heightへ渡す。
- icons.tsx:312のPlatformIconはsize?:number、:317以降で0.7/0.70/0.80/0.72を掛けMath.roundする。pages/inbox/InboxConversationList.tsx:219がICON.baseを渡す。CSS変数文字列への一括変更は数値互換を維持できない。
- icons.tsx:407のLeadChatIconもsize?:number、既定20。IconSize型の定義以外の参照は検索で0。
- ICONの5キーは全TS/TSXの文字列検索で109個/25ファイル。テスト・stories・design-preview・design-system除外では76個/21ファイル。コメント込み、JSX使用数ではない。
- heroicons/phosphor/lucideの直接import全文検索ではheroiconsの2importのみ、icons.tsx:60,91。eslint.config.js:120はlucide-reactだけを禁止しheroiconsは対象外。
- DashboardPage.tsx:172のgetChartColorsはhtmlの--accentを取得。:175に固定色fallback、:176に文字列40付加。:708,717のBar.fillで使用。
- index.css:27/221のaccentはlight #1e3a8a、dark #5b8dd9。現状6桁hexだが取得APIの形式検証はない。
- ThemeContext.tsx:54/95はforce-darkとstateを更新。DashboardはuseThemeを購読せず、getChartColorsはDashboard描画時のみ呼ばれる。実際の切替表示は未検証。
- DashboardPage.tsx:675,682のtick.fillはvar(--text-secondary)。このコードの存在だけでRechartsの全CSS色形式の対応を保証しない。

担当が実行したチェック（設計担当による本ターン再実行ではない）:
- node scripts/check-icon-sync.js: 5サイズ同期、成功。
- node scripts/check-color-token-sync.js: 37色トークン掲載、成功。
- node scripts/check-sidebar-outline.js: NAV_ICONS 22項目+LeadChatIcon、成功。

限界: icon-syncは数値比較のみ、color-token-syncは限定prefixの名前掲載検査。生成物の正しさ・全色のSSOT・グラフのテーマ反映は証明しない。
未確認: Rechartsの公式仕様と実表示、生成器のCSS構文/単位/失敗時契約、実行タイミング、画像内側の比率の表示互換。
