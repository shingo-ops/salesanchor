# 実装カード R1 — 送り先の住所の末尾の改行を受け口でも断る（PR 5718）

- 根拠: `docs/handoff/customer-form-layout/review-opus.md` の R1・`design.md` §3-1（`.fullmatch` に直した）・§2（改行は断る）・KGI K7
- ブランチ: `release/customer-form-pc-layout-impl`（PR 5718 の head）。新しいブランチは作らない

## 変える所（3か所だけ）

1. `backend/app/schemas/base.py` の `validate_delivery_address_line` の中
   - 前: `if not _DELIVERY_ADDRESS_LINE_RE.match(value):`
   - 後: `if not _DELIVERY_ADDRESS_LINE_RE.fullmatch(value):`
2. `backend/tests/test_delivery_address_rule.py` の `test_newline_rejected` の最後に2行足す
   ```python
       with pytest.raises(ValueError, match="address_line_non_ascii"):
           validate_delivery_address_line("abc\n")
   ```
3. `frontend/src/utils/addressRules.test.ts` の `it("改行は ascii", ...)` の中に1行足す
   ```ts
       expect(deliveryAddressLineError("abc\n")).toBe("addressRule.ascii");
   ```

## 触らない所

- 上の3か所以外のファイル・行は全部触らない。`addressRules.ts` は変えない（JS の `$` は末尾の改行に当たらないので今のままで断る）。

## 確かめ

- `cd backend && python -m pytest tests/test_delivery_address_rule.py -q` が全部通る（生出力を残す）
- `cd frontend && npx vitest run src/utils/addressRules.test.ts` が全部通る（生出力を残す）
- `git diff --stat origin/release/customer-form-pc-layout-impl` が上の3ファイルだけ

## 想定の分岐

- 試験が1つでも落ちたら直さずに止めて、生出力をそのまま報告する（BLOCKED）
- 行が見つからない・前の形と違う時も止めて報告する
