const base = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(
  /\/$/,
  "",
);
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}
async function call(
  path: string,
  token: string,
  body?: unknown,
  accept = "application/json",
) {
  const headers: Record<string, string> = { Accept: accept };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  let response: Response;
  try {
    response = await fetch(base + path, {
      method: body === undefined ? "GET" : "POST",
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store",
    });
  } catch {
    throw new Error("暂时连不上训练服务，请确认后端已启动，再试一次。");
  }
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new ApiError(
      response.status,
      data?.error?.message || `服务暂不可用（${response.status}）。`,
    );
  }
  return response;
}
export async function json<T>(
  path: string,
  token = "",
  body?: unknown,
): Promise<T> {
  const res = await call(path, token, body);
  return res.status === 204 ? (undefined as T) : res.json();
}
export async function stream(
  path: string,
  token: string,
  body: unknown,
  append: (text: string) => void,
) {
  const res = await call(path, token, body, "text/event-stream");
  if (
    !res.body ||
    !res.headers.get("content-type")?.includes("text/event-stream")
  )
    throw new Error("没有收到对话流，请重新读取历史。");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let pending = "",
    complete = false;
  try {
    while (true) {
      const part = await reader.read();
      pending += decoder.decode(part.value, { stream: !part.done });
      pending = pending.replaceAll("\r\n", "\n");
      let end: number;
      while ((end = pending.indexOf("\n\n")) !== -1) {
        const lines = pending.slice(0, end).split("\n");
        pending = pending.slice(end + 2);
        const type = lines
          .find((l) => l.startsWith("event:"))
          ?.slice(6)
          .trim();
        const payload = lines
          .filter((l) => l.startsWith("data:"))
          .map((l) => l.slice(5).trimStart())
          .join("\n");
        if (!payload) continue;
        const data = JSON.parse(payload);
        if (type === "delta") append(data.text);
        if (type === "error") throw new Error("回复已中断，请重新读取历史。");
        if (type === "complete") complete = true;
      }
      if (part.done) break;
    }
  } finally {
    reader.releaseLock();
  }
  if (!complete) throw new Error("连接在回复完成前断开，可重新读取对话。");
}
export const problem = (error: unknown) =>
  error instanceof Error ? error.message : "暂时无法完成，请重试。";
