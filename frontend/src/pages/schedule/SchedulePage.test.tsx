import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import SchedulePage from "./SchedulePage";

const {
  mockGet,
  mockPermissions,
  mockSetInterval,
  mockClearInterval,
} = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPermissions: new Set<string>(),
  mockSetInterval: vi.fn(),
  mockClearInterval: vi.fn(),
}));

const translate = (key: string, vars?: Record<string, string | number>) => {
  const labels: Record<string, string> = {
    "schedule.title": "Schedule",
    "schedule.settings": "Settings",
    "schedule.myCalendars": "My calendars",
    "schedule.otherCalendars": "Other members",
    "schedule.create": "Create",
    "schedule.loading": "Loading",
    "schedule.emptyTitle": "No events",
    "schedule.emptyDescription": "No events available",
    "schedule.addEvent": "Add event",
    "schedule.settingsSubtitle": "Settings subtitle",
    "schedule.settingsNavigation": "Settings navigation",
    "schedule.settingsTitle": "Schedule settings",
    "schedule.settingsBack": "Back",
    "common.noData": "No data",
    "common.close": "Close",
  };
  if (vars?.count != null) return `${key}:${vars.count}`;
  return labels[key] ?? key;
};

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: translate,
  }),
}));

vi.mock("../../lib/api", () => ({
  api: {
    get: mockGet,
  },
}));

vi.mock("../../hooks/usePermissions", () => ({
  usePermissions: () => ({
    permissions: mockPermissions,
    loading: false,
    error: null,
    hasPermission: (key: string) => mockPermissions.has(key),
    hasAny: (...keys: string[]) => keys.some((key) => mockPermissions.has(key)),
    reload: vi.fn(),
  }),
}));

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/schedule"]}>
      <SchedulePage />
    </MemoryRouter>,
  );
}

describe("SchedulePage staff roster", () => {
  beforeEach(() => {
    mockPermissions.clear();
    mockGet.mockReset();
    mockSetInterval.mockReset();
    mockClearInterval.mockReset();
    vi.spyOn(window, "setInterval").mockImplementation(((handler: TimerHandler) => {
      mockSetInterval(handler);
      return 1 as unknown as number;
    }) as typeof window.setInterval);
    vi.spyOn(window, "clearInterval").mockImplementation((intervalId) => {
      mockClearInterval(intervalId);
    });
    mockGet.mockImplementation(async (path: string) => {
      if (path === "/staff/me") {
        return {
          id: 1,
          user_id: 101,
          staff_code: "EMP-001",
          surname_jp: "Yamada",
          given_name_jp: "Taro",
          primary_email: "yamada@example.com",
        };
      }
      if (path.startsWith("/staff?")) {
        return [
          {
            id: 1,
            user_id: 101,
            staff_code: "EMP-001",
            surname_jp: "Yamada",
            given_name_jp: "Taro",
            primary_email: "yamada@example.com",
          },
          {
            id: 2,
            user_id: 202,
            staff_code: "EMP-002",
            surname_jp: "Sato",
            given_name_jp: "Hanako",
            primary_email: "sato@example.com",
          },
        ];
      }
      if (path.includes("/calendar/events") && path.includes("user_id=101")) {
        return {
          events: [
            {
              id: 11,
              user_id: 101,
              calendar_type: "personal",
              category: "meeting",
              title: "Mine",
              description: null,
              location: null,
              start_datetime: "2026-06-20T09:00:00+09:00",
              end_datetime: "2026-06-20T10:00:00+09:00",
              is_all_day: false,
              source: "app",
              sync_status: "synced",
              created_by_user_id: 101,
              created_by_name: "Yamada Taro",
            },
          ],
        };
      }
      if (path.includes("/calendar/events") && path.includes("user_id=202")) {
        return {
          events: [
            {
              id: 22,
              user_id: 202,
              calendar_type: "personal",
              category: "meeting",
              title: "Other",
              description: null,
              location: null,
              start_datetime: "2026-06-20T11:00:00+09:00",
              end_datetime: "2026-06-20T12:00:00+09:00",
              is_all_day: false,
              source: "app",
              sync_status: "synced",
              created_by_user_id: 202,
              created_by_name: "Sato Hanako",
            },
          ],
        };
      }
      if (path.startsWith("/shifts?")) {
        return [];
      }
      throw new Error(`unexpected request: ${path}`);
    });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("shows only my calendar for non-managers", async () => {
    renderPage();

    await waitFor(() => expect(screen.getByText("Mine")).toBeTruthy());
    expect(screen.queryByText("Other members")).toBeNull();
  });

  it("lets managers toggle other members on and off", async () => {
    mockPermissions.add("staff.view");
    renderPage();

    await waitFor(() => expect(screen.getByText("Mine")).toBeTruthy());
    expect(screen.getByText("Other members")).toBeTruthy();
    expect(screen.queryByText("Other")).toBeNull();

    fireEvent.click(screen.getByLabelText("Sato Hanako"));
    await waitFor(() => expect(screen.getByText("Other")).toBeTruthy());

    fireEvent.click(screen.getByLabelText("Sato Hanako"));
    await waitFor(() => expect(screen.queryByText("Other")).toBeNull());
  });
});
