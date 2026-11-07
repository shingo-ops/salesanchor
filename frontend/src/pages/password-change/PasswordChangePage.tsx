import { useTranslation } from "react-i18next";
import { PageLayout } from "../../components/PageLayout";
import { Button } from "../../components/Button";
import { useAuth } from "../../contexts/AuthContext";
import PasswordChangeForm from "../../features/auth/PasswordChangeForm";

/**
 * 仮パスワードの変更ページ（ADR-1068）。シェルの無い道。
 * 変えるまで他の API は 403 password_change_required で止まるため、このページ自身は他の API を呼ばない。
 */
export default function PasswordChangePage() {
  const { t } = useTranslation();
  const { signOut } = useAuth();

  return (
    <PageLayout titleText={t("passwordChangePage.title")} subtitleKey="passwordChangePage.subtitle">
      <PasswordChangeForm onChanged={() => window.location.assign("/")} />
      <Button variant="secondary" type="button" onClick={() => void signOut()}>
        {t("passwordChangePage.signOut")}
      </Button>
    </PageLayout>
  );
}
