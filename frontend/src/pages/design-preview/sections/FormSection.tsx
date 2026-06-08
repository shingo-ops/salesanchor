/**
 * §6 フォーム入力 — 全状態
 * §7 フォーム入力 — サイズ比較
 */
import { TextField } from "../../../components/TextField";
import { Select } from "../../../components/Select";
import { Textarea } from "../../../components/Textarea";
import { SectionHeader } from "./_shared";

const DEMO_SELECT_OPTIONS = [
  { value: "active",  label: "有効 (Active)"  },
  { value: "pending", label: "保留 (Pending)" },
  { value: "closed",  label: "終了 (Closed)"  },
];

export function FormSection() {
  return (
    <>
      {/* §6: 全状態 */}
      <section className="dp-section">
        <SectionHeader
          title="6. フォーム入力 — 全状態 (states)"
          desc="通常・focus（選択中・青枠）・エラー（赤枠＋エラーメッセージ）・無効（薄く表示）の見え方を確認します。"
        />
        <div className="dp-form-grid">
          {/* テキスト入力 (TextField) */}
          <div>
            <span className="dp-card-col-label">テキスト入力 (TextField) / 通常</span>
            <TextField label="会社名" placeholder="会社名を入力" helperText="補助テキストの表示例。" />
          </div>
          <div>
            <span className="dp-card-col-label">テキスト入力 (TextField) / 必須 (required)</span>
            <TextField label="メールアドレス" type="email" placeholder="you@example.com" required />
          </div>
          <div>
            <span className="dp-card-col-label">テキスト入力 (TextField) / エラー (error)</span>
            <TextField
              label="メールアドレス"
              type="email"
              defaultValue="不正な入力値"
              error="メールアドレスの形式が正しくありません。"
              required
            />
          </div>
          <div>
            <span className="dp-card-col-label">テキスト入力 (TextField) / 無効 (disabled)</span>
            <TextField label="アカウント ID" defaultValue="ACC-00123" disabled helperText="変更できません。" />
          </div>

          {/* 選択 (Select) */}
          <div>
            <span className="dp-card-col-label">選択 (Select) / 通常</span>
            <Select label="ステータス" options={DEMO_SELECT_OPTIONS} placeholder="-- 選択してください --" helperText="補助テキストの表示例。" />
          </div>
          <div>
            <span className="dp-card-col-label">選択 (Select) / 必須 (required)</span>
            <Select label="カテゴリ" options={DEMO_SELECT_OPTIONS} placeholder="-- 選択してください --" required />
          </div>
          <div>
            <span className="dp-card-col-label">選択 (Select) / エラー (error)</span>
            <Select label="地域" options={DEMO_SELECT_OPTIONS} error="選択肢を選んでください。" required />
          </div>
          <div>
            <span className="dp-card-col-label">選択 (Select) / 無効 (disabled)</span>
            <Select label="通貨" options={[{ value: "jpy", label: "JPY — 日本円" }]} defaultValue="jpy" disabled helperText="このアカウントでは固定です。" />
          </div>

          {/* 複数行入力 (Textarea) */}
          <div>
            <span className="dp-card-col-label">複数行入力 (Textarea) / 通常</span>
            <Textarea label="メモ" placeholder="メモを入力してください..." helperText="チーム全員に表示されます。" />
          </div>
          <div>
            <span className="dp-card-col-label">複数行入力 (Textarea) / エラー (error)</span>
            <Textarea label="メッセージ" placeholder="メッセージを入力..." error="メッセージを入力してください。" required />
          </div>
          <div>
            <span className="dp-card-col-label">複数行入力 (Textarea) / 無効 (disabled)</span>
            <Textarea label="テンプレート本文" defaultValue="このテンプレートはロックされています。" disabled helperText="変更できません。" />
          </div>
        </div>
      </section>

      {/* §7: サイズ比較 */}
      <section className="dp-section">
        <SectionHeader
          title="7. フォーム入力 — サイズ比較 (sm / md / lg)"
          desc="小 (sm)＝28px 最小高 / 中 (md)＝既定 / 大 (lg)＝44px 最小高（モバイルタッチ対応）"
        />
        <div className="dp-form-grid">
          <div>
            <span className="dp-card-col-label">テキスト入力 / 小 (sm)</span>
            <TextField label="小サイズ" placeholder="sm 入力" size="sm" />
          </div>
          <div>
            <span className="dp-card-col-label">テキスト入力 / 中・既定 (md)</span>
            <TextField label="中サイズ（既定）" placeholder="md 入力" size="md" />
          </div>
          <div>
            <span className="dp-card-col-label">テキスト入力 / 大 (lg)</span>
            <TextField label="大サイズ" placeholder="lg 入力" size="lg" />
          </div>
          <div>
            <span className="dp-card-col-label">選択 / 小 (sm)</span>
            <Select label="小サイズ" options={DEMO_SELECT_OPTIONS} size="sm" />
          </div>
          <div>
            <span className="dp-card-col-label">選択 / 中・既定 (md)</span>
            <Select label="中サイズ（既定）" options={DEMO_SELECT_OPTIONS} size="md" />
          </div>
          <div>
            <span className="dp-card-col-label">選択 / 大 (lg)</span>
            <Select label="大サイズ" options={DEMO_SELECT_OPTIONS} size="lg" />
          </div>
        </div>
      </section>
    </>
  );
}
