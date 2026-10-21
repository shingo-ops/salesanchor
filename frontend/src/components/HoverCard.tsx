/**
 * HoverCard — 切れた文字の全文を名前の上に浮かせて見せる金型
 *
 * - HoverCard（トリガー）で children を包み、HoverCardHost を1画面に1つだけ置く
 * - onlyWhenClipped（既定 true）: 子孫の [data-hover-card-clip] のどれかが切れているときだけ出す
 * - delay (ms) 後に表示。開いている間と閉じて 300ms 以内は待たずに出し、位置を滑らせる
 * - クリックでは開閉しない（行クリックの引き出しとぶつけない）
 */

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import "./HoverCard.css";

export interface HoverCardProps {
  /** 1行目（太字） */
  title: string;
  /** 2行目（小さく薄く）。空なら出さない */
  subtitle?: string | null;
  /** 既定 true。子孫の [data-hover-card-clip] のどれかが切れているときだけ出す */
  onlyWhenClipped?: boolean;
  /** 表示までの遅延 ms（デフォルト: 150） */
  delay?: number;
  className?: string;
  children: ReactNode;
}

interface CardState {
  anchor: DOMRect | null;
  title: string;
  subtitle: string | null;
  open: boolean;
  glide: boolean;
}

const OFFSET_X = 4; // px — 基準の左端からのずらし
const GAP = 8; // px — 基準との間隔・画面端の余白
const REOPEN_MS = 300; // 閉じてからこの間は待たずに出す

let state: CardState = { anchor: null, title: "", subtitle: null, open: false, glide: false };
let owner: HTMLElement | null = null;
let closedAt = 0;
const listeners = new Set<() => void>();

function setState(next: Partial<CardState>) {
  state = { ...state, ...next };
  listeners.forEach((l) => l());
}

function subscribe(l: () => void) {
  listeners.add(l);
  return () => {
    listeners.delete(l);
  };
}

function getState() {
  return state;
}

function closeCard() {
  if (!state.open) return;
  closedAt = Date.now();
  owner = null;
  setState({ open: false });
}

function isClipped(root: HTMLElement): boolean {
  const els = root.querySelectorAll<HTMLElement>("[data-hover-card-clip]");
  return Array.from(els).some((el) => el.scrollWidth > el.clientWidth);
}

export function HoverCard({
  title,
  subtitle,
  onlyWhenClipped = true,
  delay = 150,
  className,
  children,
}: HoverCardProps) {
  const ref = useRef<HTMLDivElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const handleMouseEnter = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    clearTimer();
    if (onlyWhenClipped && !isClipped(el)) return;
    const show = (glide: boolean) => {
      owner = el;
      setState({
        anchor: el.getBoundingClientRect(),
        title,
        subtitle: subtitle || null,
        open: true,
        glide,
      });
    };
    if (state.open || Date.now() - closedAt <= REOPEN_MS) {
      show(true);
    } else {
      timerRef.current = setTimeout(() => {
        timerRef.current = null;
        show(false);
      }, delay);
    }
  }, [clearTimer, onlyWhenClipped, title, subtitle, delay]);

  const handleMouseLeave = useCallback(() => {
    clearTimer();
    if (owner === ref.current) closeCard();
  }, [clearTimer]);

  // アンマウント時にタイマー解除。自分が基準なら閉じる（即時反映で行が描き直されても残さない）
  // React は cleanup 前に ref を null にするので、本体で取っておく
  useEffect(() => {
    const el = ref.current;
    return () => {
      clearTimer();
      if (owner !== null && owner === el) closeCard();
    };
  }, [clearTimer]);

  return (
    <div
      ref={ref}
      className={["comp-hover-card-trigger", className].filter(Boolean).join(" ")}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {children}
    </div>
  );
}

export function HoverCardHost() {
  const s = useSyncExternalStore(subscribe, getState, getState);
  const cardRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ top: number; left: number; below: boolean }>({
    top: 0,
    left: 0,
    below: false,
  });
  const [shown, setShown] = useState(false);
  const [mounted, setMounted] = useState(false);

  // いちど開いたら閉じたあとも DOM を残す（フェードアウトと滑りのため）
  useEffect(() => {
    if (s.open) setMounted(true);
  }, [s.open]);

  useLayoutEffect(() => {
    const card = cardRef.current;
    if (!s.open || !s.anchor || !card) return;
    const w = card.offsetWidth;
    const h = card.offsetHeight;
    const maxLeft = window.innerWidth - w - GAP;
    const left = Math.max(GAP, Math.min(s.anchor.left + OFFSET_X, maxLeft));
    let top = s.anchor.top - h - GAP;
    let below = false;
    if (top < GAP) {
      top = s.anchor.bottom + GAP;
      below = true;
    }
    setPos({ top, left, below });
  }, [s.open, s.anchor, s.title, s.subtitle, mounted]);

  // open になった次のフレームで --open を付ける（拡大しながらのフェードイン）
  useEffect(() => {
    if (!s.open) {
      setShown(false);
      return;
    }
    const id = requestAnimationFrame(() => setShown(true));
    return () => cancelAnimationFrame(id);
  }, [s.open, s.anchor]);

  // スクロール（capture）と画面幅の変更で閉じる
  useEffect(() => {
    if (!s.open) return;
    window.addEventListener("scroll", closeCard, true);
    window.addEventListener("resize", closeCard);
    return () => {
      window.removeEventListener("scroll", closeCard, true);
      window.removeEventListener("resize", closeCard);
    };
  }, [s.open]);

  if (!mounted) return null;

  const cls = [
    "comp-hover-card",
    pos.below ? "comp-hover-card--below" : "",
    s.glide ? "comp-hover-card--glide" : "",
    s.open && shown ? "comp-hover-card--open" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return createPortal(
    <div
      ref={cardRef}
      className={cls}
      role="tooltip"
      aria-hidden={!s.open}
      style={{ top: pos.top, left: pos.left }}
    >
      <span className="comp-hover-card__title">{s.title}</span>
      {s.subtitle && <span className="comp-hover-card__subtitle">{s.subtitle}</span>}
    </div>,
    document.body,
  );
}
