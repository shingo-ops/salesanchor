/**
 * AsyncCombobox — 名前を入れると候補が出て選べる部品（ADR-144 金型）
 *
 * - 入力のたびに（debounceMs 待ってから）loadOptions(query) で候補を取り直す。
 * - 候補は選んだときだけ onSelect で渡す。打っている途中の文字では何も起こさない。
 * - 候補の一覧は document.body に Portal で描き、position: fixed で入力欄の下に合わせる。
 *   表（DataTable の .comp-table は overflow-x:auto で縦も切れる）のセルに置いても切れない。
 *   スクロール（capture）とリサイズで位置を取り直す。下に収まらなければ上に開く。
 * - キー操作: ArrowDown / ArrowUp / Enter / Escape。WAI-ARIA combobox（listbox + option）。
 * - 文字（noResultsText / loadingText / errorText / placeholder / ariaLabel）は呼ぶ側が t() で渡す。
 */
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import type { CSSProperties, KeyboardEvent as ReactKeyboardEvent } from "react";
import { createPortal } from "react-dom";
import { TextFieldControl } from "./TextField";
import "./AsyncCombobox.css";

export interface AsyncComboboxOption {
  value: string;
  label: string;
}

export interface AsyncComboboxProps {
  id: string;
  /** 入力欄の読み上げ名（呼ぶ側が t() で渡す） */
  ariaLabel: string;
  /** 閉じているときに入力欄へ出す文字（今の値の表示名） */
  value: string;
  placeholder?: string;
  disabled?: boolean;
  /** 候補を取る。query は前後の空白を除いた文字 */
  loadOptions: (query: string) => Promise<AsyncComboboxOption[]>;
  /** 候補を選んだときだけ呼ぶ */
  onSelect: (option: AsyncComboboxOption) => void;
  /** 何文字から検索するか（既定 1） */
  minChars?: number;
  /** 入力が止まってから検索するまでの待ち（ms・既定 300） */
  debounceMs?: number;
  noResultsText: string;
  loadingText: string;
  /** 候補の取得に失敗したときの文字。省略時は noResultsText */
  errorText?: string;
}

type LoadStatus = "idle" | "loading" | "done" | "error";

const DEFAULT_MIN_CHARS = 1;
const DEFAULT_DEBOUNCE_MS = 300;
const LIST_MAX_HEIGHT_PX = 240;
const LIST_GAP_PX = 4;
const VIEWPORT_MARGIN_PX = 8;

interface ListPosition {
  left: number;
  width: number;
  maxHeight: number;
  placement: "bottom" | "top";
  /** placement=bottom のとき top、top のとき bottom（どちらも viewport 基準） */
  edge: number;
}

function calcListPosition(rect: DOMRect): ListPosition {
  const spaceBelow = window.innerHeight - rect.bottom - LIST_GAP_PX - VIEWPORT_MARGIN_PX;
  const spaceAbove = rect.top - LIST_GAP_PX - VIEWPORT_MARGIN_PX;
  const placeTop = spaceBelow < LIST_MAX_HEIGHT_PX && spaceAbove > spaceBelow;
  const room = placeTop ? spaceAbove : spaceBelow;
  const maxHeight = Math.max(0, Math.min(LIST_MAX_HEIGHT_PX, room));
  const width = Math.min(rect.width, window.innerWidth - VIEWPORT_MARGIN_PX * 2);
  const left = Math.min(Math.max(rect.left, VIEWPORT_MARGIN_PX), window.innerWidth - VIEWPORT_MARGIN_PX - width);
  return placeTop
    ? { left, width, maxHeight, placement: "top", edge: window.innerHeight - rect.top + LIST_GAP_PX }
    : { left, width, maxHeight, placement: "bottom", edge: rect.bottom + LIST_GAP_PX };
}

