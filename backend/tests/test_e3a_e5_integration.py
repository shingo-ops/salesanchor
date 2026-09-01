"""
test_e3a_e5_integration.py

E3a + E5 統合テスト — 合成データによる動作検証。
本番 DB 不使用。Session を Mock してロジックのみを検証する。

GAS AnalysisV2UnitRecovery.gs / AnalysisV2ConditionRecalc.gs との
動作一致を確認する。

検証項目:
  E3a-1: 単位語終端マッチで回収 (box / ﾊﾟｯｸ / 箱 / BOX)
  E3a-2: A-2 除外 — japanese_title に単位語を含む → スキップ
  E3a-3: unit_resolved=True → スキップ
  E3a-4: raw_unit 非空 → スキップ
  E3a-5: pid_resolved=False → スキップ
  E3a-6: end-match 不一致 → スキップ (例: "boxセット" は box で終わらない)
  E3a-7: ケース special — "スーツケース" は非空白接頭 → スキップ
  E3a-8: 安全装置 101件 → aborted=True
  GAS-11: GAS 11件再現 (ﾊﾟｯｸ×6 / box×3 / BOX×1 / 箱×1)
  E5-1: R4:単位既定:単位不明 の行を再計算 → Sealed box / Searched pack
  E5-2: R4 以外の condition_basis は対象外
  E5-3: 安全装置 201件 → aborted=True
  GAS-E5: GAS 11件の E5 再計算で FLAG_SINGLE -11 / Sealed box +5 / Searched pack +6
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.tcg_unit_recovery_svc import (
    E3A_MAX_RECOVER,
    E5_MAX_ROWS,
    recalc_condition_from_recovered_unit,
    recover_unit_from_product_name,
)

# ---------------------------------------------------------------------------
# 共通ヘルパー
# ---------------------------------------------------------------------------

# E3a の session.execute().fetchall() が返す Row のフォーマット
# (ar_id, extraction_item_id, unit_resolved, pid_resolved, product_id,
#  raw_unit, raw_product_name, product_code, japanese_title)
_IDX = {
    "ar_id": 0, "ei_id": 1, "unit_resolved": 2, "pid_resolved": 3,
    "product_id": 4, "raw_unit": 5, "raw_product_name": 6,
    "product_code": 7, "japanese_title": 8,
}


def _row(
    ar_id: str = "1",
    ei_id: str = "ei-1",
    unit_resolved: bool = False,
    pid_resolved: bool = True,
    product_id: str | None = None,
    raw_unit: str = "",
    raw_product_name: str = "",
    product_code: str | None = None,
    japanese_title: str | None = None,
) -> tuple:
    return (ar_id, ei_id, unit_resolved, pid_resolved, product_id,
            raw_unit, raw_product_name, product_code, japanese_title)


def _session_for_e3a(rows: list[tuple]) -> MagicMock:
    """E3a 用 mock session: execute().fetchall() → rows"""
    s = MagicMock()
    s.execute.return_value.fetchall.return_value = rows
    return s


# E5 テスト用最小条件エントリ
# search_kw に "NEVERMATCHES" を置くことで main-loop をスルーさせ、
# R4b フォールバックのみを使う。_find_cond_id() は code で引く。
_FAKE_COND_ENTRIES = [
    {"cond_id": "cid-cn0001", "code": "CN0001", "canonical": "Case",
     "priority": 4, "app_kubun": "箱系大", "search_kw": "NEVERMATCHES", "exclude_kw": ""},
    {"cond_id": "cid-cn0003", "code": "CN0003", "canonical": "Sealed box",
     "priority": 4, "app_kubun": "箱系",   "search_kw": "NEVERMATCHES", "exclude_kw": ""},
    {"cond_id": "cid-cn0008", "code": "CN0008", "canonical": "FLAG_SINGLE",
     "priority": 4, "app_kubun": "",       "search_kw": "NEVERMATCHES", "exclude_kw": ""},
    {"cond_id": "cid-cn0010", "code": "CN0010", "canonical": "Searched pack",
     "priority": 5, "app_kubun": "パック系","search_kw": "NEVERMATCHES", "exclude_kw": ""},
]

# load_lookup_maps の返り値:
# (product_code_to_uuid, unit_alias_to_canonical, unit_canonical_to_uuid,
#  cond_alias_to_canonical, cond_canonical_to_uuid, unit_alias_to_info)
_FAKE_LOOKUP_MAPS = (
    {},   # product_code_to_uuid
    {},   # unit_alias_to_canonical
    {},   # unit_canonical_to_uuid
    {},   # cond_alias_to_canonical
    {     # cond_canonical_to_uuid
        "Case": "cid-cn0001",
        "Sealed box": "cid-cn0003",
        "FLAG_SINGLE": "cid-cn0008",
        "Searched pack": "cid-cn0010",
    },
    {},   # unit_alias_to_info
)


def _e5_session(ar_condition_rows: list[tuple]) -> MagicMock:
    """E5 用 mock session: condition_basis クエリの結果を返す"""
    s = MagicMock()
    s.execute.return_value.fetchall.return_value = ar_condition_rows
    return s


# E5 の condition_basis クエリが返す Row フォーマット:
# (id, condition_basis, condition_canonical, raw_state, raw_product_name)
def _cond_row(
    ar_id: str,
    condition_basis: str = "R4:単位既定:単位不明",
    condition_canonical: str = "FLAG_SINGLE",
    raw_state: str = "",
    raw_product_name: str = "",
) -> tuple:
    return (ar_id, condition_basis, condition_canonical, raw_state, raw_product_name)


# ---------------------------------------------------------------------------
# E3a 単体検証
# ---------------------------------------------------------------------------


class TestE3aRecovery:
    """E3a-1: 各単位語で回収できること"""

    def test_box_lowercase(self):
        """'OP-01 box' → term='box', canonical='Box'"""
        s = _session_for_e3a([_row(raw_product_name="OP-01 box")])
        result = recover_unit_from_product_name(s, "tenant_004")
        assert result["success"] is True
        assert result["updated_count"] == 1
        d = result["details"][0]
        assert d["term"] == "box"
        assert d["canonical"] == "Box"
        assert d["unit_basis"] == "NAME_RECOVERY:box"

    def test_pack_halfwidth_katakana(self):
        """'スカーレット＆バイオレット ﾊﾟｯｸ' → term='ﾊﾟｯｸ', canonical='Pack'"""
        s = _session_for_e3a([_row(raw_product_name="スカーレット＆バイオレット ﾊﾟｯｸ")])
        result = recover_unit_from_product_name(s, "tenant_004")
        assert result["success"] is True
        assert result["updated_count"] == 1
        d = result["details"][0]
        assert d["term"] == "ﾊﾟｯｸ"
        assert d["canonical"] == "Pack"
        assert d["unit_basis"] == "NAME_RECOVERY:ﾊﾟｯｸ"

    def test_hako_kanji(self):
        """
        '白箱' → term='箱', canonical='Box'
        注: 'パック 箱' は find_term が 'パック' を先に見つけ end-match 失敗になるため
        '箱' のみを含む商品名を使う（GAS 準拠の正しい動作）
        """
        s = _session_for_e3a([_row(raw_product_name="白箱")])
        result = recover_unit_from_product_name(s, "tenant_004")
        assert result["success"] is True
        assert result["updated_count"] == 1
        d = result["details"][0]
        assert d["term"] == "箱"
        assert d["canonical"] == "Box"

    def test_BOX_uppercase(self):
        """'30th CELEBRATION BOX' → term='BOX', canonical='Box'"""
        s = _session_for_e3a([_row(
            raw_product_name="30th CELEBRATION BOX",
            japanese_title="30th CELEBRATION",  # A-2 除外されない
        )])
        result = recover_unit_from_product_name(s, "tenant_004")
        assert result["success"] is True
        assert result["updated_count"] == 1
        d = result["details"][0]
        assert d["term"] == "BOX"
        assert d["canonical"] == "Box"

    def test_carton_katakana(self):
        """'テスト カートン' → canonical='Case' (カートンはCaseのエイリアス)"""
        s = _session_for_e3a([_row(raw_product_name="テスト カートン")])
        result = recover_unit_from_product_name(s, "tenant_004")
        assert result["success"] is True
        assert result["updated_count"] == 1
        assert result["details"][0]["canonical"] == "Case"


class TestE3aExclusions:
    """E3a-2〜7: 各除外ルール"""

    def test_a2_exclusion_japanese_title_contains_term(self):
        """
        A-2 除外: japanese_title に 'BOX' → スキップ (PM0264 再現)
        GAS: AnalysisV2UnitRecovery.gs:230-237
        """
        s = _session_for_e3a([_row(
            raw_product_name="FUTURISTIC BOX",
            product_id="prod-pm0264",
            japanese_title="FUTURISTIC BOX",  # 'BOX' を含む → A-2 除外
        )])
        result = recover_unit_from_product_name(s, "tenant_004")
        assert result["success"] is True
        assert result["updated_count"] == 0  # 除外されて0件

    def test_a2_exclusion_halfwidth_in_title(self):
        """A-2: japanese_title に ﾊﾟｯｸ (NFKC→パック) → 'パック' 含む → 除外"""
        s = _session_for_e3a([_row(
            raw_product_name="テスト ﾊﾟｯｸ",
            product_id="prod-1",
            japanese_title="テストパック商品",  # NFKC 正規化後 'パック' を含む
        )])
        result = recover_unit_from_product_name(s, "tenant_004")
        assert result["success"] is True
        assert result["updated_count"] == 0

    def test_unit_resolved_true_skipped(self):
        """E3a-3: unit_resolved=True → スキップ"""
        s = _session_for_e3a([_row(unit_resolved=True, raw_product_name="テスト box")])
        result = recover_unit_from_product_name(s, "tenant_004")
        assert result["updated_count"] == 0

    def test_raw_unit_nonempty_skipped(self):
        """E3a-4: raw_unit≠'' → スキップ"""
        s = _session_for_e3a([_row(raw_unit="パック", raw_product_name="テスト box")])
        result = recover_unit_from_product_name(s, "tenant_004")
        assert result["updated_count"] == 0

    def test_pid_not_resolved_skipped(self):
        """E3a-5: pid_resolved=False → スキップ"""
        s = _session_for_e3a([_row(pid_resolved=False, raw_product_name="テスト box")])
        result = recover_unit_from_product_name(s, "tenant_004")
        assert result["updated_count"] == 0

    def test_end_match_fail_skipped(self):
        """
        E3a-6: 'box' が末尾でない → スキップ
        GAS: AnalysisV2UnitRecovery.gs:218-220
        """
        s = _session_for_e3a([_row(raw_product_name="boxセット")])
        result = recover_unit_from_product_name(s, "tenant_004")
        # 'セット' が末尾 → 'box' は末尾ではない → スキップ
        # ただし 'セット' が別 term として match する可能性があるので term を確認
        for d in result.get("details", []):
            assert d["term"] != "box", "box は末尾でないため回収されてはいけない"

    def test_case_special_suitcase_skipped(self):
        """
        E3a-7: 'スーツケース' → 'ツ' が 'ケース' 直前 → 空白なし → スキップ
        GAS: AnalysisV2UnitRecovery.gs:224-227
        """
        s = _session_for_e3a([_row(raw_product_name="スーツケース")])
        result = recover_unit_from_product_name(s, "tenant_004")
        case_hits = [d for d in result.get("details", []) if d["canonical"] == "Case"]
        assert len(case_hits) == 0, "スーツケースはケース special で除外される"

    def test_case_with_space_before_matched(self):
        """'テスト ケース' → 直前が空白 → 回収される"""
        s = _session_for_e3a([_row(raw_product_name="テスト ケース")])
        result = recover_unit_from_product_name(s, "tenant_004")
        assert result["updated_count"] == 1
        assert result["details"][0]["canonical"] == "Case"

    def test_empty_product_name_skipped(self):
        """商品名なし → スキップ"""
        s = _session_for_e3a([_row(raw_product_name="")])
        result = recover_unit_from_product_name(s, "tenant_004")
        assert result["updated_count"] == 0


class TestE3aSafetyLimit:
    """E3a-8: 101件で中止"""

    def test_101_rows_abort(self):
        """101件回収可能 → aborted=True, updated_count=0"""
        rows = [
            _row(ar_id=str(i), raw_product_name=f"テスト{i} box")
            for i in range(E3A_MAX_RECOVER + 1)  # 101件
        ]
        s = _session_for_e3a(rows)
        result = recover_unit_from_product_name(s, "tenant_004")
        assert result["success"] is False
        assert result["aborted"] is True
        assert result["updated_count"] == 0
        assert "Safety abort" in result["message"]

    def test_100_rows_ok(self):
        """100件回収可能 → 正常 (limit=100 は OK)"""
        rows = [
            _row(ar_id=str(i), raw_product_name=f"テスト{i} box")
            for i in range(E3A_MAX_RECOVER)  # ちょうど 100件
        ]
        s = _session_for_e3a(rows)
        result = recover_unit_from_product_name(s, "tenant_004")
        assert result["success"] is True
        assert result["aborted"] is False
        assert result["updated_count"] == E3A_MAX_RECOVER


# ---------------------------------------------------------------------------
# GAS 11件再現
# ---------------------------------------------------------------------------


class TestGAS11CaseReproduction:
    """
    GAS 実測 11件の完全再現。
    ﾊﾟｯｸ×6 / box×3 / BOX×1 / 箱×1
    PM0264 (japanese_title='FUTURISTIC BOX') は A-2 で除外。
    """

    @pytest.fixture()
    def gas_11_rows(self) -> list[tuple]:
        """GAS の 11件に対応する合成 extraction_items 行"""
        rows = []
        # ﾊﾟｯｸ×6 — パック系商品, japanese_title には ﾊﾟｯｸ/パックなし
        for i in range(6):
            rows.append(_row(
                ar_id=f"pack-{i}",
                raw_product_name=f"スカーレット＆バイオレット No.{i+1} ﾊﾟｯｸ",
                product_id=f"prod-pack-{i}",
                japanese_title=f"スカーレット＆バイオレット No.{i+1}",  # パックなし
            ))
        # box×3 — 小文字 box, japanese_title には box/箱なし
        for i in range(3):
            rows.append(_row(
                ar_id=f"box-{i}",
                raw_product_name=f"OP-{i+1:02d} box",
                product_id=f"prod-box-{i}",
                japanese_title=f"ワンピースカードゲーム OP-{i+1:02d}",
            ))
        # BOX×1 — PM0263 (30th CELEBRATION), japanese_title に BOX なし
        rows.append(_row(
            ar_id="box-pm0263",
            raw_product_name="ポケモンカード 30th CELEBRATION BOX",
            product_code="PM0263",
            product_id="prod-pm0263",
            japanese_title="30th CELEBRATION",  # BOX を含まない → A-2 非除外
        ))
        # 箱×1
        rows.append(_row(
            ar_id="hako-1",
            raw_product_name="シャドウバース 白箱",
            product_id="prod-hako-1",
            japanese_title="シャドウバース カードパック",  # 箱なし
        ))
        return rows

    @pytest.fixture()
    def gas_11_with_pm0264(self, gas_11_rows) -> list[tuple]:
        """PM0264 (FUTURISTIC BOX) を追加した 12件セット — A-2 除外テスト用"""
        return gas_11_rows + [
            _row(
                ar_id="box-pm0264",
                raw_product_name="FUTURISTIC BOX",
                product_code="PM0264",
                product_id="prod-pm0264",
                japanese_title="FUTURISTIC BOX",  # BOX を含む → A-2 除外
            )
        ]

    def test_11_rows_recovered(self, gas_11_rows):
        """GAS 11件入力 → E3a で 11件回収"""
        s = _session_for_e3a(gas_11_rows)
        result = recover_unit_from_product_name(s, "tenant_004")
        assert result["success"] is True
        assert result["updated_count"] == 11

    def test_term_distribution(self, gas_11_rows):
        """回収内訳: ﾊﾟｯｸ:6 / box:3 / BOX:1 / 箱:1"""
        s = _session_for_e3a(gas_11_rows)
        result = recover_unit_from_product_name(s, "tenant_004")
        by_term: dict[str, int] = {}
        for d in result["details"]:
            by_term[d["term"]] = by_term.get(d["term"], 0) + 1
        assert by_term.get("ﾊﾟｯｸ") == 6, f"ﾊﾟｯｸ expected 6, got {by_term}"
        assert by_term.get("box") == 3,  f"box expected 3, got {by_term}"
        assert by_term.get("BOX") == 1,  f"BOX expected 1, got {by_term}"
        assert by_term.get("箱") == 1,   f"箱 expected 1, got {by_term}"

    def test_pm0264_a2_exclusion(self, gas_11_with_pm0264):
        """12件入力 (PM0264含む) → PM0264 は A-2 除外 → 回収 11件"""
        s = _session_for_e3a(gas_11_with_pm0264)
        result = recover_unit_from_product_name(s, "tenant_004")
        assert result["updated_count"] == 11
        recovered_ids = {d["ar_id"] for d in result["details"]}
        assert "box-pm0264" not in recovered_ids, "PM0264 は除外されなければならない"

    def test_all_canonical_box_or_pack(self, gas_11_rows):
        """回収された全行の canonical が Box または Pack"""
        s = _session_for_e3a(gas_11_rows)
        result = recover_unit_from_product_name(s, "tenant_004")
        for d in result["details"]:
            assert d["canonical"] in ("Box", "Pack"), (
                f"ar_id={d['ar_id']} canonical={d['canonical']} は想定外"
            )


# ---------------------------------------------------------------------------
# E5 統合テスト
# ---------------------------------------------------------------------------


class TestE5Integration:
    """E5-1〜3: condition 再計算の検証"""

    @patch("app.services.tcg_unit_recovery_svc.load_lookup_maps",
           return_value=_FAKE_LOOKUP_MAPS)
    @patch("app.services.tcg_unit_recovery_svc.load_condition_entries",
           return_value=_FAKE_COND_ENTRIES)
    def test_box_kubun_recalc_to_sealed_box(self, mock_cond, mock_maps):
        """
        E5-1: kubun='箱系' (Box 回収) + R4:単位既定:単位不明 → Sealed box
        """
        e3a_details = [{
            "ar_id": "1", "extraction_item_id": "ei-1",
            "product_name": "テスト box", "product_code": "",
            "term": "box", "unit_id": "UN0002",
            "canonical": "Box", "kubun": "箱系",
            "unit_basis": "NAME_RECOVERY:box",
        }]
        cond_rows = [_cond_row("1", "R4:単位既定:単位不明", "FLAG_SINGLE")]
        s = _e5_session(cond_rows)

        result = recalc_condition_from_recovered_unit(e3a_details, s, "tenant_004")

        assert result["success"] is True
        assert result["target_count"] == 1
        assert result["changed_count"] == 1
        change = result["changes"][0]
        assert change["old_condition"] == "FLAG_SINGLE"
        assert change["new_condition"] == "Sealed box"

    @patch("app.services.tcg_unit_recovery_svc.load_lookup_maps",
           return_value=_FAKE_LOOKUP_MAPS)
    @patch("app.services.tcg_unit_recovery_svc.load_condition_entries",
           return_value=_FAKE_COND_ENTRIES)
    def test_pack_kubun_recalc_to_searched_pack(self, mock_cond, mock_maps):
        """
        E5-1: kubun='パック系' (ﾊﾟｯｸ 回収) + R4:単位既定:単位不明 → Searched pack
        GAS: R5:パック既定
        """
        e3a_details = [{
            "ar_id": "2", "extraction_item_id": "ei-2",
            "product_name": "テスト ﾊﾟｯｸ", "product_code": "",
            "term": "ﾊﾟｯｸ", "unit_id": "UN0003",
            "canonical": "Pack", "kubun": "パック系",
            "unit_basis": "NAME_RECOVERY:ﾊﾟｯｸ",
        }]
        cond_rows = [_cond_row("2", "R4:単位既定:単位不明", "FLAG_SINGLE")]
        s = _e5_session(cond_rows)

        result = recalc_condition_from_recovered_unit(e3a_details, s, "tenant_004")

        assert result["success"] is True
        assert result["changed_count"] == 1
        change = result["changes"][0]
        assert change["new_condition"] == "Searched pack"

    @patch("app.services.tcg_unit_recovery_svc.load_lookup_maps",
           return_value=_FAKE_LOOKUP_MAPS)
    @patch("app.services.tcg_unit_recovery_svc.load_condition_entries",
           return_value=_FAKE_COND_ENTRIES)
    def test_non_r4_basis_skipped(self, mock_cond, mock_maps):
        """
        E5-2: condition_basis が R4:単位既定:単位不明 以外 → 対象外
        GAS: condRecalcCollectTargets_ は R4 専用
        """
        e3a_details = [{
            "ar_id": "3", "extraction_item_id": "ei-3",
            "product_name": "テスト box", "product_code": "",
            "term": "box", "unit_id": "UN0002",
            "canonical": "Box", "kubun": "箱系",
            "unit_basis": "NAME_RECOVERY:box",
        }]
        # R1 basis → 対象外
        cond_rows = [_cond_row("3", "R1:単品語", "FLAG_SINGLE")]
        s = _e5_session(cond_rows)

        result = recalc_condition_from_recovered_unit(e3a_details, s, "tenant_004")

        assert result["target_count"] == 0
        assert result["changed_count"] == 0

    @patch("app.services.tcg_unit_recovery_svc.load_lookup_maps",
           return_value=_FAKE_LOOKUP_MAPS)
    @patch("app.services.tcg_unit_recovery_svc.load_condition_entries",
           return_value=_FAKE_COND_ENTRIES)
    def test_e5_safety_limit_201_rows(self, mock_cond, mock_maps):
        """E5-3: 201件対象 → aborted=True"""
        n = E5_MAX_ROWS + 1  # 201
        e3a_details = [
            {
                "ar_id": str(i), "extraction_item_id": f"ei-{i}",
                "product_name": f"テスト{i} box", "product_code": "",
                "term": "box", "unit_id": "UN0002",
                "canonical": "Box", "kubun": "箱系",
                "unit_basis": "NAME_RECOVERY:box",
            }
            for i in range(n)
        ]
        cond_rows = [
            _cond_row(str(i), "R4:単位既定:単位不明", "FLAG_SINGLE")
            for i in range(n)
        ]
        s = _e5_session(cond_rows)

        result = recalc_condition_from_recovered_unit(e3a_details, s, "tenant_004")

        assert result["success"] is False
        assert result["aborted"] is True
        assert result["changed_count"] == 0

    def test_empty_e3a_details(self):
        """E3a 結果が空なら E5 は即 success / 変更なし"""
        s = MagicMock()
        result = recalc_condition_from_recovered_unit([], s, "tenant_004")
        assert result["success"] is True
        assert result["target_count"] == 0
        assert result["changed_count"] == 0
        s.execute.assert_not_called()


# ---------------------------------------------------------------------------
# GAS 11件 E3a+E5 エンドツーエンド
# ---------------------------------------------------------------------------


class TestGAS11EndToEnd:
    """
    GAS 11件シナリオの E3a + E5 連鎖実行。
    E3a: ﾊﾟｯｸ×6 (パック系) + box×3 + BOX×1 + 箱×1 (箱系) = 11件
    E5 期待結果:
      FLAG_SINGLE -11 / Sealed box +5 (box3+BOX1+箱1) / Searched pack +6 (ﾊﾟｯｸ6)
    """

    @pytest.fixture()
    def e3a_details_11(self) -> list[dict]:
        details = []
        for i in range(6):
            details.append({
                "ar_id": f"pack-{i}", "extraction_item_id": f"ei-pack-{i}",
                "product_name": f"スカーレット No.{i+1} ﾊﾟｯｸ",
                "product_code": "", "term": "ﾊﾟｯｸ", "unit_id": "UN0003",
                "canonical": "Pack", "kubun": "パック系",
                "unit_basis": "NAME_RECOVERY:ﾊﾟｯｸ",
            })
        for i in range(3):
            details.append({
                "ar_id": f"box-{i}", "extraction_item_id": f"ei-box-{i}",
                "product_name": f"OP-{i+1:02d} box",
                "product_code": "", "term": "box", "unit_id": "UN0002",
                "canonical": "Box", "kubun": "箱系",
                "unit_basis": "NAME_RECOVERY:box",
            })
        details.append({
            "ar_id": "pm0263", "extraction_item_id": "ei-pm0263",
            "product_name": "ポケモンカード 30th CELEBRATION BOX",
            "product_code": "PM0263", "term": "BOX", "unit_id": "UN0002",
            "canonical": "Box", "kubun": "箱系",
            "unit_basis": "NAME_RECOVERY:BOX",
        })
        details.append({
            "ar_id": "hako-1", "extraction_item_id": "ei-hako-1",
            "product_name": "シャドウバース 白箱",
            "product_code": "", "term": "箱", "unit_id": "UN0002",
            "canonical": "Box", "kubun": "箱系",
            "unit_basis": "NAME_RECOVERY:箱",
        })
        return details

    @pytest.fixture()
    def e5_cond_rows_all_r4(self, e3a_details_11) -> list[tuple]:
        return [
            _cond_row(d["ar_id"], "R4:単位既定:単位不明", "FLAG_SINGLE")
            for d in e3a_details_11
        ]

    @patch("app.services.tcg_unit_recovery_svc.load_lookup_maps",
           return_value=_FAKE_LOOKUP_MAPS)
    @patch("app.services.tcg_unit_recovery_svc.load_condition_entries",
           return_value=_FAKE_COND_ENTRIES)
    def test_e5_changes_11(self, mock_cond, mock_maps,
                           e3a_details_11, e5_cond_rows_all_r4):
        """E5 で FLAG_SINGLE 11件が変化する"""
        s = _e5_session(e5_cond_rows_all_r4)
        result = recalc_condition_from_recovered_unit(
            e3a_details_11, s, "tenant_004"
        )
        assert result["success"] is True
        assert result["target_count"] == 11
        assert result["changed_count"] == 11

    @patch("app.services.tcg_unit_recovery_svc.load_lookup_maps",
           return_value=_FAKE_LOOKUP_MAPS)
    @patch("app.services.tcg_unit_recovery_svc.load_condition_entries",
           return_value=_FAKE_COND_ENTRIES)
    def test_e5_condition_distribution(self, mock_cond, mock_maps,
                                       e3a_details_11, e5_cond_rows_all_r4):
        """
        E5 後の condition 分布変化:
          Sealed box: +5 (box×3 + BOX×1 + 箱×1)
          Searched pack: +6 (ﾊﾟｯｸ×6)
          FLAG_SINGLE: -11
        GAS dry-run 実測と同じ方向性
        """
        s = _e5_session(e5_cond_rows_all_r4)
        result = recalc_condition_from_recovered_unit(
            e3a_details_11, s, "tenant_004"
        )
        new_conditions = [c["new_condition"] for c in result["changes"]]
        sealed_count = new_conditions.count("Sealed box")
        pack_count   = new_conditions.count("Searched pack")
        assert sealed_count == 5, f"Sealed box expected 5, got {sealed_count}"
        assert pack_count   == 6, f"Searched pack expected 6, got {pack_count}"
        old_conditions = [c["old_condition"] for c in result["changes"]]
        assert all(c == "FLAG_SINGLE" for c in old_conditions), (
            "全変化行の old_condition は FLAG_SINGLE でなければならない"
        )
