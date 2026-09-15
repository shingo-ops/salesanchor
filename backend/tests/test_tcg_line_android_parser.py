import unittest
from app.services.tcg_line_android_parser import AndroidExportError, parse_android_export

SAMPLE = '[LINE] test\r\n保存日時: test\r\n\r\n2026/9/12(土)\r\n12:00\t姓 名\t商品A\r\n\r\n商品B\t注記\r\n12:01\t別の人\t末尾\r\n'


class ParserTests(unittest.TestCase):
    def test_multiline_and_sender_spaces(self):
        result = parse_android_export(SAMPLE)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['display_name'], '姓 名')
        self.assertEqual(result[0]['body'], '商品A\n\n商品B\t注記')
        self.assertEqual(result[-1]['body'], '末尾')
        self.assertEqual(result[0]['timestamp'], '2026-09-12 12:00:00')

    def test_bom(self):
        self.assertEqual(parse_android_export('\ufeff' + SAMPLE), parse_android_export(SAMPLE))

    def test_system_record_is_not_supplier(self):
        result = parse_android_export(SAMPLE + '12:02\t参加しました\n')
        self.assertTrue(result[-1]['is_system_event'])
        self.assertEqual(result[-1]['display_name'], '')

    def test_literal_quotes_not_csv(self):
        result = parse_android_export('2026/9/12(土)\n1:02\tA\t"引用\n続き"')
        self.assertEqual(result[0]['body'], '"引用\n続き"')

    def test_empty_pc_and_invalid_dates_rejected(self):
        for value in ['', '2026.09.12 土曜日\n12:00 A text',
                      '2026/2/30(月)\n12:00\tA\tB',
                      '2026/9/12(土)\n24:01\tA\tB',
                      '2026/9/12(土)\n12:01\t\tB']:
            with self.subTest(value=value), self.assertRaises(AndroidExportError):
                parse_android_export(value)

    def test_headerless_content_after_date_rejected(self):
        with self.assertRaises(AndroidExportError):
            parse_android_export('2026/9/12(土)\nmissing header\n12:00\tA\tB')
