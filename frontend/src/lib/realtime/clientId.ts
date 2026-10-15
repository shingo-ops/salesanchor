// ADR-1016: タブごとの乱数 ID。保存しない（モジュール変数のみ）。自分が起こした変更の合図を無視するために使う。
const clientId: string = crypto.randomUUID();

export function getClientId(): string {
  return clientId;
}
