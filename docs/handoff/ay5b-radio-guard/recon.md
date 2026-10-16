# AY-5b recon: 生ラジオの見張りを UI governance gate に足す

- 作成: 2026-10-16 Opus / 基点 origin/main 96e415ccc（AY-5 #4365 マージ後）
- 調査は Sonnet。生出力は /tmp/CC報告ファイル/ssot-radio/ay5b/（00〜06）

## 既存 ADR 検索

- ui-governance の ADR は ADR-144 だけ（AY-4d recon と同じ。docs/handoff/ay4d-checkbox-guard/recon.md）。
- docs/adr/ADR-144-ui-component-governance.md:130 以降「2026-10-16 追記: 生チェック欄を種別に追加（AY-4d）」。そこには「生 radio は対象外」と書いてある。今回はこの対象外を外し、種別を 4 から 5 にする。
- docs/specs/design-system/design.md:4257 §AY-5 の :4264 と :4265 に「AY-5b として別に提案」とある。

## 現在地

- scripts/check-ui-governance.js:8-12 冒頭コメントは「検出対象（4種）」。
- scripts/check-ui-governance.js:244-245 isCheckboxInput、:251-260 countCheckbox（extractInputTags :175 で input タグを取り出し、ui-allow を除く）。
- scripts/check-ui-governance.js:313-320 countAll、:355-360 typeLabels、:362 比較の種別の並び `['select', 'input', 'tab', 'checkbox']`、:419-429 export。radio の関数は無い。
- scripts/tests/test-ui-governance.js は 31 件で全部通る（02b-test-run.txt）。:249-253 の T26 は countCheckbox が type="radio" を数えないことの試験。radio の試験は無い。
- 生ラジオの今の数（03a・03b）: frontend/src/pages/ の .tsx は 0 件。frontend/src の .tsx は 4 件。内訳は金型本体 3 件（components/Radio.tsx:49、components/RadioControl.tsx:14、components/ChoiceCardGroup.tsx:39）と試験 1 件（components/CheckboxControl.test.tsx:70）。関所は pages/ しか見ないので、関所を足しても今ある PR は赤にならない。
- docs/CC_UI_GOVERNANCE.md:25 の禁止表に checkbox の行がある。:30 に「生 radio も使わない（CI ではまだ止まらない。AY-5b で提案）」の注記がある。
- 種別の列挙が古い箇所: .github/workflows/ui-governance-gate.yml:3-4、docs/BRANCH_PROTECTION_SETUP.md:314、CLAUDE.md:119。いずれも AY-4d の時点で checkbox が無く、ADR-144 追記に「今回は触らない」と記録済み。

## 未確認

- なし（CI 上の BASE/HEAD の実走は PR の CI で確かめる）。
