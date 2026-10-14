# Design: 除外ワードの左境界

**対象ADR**: ADR-154
recon: docs/handoff/fix-exclude-keyword-boundary/recon.md

## 外部・過去事例の参照と我々への応用

| 事例 | 内容 | 応用 |
|---|---|---|
| 検索エンジンのストップワード／ブラックリスト照合 | 短いトークンは単語境界つきの照合にしないと語中に誤ヒットする（例: Lucene のトークン単位一致、正規表現の `\b`）。 | 同じ ar を検索ワード側は両側境界で守っている（`_value_hits`）。除外側にも短い語の境界を入れる。 |
| 本リポジトリ内の先行（検索ワード側の PR-3b） | 2文字以下・数字だけは境界つき（extraction_judgement_svc.py:57-59,201-215） | 同じ `_needs_boundary` を使い、定義を二重にしない。 |

## 変更（最小）
- backend/app/services/extraction_judgement_svc.py: `has_left_word_boundary` を追加（`has_word_boundary` と同じ「英字・数字」を境界の対象とし、左側だけ判定。出現位置のどれか1つで左が境界なら True）。`_excluded_keywords` の非 strict 経路で、`folded` があり `_needs_boundary(normalized)` のとき、`has_left_word_boundary` が False なら除外しない。
- 右側を条件にしない理由: 既存仕様「SR は SRR に当たる」（テスト 770-774）を保つため。
- 触らない: 検索ワード側、品番の strict 判定、`has_word_boundary` の挙動、マスタ、frontend。

## 挙動が変わる点
- 「SSR」と除外語「SR」: 修正前は SSR の中の sr に当たって除外、修正後は直前が s（語の途中）なので当たらない。テストで固定（test_ssr_no_longer_excluded_by_sr）。
- 同様に、短い除外語（2文字以下・数字だけ）が語の途中（直前が英字・数字）にしか現れない文では、除外されなくなる。影響行は impl/measure.py で全件列挙してからマージ判断する。
- 変わらない点: 3文字以上の除外語、strict の品番除外、語頭・単独・「ARカード」（直前が語頭）の除外。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 「25th ANNIVERSARY GOLDEN BOX」で除外語 AR に当たらない | test_ar_does_not_exclude_inside_anniversary（strict 有無の両方） |
| 「AR 100枚」「ARカード」「AR/CHR」で AR に当たる | test_ar_excludes_when_standalone / _before_kana / _in_slash_list |
| 「SRR」で SR に当たる（既存仕様） | test_strict_two_char_exclude_keeps_substring（無変更）・test_sr_excludes_srr_left_boundary_only |
| 「SSR」で SR に当たらない（変更点） | test_ssr_no_longer_excluded_by_sr |
| 修正前の origin/main で新テストが赤 | impl/red-origin-main.txt（2件失敗） |
| 既存の照合・解析テストが緑 | impl/green-after-fix.txt・impl/related-tests.txt |
| ruff が通る | impl/ruff.txt |
| 本番の影響行を全件列挙 | impl/measure.py（実行は Opus）・impl/measure-plan.md |

## 維持の仕組み
守り手: 追加テスト（backend CI の pytest）。追加テストが、AR/ANNIVERSARY・SR/SSR・SR/SRR の挙動を固定する。
