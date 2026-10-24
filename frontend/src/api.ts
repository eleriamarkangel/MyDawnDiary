export type Theme = "orange-yellow" | "blue-yellow" | "green-yellow";

export interface User {
  id: string;
  email: string;
  display_name: string | null;
  time_zone: string;
  theme: Theme;
}

export interface Note {
  id: string;
  diary_date: string;
  title: string | null;
  content: string;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
  purge_after: string | null;
}

export interface TrashedRecord {
  id: string;
  diary_date: string;
  title: string | null;
  ai_summary: string | null;
  edited_summary: string | null;
  deleted_at: string | null;
  purge_after: string | null;
  entries: { id: string; speaker: "user" | "assistant"; content: string; position: number }[];
}

export interface Trash {
  notes: Note[];
  records: TrashedRecord[];
}

export interface Diary {
  diary_date: string;
  ai_combined_entry: string | null;
  edited_combined_entry: string | null;
  notes: Note[];
}

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

export async function api<T>(path: string, options: {
  method?: string;
  body?: unknown;
  token?: string;
} = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (options.token) headers.Authorization = `Bearer ${options.token}`;
  let response: Response;
  try {
    response = await fetch(path, {
      method: options.method || "GET",
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    });
  } catch {
    throw new ApiError("Could not reach the server. Check your connection and try again.", 0);
  }
  if (response.status === 204) return null as T;
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data && typeof data === "object" && "detail" in data ? data.detail : null;
    const message = typeof detail === "string" ? detail :
      Array.isArray(detail) ? detail.map((item) => item?.msg || "Invalid value").join("; ") :
      `Request failed (${response.status}).`;
    throw new ApiError(message, response.status);
  }
  return data as T;
}

export function userDate(timeZone: string): string {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone, year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date());
  const pick = (type: string) => parts.find((part) => part.type === type)?.value;
  return `${pick("year")}-${pick("month")}-${pick("day")}`;
}

export function displayDate(date: string, weekday = false): string {
  return new Intl.DateTimeFormat("en", {
    timeZone: "UTC", year: "numeric", month: "long", day: "numeric",
    ...(weekday ? { weekday: "long" } : {}),
  }).format(new Date(`${date}T12:00:00Z`));
}

export function shiftDate(date: string, days: number): string {
  const value = new Date(`${date}T12:00:00Z`);
  value.setUTCDate(value.getUTCDate() + days);
  return value.toISOString().slice(0, 10);
}

export function diaryDateLabel(date: string): string {
  const [year, month, day] = date.split("-");
  const weekday = new Intl.DateTimeFormat("en-US", { weekday: "long", timeZone: "UTC" })
    .format(new Date(`${date}T12:00:00Z`));
  return `${month}/${day}/${year}, ${weekday}`;
}
