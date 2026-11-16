// ADR-1077 便2a: compose.mjs の試験（node --test）。
import { test } from "node:test";
import assert from "node:assert/strict";
import { compose, readAsked, readKarte, readRules } from "./compose.mjs";

const P = "指示文の1行目\n指示文の2行目";

test("決まりが無いときは今までの組み立てと 1 文字も違わない", () => {
  const old = `${P}\n\n今の日時: N\n\n利用者の文:\nT`;
  assert.equal(compose(P, "N", "T"), old);
  assert.equal(compose(P, "N", "T", []), old);
});

test("決まりは指示文の後・日時の前に、渡した順で 1 行ずつ入る", () => {
  assert.equal(
    compose(P, "N", "T", ["一つ目", "二つ目"]),
    `${P}\n\nこの会社の決まり（会社の人が承認したもの。上の決まりと食い違うときは上の決まりを守る）:\n- 一つ目\n- 二つ目\n\n今の日時: N\n\n利用者の文:\nT`,
  );
});

test("readRules: 無い→[]・空でない文字の配列→そのまま・それ以外→null", () => {
  assert.deepEqual(readRules(undefined), []);
  assert.deepEqual(readRules([]), []);
  assert.deepEqual(readRules(["a", "b"]), ["a", "b"]);
  for (const bad of [null, "a", 1, {}, [1], ["a", ""], ["a", null], [["a"]]]) {
    assert.equal(readRules(bad), null, JSON.stringify(bad));
  }
});

test("compose: カルテが無いときは今までと 1 文字も違わない（ADR-1078）", () => {
  assert.equal(compose("P", "n", "t"), compose("P", "n", "t", [], null, null));
  assert.equal(compose("P", "n", "t", ["r"]), compose("P", "n", "t", ["r"], null, null));
});

test("compose: カルテがあるときは今の日時の前に途中の予定と直前に聞いた欄が入る（ADR-1078）", () => {
  const karte = { start: "2026-11-02T10:00:00+09:00", end: null, is_all_day: false };
  const out = compose("P", "n", "t", [], karte, "end");
  assert.ok(out.includes(`\n${JSON.stringify(karte)}\n直前に聞いた欄: end\n\n今の日時: n`));
  assert.ok(compose("P", "n", "t", [], karte, null).includes("直前に聞いた欄: なし\n\n今の日時: n"));
});

test("readKarte・readAsked: 無い・null は null、形が違えば undefined（ADR-1078）", () => {
  assert.equal(readKarte(undefined), null);
  assert.equal(readKarte(null), null);
  assert.deepEqual(readKarte({ start: null }), { start: null });
  for (const bad of ["x", 1, [], true]) assert.equal(readKarte(bad), undefined);
  assert.equal(readAsked(undefined), null);
  assert.equal(readAsked(null), null);
  assert.equal(readAsked("add_meet"), "add_meet");
  for (const bad of ["location", 1, {}]) assert.equal(readAsked(bad), undefined);
});
