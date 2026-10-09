/** 日本時間（Asia/Tokyo）の「年月日 時分」に整える。要確認ページの日時列で共有する。 */
export function formatDate(isoString: string, locale: string): string {
  return new Intl.DateTimeFormat(locale.startsWith("ja") ? "ja-JP" : "en-GB", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(new Date(isoString));
}
