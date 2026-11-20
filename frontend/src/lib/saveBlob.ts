/**
 * Blob に名前を付けて保存する（同じ出所の blob の URL を a[download] で押す）。
 * invoice-create-portfolio design-v2 §3-6（R6）。同じ書き方の今あるページは R6 では書き換えない。
 */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  try {
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
  } finally {
    anchor.remove();
    URL.revokeObjectURL(url);
  }
}
