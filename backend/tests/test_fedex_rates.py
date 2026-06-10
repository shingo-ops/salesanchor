"""
FedEx Rates API クライアントのユニットテスト（ADR-125）。

実際の FedEx API は呼び出さず、httpx をモックして動作を検証する。

テスト対象:
  - get_or_refresh_token: キャッシュヒット / ミス / 期限切れ
  - get_rates: 正常系 / 認証エラー / API エラー / タイムアウト / サービスフィルタ
  - /shipping/calculate エンドポイント: FedEx ライブ分岐 / 静的フォールバック /
                                         未連携時の live_error 明示返却 /
                                         rate_precision exact/approximate（仕様追補 2026-06-10）

変更履歴:
  2026-06-09: 初版（ADR-125 Phase B）
  2026-06-10: TARGET_INTERNATIONAL_SERVICE_TYPES フィルタ対応
              rate_precision (exact/approximate) テスト追加
              _try_fedex_live の 3-tuple 戻り値に対応
        """
        from app.routers.shipping import calc_shipping
        from app.schemas.shipping import ShippingCalcRequest

        with patch("app.services.carrier_credentials.get_credentials", return_value=None), \
             patch("app.routers.shipping.calculate_shipping_fee", new_callable=AsyncMock) as mock_calc:
            data = ShippingCalcRequest(
                country_code="US",
                weight_kg=Decimal("1.0"),
                carrier="fedex",
                origin_country_code="JP",
            )
            resp = await calc_shipping(
                data=data,
                db=AsyncMock(),
                tenant_id=1,
                current_user=MagicMock(),
            )

        assert resp.results == [], f"未連携時に静的結果が混入: {resp.results}"
        assert resp.live_error is not None, "未連携時に live_error が None"
        assert "未連携" in resp.live_error, f"live_error に「未連携」文言なし: {resp.live_error}"
        mock_calc.assert_not_called()  # calculate_shipping_fee が呼ばれないこと

    async def test_live_error_explicit_on_api_failure(self):
        """FedEx API エラー時に live_error を明示返却し、results は空。

        ADR-125 D5: 暗黙フォールバック禁止。
        """
        from app.routers.shipping import _try_fedex_live

        creds = {
            "client_id": "cid",
            "client_secret": "csec",
            "environment": "sandbox",
            "account_number": "123456789",
        }

        with patch("app.services.fedex_rates.get_rates", side_effect=FedExAPIError("タイムアウト")):
            results, live_error, rate_precision = await _try_fedex_live(
                creds=creds,
                tenant_id=1,
                destination_country_code="US",
                origin_country_code="JP",
                weight_kg=Decimal("1.0"),
            )

        assert results == []
        assert live_error is not None
        assert "タイムアウト" in live_error
        assert rate_precision is None  # API エラー時は精度フラグなし

    async def test_no_account_number_returns_live_error(self):
        """account_number 未設定時に live_error を返す（D5）。"""
        from app.routers.shipping import _try_fedex_live

        creds = {
            "client_id": "cid",
            "client_secret": "csec",
            "environment": "sandbox",
            "account_number": None,  # 未設定
        }

        results, live_error, rate_precision = await _try_fedex_live(
            creds=creds,
            tenant_id=1,
            destination_country_code="US",
            origin_country_code="JP",
            weight_kg=Decimal("1.0"),
        )

        assert results == []
        assert live_error is not None
        assert rate_precision is None  # account_number 未設定時は精度フラグなし

    async def test_rate_precision_exact_when_postal_code_provided(self):
        """郵便番号指定ありで rate_precision='exact' を返す（仕様追補 2026-06-10）。"""
        from app.routers.shipping import _try_fedex_live

        creds = {
            "client_id": "cid",
            "client_secret": "csec",
            "environment": "sandbox",
            "account_number": "740561073",
        }
        mock_quotes = [
            FedExRateQuote(
                service_type="INTERNATIONAL_PRIORITY",
                service_name="FedEx International Priority®",
                total_net_charge=Decimal("12500"),
                currency="JPY",
            )
        ]

        with patch("app.services.fedex_rates.get_rates", return_value=mock_quotes):
            results, live_error, rate_precision = await _try_fedex_live(
                creds=creds,
                tenant_id=1,
                destination_country_code="US",
                origin_country_code="JP",
                weight_kg=Decimal("1.0"),
                destination_postal_code="10001",  # 郵便番号あり
            )

        assert live_error is None
        assert rate_precision == "exact"

    async def test_rate_precision_approximate_when_no_postal_code(self):
        """郵便番号未指定で rate_precision='approximate' を返す（仕様追補 2026-06-10）。"""
        from app.routers.shipping import _try_fedex_live

        creds = {
            "client_id": "cid",
            "client_secret": "csec",
            "environment": "sandbox",
            "account_number": "740561073",
        }
        mock_quotes = [
            FedExRateQuote(
                service_type="INTERNATIONAL_PRIORITY",
                service_name="FedEx International Priority®",
                total_net_charge=Decimal("12500"),
                currency="JPY",
            )
        ]

        with patch("app.services.fedex_rates.get_rates", return_value=mock_quotes):
            results, live_error, rate_precision = await _try_fedex_live(
                creds=creds,
                tenant_id=1,
                destination_country_code="US",
                origin_country_code="JP",
                weight_kg=Decimal("1.0"),
                # destination_postal_code 未指定
            )

        assert live_error is None
        assert rate_precision == "approximate"