export function AsyncCombobox({
  id,
  ariaLabel,
  value,
  placeholder,
  disabled = false,
  loadOptions,
  onSelect,
  minChars = DEFAULT_MIN_CHARS,
  debounceMs = DEFAULT_DEBOUNCE_MS,
  noResultsText,
  loadingText,
  errorText,
}: AsyncComboboxProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const requestRef = useRef(0);
  const loadRef = useRef(loadOptions);
  loadRef.current = loadOptions;

  const [editing, setEditing] = useState(false);
  const [query, setQuery] = useState("");
  const [options, setOptions] = useState<AsyncComboboxOption[]>([]);
  const [status, setStatus] = useState<LoadStatus>("idle");
  const [activeIndex, setActiveIndex] = useState(-1);
  const [position, setPosition] = useState<ListPosition | null>(null);

  const trimmed = query.trim();
  const isSearching = editing && trimmed.length >= minChars;
  const isListOpen = isSearching && !disabled;

  const close = useCallback(() => {
    requestRef.current += 1;
    setEditing(false);
    setQuery("");
    setOptions([]);
    setStatus("idle");
    setActiveIndex(-1);
  }, []);

  // 入力 → 待ってから候補を取る（古い応答は捨てる）
  useEffect(() => {
    if (!isSearching) return;
    const requestId = requestRef.current + 1;
    requestRef.current = requestId;
    setStatus("loading");
    const timer = window.setTimeout(() => {
      loadRef
        .current(trimmed)
        .then((rows) => {
          if (requestRef.current !== requestId) return;
          setOptions(rows);
          setActiveIndex(rows.length > 0 ? 0 : -1);
          setStatus("done");
        })
        .catch(() => {
          if (requestRef.current !== requestId) return;
          setOptions([]);
          setActiveIndex(-1);
          setStatus("error");
        });
    }, debounceMs);
    return () => window.clearTimeout(timer);
  }, [isSearching, trimmed, debounceMs]);

  // 一覧の位置: 開いている間、入力欄に合わせる（スクロールは capture で拾う）
  const updatePosition = useCallback(() => {
    if (!inputRef.current) return;
    setPosition(calcListPosition(inputRef.current.getBoundingClientRect()));
  }, []);

  useLayoutEffect(() => {
    if (!isListOpen) {
      setPosition(null);
      return;
    }
    updatePosition();
    window.addEventListener("scroll", updatePosition, true);
    window.addEventListener("resize", updatePosition);
    return () => {
      window.removeEventListener("scroll", updatePosition, true);
      window.removeEventListener("resize", updatePosition);
    };
  }, [isListOpen, updatePosition]);

  // 動かしたとき、選択中の候補が見える位置にスクロールする
  useEffect(() => {
    if (activeIndex < 0 || !listRef.current) return;
    const el = listRef.current.querySelector<HTMLElement>(`[data-index="${activeIndex}"]`);
    el?.scrollIntoView?.({ block: "nearest" });
  }, [activeIndex]);

  const choose = (option: AsyncComboboxOption) => {
    onSelect(option);
    close();
  };

  const handleKeyDown = (event: ReactKeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Escape") {
      if (editing) {
        event.preventDefault();
        close();
      }
      return;
    }
    if (!isListOpen || options.length === 0) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((current) => (current + 1) % options.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((current) => (current <= 0 ? options.length - 1 : current - 1));
    } else if (event.key === "Enter" && activeIndex >= 0) {
      event.preventDefault();
      choose(options[activeIndex]);
    }
  };

  const listId = `${id}-listbox`;
  const optionId = (index: number) => `${id}-option-${index}`;
  const hasOptions = status === "done" && options.length > 0;
  const listStyle: CSSProperties | undefined = position
    ? ({
        "--async-combobox-left": `${position.left}px`,
        "--async-combobox-width": `${position.width}px`,
        "--async-combobox-max-h": `${position.maxHeight}px`,
        "--async-combobox-edge": `${position.edge}px`,
      } as CSSProperties)
    : undefined;

  let message: string | null = null;
  if (status === "loading" || status === "idle") message = loadingText;
  else if (status === "error") message = errorText ?? noResultsText;
  else if (options.length === 0) message = noResultsText;

  return (
    <div className="comp-async-combobox">
      <TextFieldControl
        ref={inputRef}
        id={id}
        type="text"
        role="combobox"
        aria-label={ariaLabel}
        aria-expanded={isListOpen}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={hasOptions && activeIndex >= 0 ? optionId(activeIndex) : undefined}
        autoComplete="off"
        size="sm"
        disabled={disabled}
        value={editing ? query : value}
        placeholder={placeholder}
        onFocus={() => {
          if (disabled) return;
          setEditing(true);
          setQuery("");
        }}
        onChange={(event) => {
          if (disabled) return;
          setEditing(true);
          setQuery(event.target.value);
        }}
        onBlur={close}
        onKeyDown={handleKeyDown}
      />
      {isListOpen &&
        position &&
        createPortal(
          <div
            ref={listRef}
            id={listId}
            role="listbox"
            aria-busy={status === "loading"}
            aria-label={ariaLabel}
            className={`comp-async-combobox__list comp-async-combobox__list--${position.placement}`}
            style={listStyle}
            onMouseDown={(event) => event.preventDefault()}
            onClick={(event) => event.stopPropagation()}
          >
            {hasOptions
              ? options.map((option, index) => (
                  <button
                    key={option.value}
                    id={optionId(index)}
                    data-index={index}
                    type="button"
                    role="option"
                    aria-selected={index === activeIndex}
                    className={
                      index === activeIndex
                        ? "comp-async-combobox__option comp-async-combobox__option--active"
                        : "comp-async-combobox__option"
                    }
                    onMouseEnter={() => setActiveIndex(index)}
                    onClick={() => choose(option)}
                  >
                    {option.label}
                  </button>
                ))
              : message !== null && <div className="comp-async-combobox__message">{message}</div>}
          </div>,
          document.body,
        )}
    </div>
  );
}
