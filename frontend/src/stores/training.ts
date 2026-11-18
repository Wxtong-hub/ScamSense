import { defineStore } from "pinia";
import { ref } from "vue";
import { ApiError, json } from "../api/client";
import type { Training } from "../types/training";
const KEY = "scamsense.v1";
export const useTraining = defineStore("training", () => {
  let saved: { id?: string; token?: string } = {};
  try {
    saved = JSON.parse(sessionStorage.getItem(KEY) || "{}") || {};
  } catch {
    /* Invalid local state is disposable. */
  }
  const id = ref(saved.id || ""),
    token = ref(saved.token || ""),
    session = ref<Training | null>(null);
  function clear() {
    id.value = "";
    token.value = "";
    session.value = null;
    sessionStorage.removeItem(KEY);
  }
  function path(suffix = "") {
    return `/sessions/${id.value}${suffix}`;
  }
  async function refresh() {
    if (!id.value || !token.value) return;
    try {
      session.value = await json<Training>(path(), token.value);
    } catch (e) {
      if (e instanceof ApiError && [401, 404].includes(e.status)) clear();
      throw e;
    }
  }
  async function start() {
    const { session_token, ...result } = await json<
      Training & { session_token: string }
    >("/sessions", "", {});
    session.value = result;
    id.value = result.session_id;
    token.value = session_token;
    sessionStorage.setItem(
      KEY,
      JSON.stringify({ id: id.value, token: token.value }),
    );
  }
  return { id, token, session, path, refresh, start };
});
