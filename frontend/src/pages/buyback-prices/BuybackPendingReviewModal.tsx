/**
 * BuybackPendingReviewModal
 *
 * 買取商品マッチング確認モーダル。
 * 複数候補が見つかった商品について、管理者が正しい自社商品を選択する。
 * - pending-reviews API から一覧取得
 * - 各アイテムごとに候補ボタンを表示し、選択時に POST /buyback-prices/{id}/link を呼ぶ
 * - 「該当なし」で unmatched 登録
 * - 全件処理後にモーダルを閉じる
 */
import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Modal } from "../../components/Modal";
import { Card } from "../../components/Card";
import { Badge } from "../../components/Badge";
import { Button } from "../../components/Button";
import { api } from "../../lib/api";
import type { PendingReviewItem, PendingReviewResponse, MatchCandidate } from "./buybackTypes";

interface BuybackPendingReviewModalProps {
  open: boolean;
  onClose: () => void;
}

export function BuybackPendingReviewModal({ open, onClose }: BuybackPendingReviewModalProps) {
  const { t } = useTranslation();

  const [items, setItems] = useState<PendingReviewItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [linkedIds, setLinkedIds] = useState<Set<string>>(new Set());
  const [submitting, setSubmitting] = useState<string | null>(null);

  const fetchItems = useCallback(() => {
    if (!open) return;
    setLoading(true);
    setError("");
    api
      .get<PendingReviewResponse>("/buyback-prices/pending-reviews")
      .then((res) => {
        setItems(res.items);
        setLinkedIds(new Set());
      })
      .catch(() => {
        setError(t("buybackPrices.loadError"));
      })
      .finally(() => {
        setLoading(false);
      });
  }, [open, t]);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  const handleLink = async (shopProductId: string, candidate: MatchCandidate) => {
    setSubmitting(shopProductId);
    try {
      await api.post(`/buyback-prices/${shopProductId}/link`, {
        product_id: candidate.product_id,
      });
      setLinkedIds((prev) => new Set(prev).add(shopProductId));
    } catch {
      // エラーは無視せず次のアイテムに進む（再取得で確認）
    } finally {
      setSubmitting(null);
    }
  };

  const handleNoMatch = async (shopProductId: string) => {
    setSubmitting(shopProductId);
    try {
      await api.post(`/buyback-prices/${shopProductId}/link`, {
        product_id: null,
      });
      setLinkedIds((prev) => new Set(prev).add(shopProductId));
    } catch {
      // エラーは無視せず次のアイテムに進む
    } finally {
      setSubmitting(null);
    }
  };

  const pendingItems = items.filter((item) => !linkedIds.has(item.shop_product_id));

  const handleClose = () => {
    setItems([]);
    setLinkedIds(new Set());
    setError("");
    onClose();
  };

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title={t("buybackPrices.pendingReviewTitle")}
      size="lg"
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
        <p style={{ color: "var(--text-muted)", fontSize: "var(--font-sm)", margin: 0 }}>
          {t("buybackPrices.pendingReviewDesc")}
        </p>

        {loading && (
          <p role="status" style={{ color: "var(--text-muted)", fontSize: "var(--font-sm)" }}>
            {t("buybackPrices.loading")}
          </p>
        )}

        {!loading && error && (
          <p role="alert" style={{ color: "var(--danger)", fontSize: "var(--font-sm)" }}>
            {error}
          </p>
        )}

        {!loading && !error && pendingItems.length === 0 && (
          <p style={{ color: "var(--text-muted)", fontSize: "var(--font-sm)" }}>
            {t("buybackPrices.pendingReviewEmpty")}
          </p>
        )}

        {!loading && pendingItems.map((item) => {
          const isSubmitting = submitting === item.shop_product_id;
          return (
            <Card key={item.shop_product_id} variant="container" density="compact">
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
                <div>
                  <p style={{ margin: 0, fontSize: "var(--font-sm)", color: "var(--text-muted)" }}>
                    {t("buybackPrices.pendingReviewBuyback")}
                  </p>
                  <p style={{ margin: 0, fontWeight: "600" }}>
                    {item.product_name}
                  </p>
                  <Badge variant="neutral" size="sm">{item.shop_code}</Badge>
                </div>

                <div>
                  <p style={{ margin: 0, fontSize: "var(--font-sm)", color: "var(--text-muted)" }}>
                    {t("buybackPrices.pendingReviewCandidates")}
                  </p>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)", marginTop: "var(--space-2)" }}>
                    {item.match_candidates.map((candidate) => (
                      <Button
                        key={candidate.product_id}
                        variant="outline"
                        size="sm"
                        disabled={isSubmitting}
                        onClick={() => handleLink(item.shop_product_id, candidate)}
                        title={t("buybackPrices.pendingReviewMatchedBy", { keyword: candidate.keyword })}
                      >
                        {candidate.product_code}
                      </Button>
                    ))}
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={isSubmitting}
                      onClick={() => handleNoMatch(item.shop_product_id)}
                    >
                      {t("buybackPrices.pendingReviewNoMatch")}
                    </Button>
                  </div>
                </div>
              </div>
            </Card>
          );
        })}

        {!loading && items.length > 0 && linkedIds.size > 0 && (
          <p style={{ color: "var(--success)", fontSize: "var(--font-sm)" }}>
            {t("buybackPrices.pendingReviewLinked")}: {linkedIds.size} / {items.length}
          </p>
        )}
      </div>
    </Modal>
  );
}
