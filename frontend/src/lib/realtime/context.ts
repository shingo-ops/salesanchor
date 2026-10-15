import { createContext } from "react";

export type RealtimeEvent = { topic: string; origin: string | null } | { reconnected: true };
export type RealtimeHandler = (ev: RealtimeEvent) => void;

export interface RealtimeApi {
  clientId: string;
  subscribe: (topics: readonly string[], handler: RealtimeHandler) => () => void;
}

/** Provider の外では null（試験や Storybook でも落ちないようにする） */
export const RealtimeContext = createContext<RealtimeApi | null>(null);
