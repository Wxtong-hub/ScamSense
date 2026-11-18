<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElDialog } from "element-plus";
import Glyph from "../components/Glyph.vue";
import { json, problem, stream } from "../api/client";
import { useTraining } from "../stores/training";
import {
  choices,
  people,
  phases,
  questions,
  type Choice,
  type Message,
  type RoleId,
  type Training,
} from "../types/training";
const store = useTraining(),
  route = useRoute(),
  router = useRouter();
const role = computed(
    () => people.find((r) => r.id === route.params.role) || people[0],
  ),
  rid = computed(() => role.value.id);
const active = computed(() => store.session?.status === "active"),
  loading = ref(false),
  sending = ref(false),
  finishing = ref(false);
const messages = ref<Message[]>([]),
  draft = ref(""),
  partial = ref(""),
  outgoing = ref(""),
  error = ref(""),
  box = ref<HTMLDivElement>();
const dialog = ref(false),
  early = ref(false),
  choice = ref<Choice | null>(null),
  reason = ref(""),
  finishError = ref("");
let epoch = 0,
  observer: IntersectionObserver | undefined,
  retry: { id: string; text: string; role: RoleId } | null = null;
const seen = new Set<string>(),
  acknowledgements = new Set<Promise<void>>();
function bottom() {
  if (box.value) box.value.scrollTop = box.value.scrollHeight;
}
function position() {
  const focus =
    typeof route.query.msg === "string"
      ? document.getElementById("msg-" + route.query.msg)
      : null;
  if (focus) focus.scrollIntoView({ block: "center" });
  else bottom();
}
function observe() {
  observer?.disconnect();
  if (!active.value || !box.value) return;
  observer = new IntersectionObserver(
    (entries) => {
      for (const e of entries) {
        const id = (e.target as HTMLElement).dataset.reply;
        if (
          !id ||
          seen.has(id) ||
          document.visibilityState !== "visible" ||
          !e.isIntersecting ||
          e.intersectionRatio < 0.95
        )
          continue;
        seen.add(id);
        observer?.unobserve(e.target);
        const p = json<void>(
          store.path(`/messages/${id}/seen`),
          store.token,
          {},
        )
          .catch(() => {
            seen.delete(id);
          })
          .finally(() => {
            acknowledgements.delete(p);
          });
        acknowledgements.add(p);
      }
    },
    { threshold: [0.95, 1] },
  );
  box.value
    .querySelectorAll("[data-reply]")
    .forEach((el) => observer?.observe(el));
}
async function load(clear = true) {
  const my = ++epoch,
    her = rid.value;
  observer?.disconnect();
  loading.value = true;
  if (clear) {
    messages.value = [];
    error.value = "";
    draft.value = "";
    retry = null;
  }
  try {
    const res = await json<{ items: Message[] }>(
      store.path(`/roles/${her}/messages`),
      store.token,
    );
    if (my !== epoch) return;
    messages.value = res.items;
    await nextTick();
    position();
    observe();
  } catch (e) {
    if (my === epoch) error.value = problem(e);
  } finally {
    if (my === epoch) loading.value = false;
  }
}
watch(
  () => [rid.value, route.query.msg],
  () => load(),
  { immediate: true },
);
document.addEventListener("visibilitychange", observe);
onBeforeUnmount(() => {
  epoch++;
  observer?.disconnect();
  document.removeEventListener("visibilitychange", observe);
});
async function send() {
  const text = draft.value.trim(),
    her = rid.value;
  if (!text || sending.value || !active.value) return;
  const key =
    retry?.text === text && retry.role === her ? retry.id : crypto.randomUUID();
  retry = { id: key, text, role: her };
  error.value = "";
  sending.value = true;
  partial.value = "";
  outgoing.value = text;
  draft.value = "";
  await nextTick();
  bottom();
  try {
    await stream(
      store.path(`/roles/${her}/messages`),
      store.token,
      { text, client_message_id: key },
      (chunk) => {
        partial.value += chunk;
        nextTick(bottom);
      },
    );
    retry = null;
  } catch (e) {
    error.value = problem(e);
    draft.value = text;
  } finally {
    outgoing.value = "";
    partial.value = "";
    try {
      await store.refresh();
      await load(false);
    } catch (e) {
      error.value = problem(e);
    }
    sending.value = false;
  }
}
function switchTo(r: RoleId) {
  if (!sending.value && r !== rid.value)
    router.push({ name: "room", params: { role: r } });
}
function openDecision(end = false) {
  early.value = end;
  finishError.value = "";
  dialog.value = true;
}
async function finish() {
  if (finishing.value || (!early.value && !choice.value) || !store.session)
    return;
  finishing.value = true;
  finishError.value = "";
  try {
    await Promise.all([...acknowledgements]);
    const payload = {
      request_id: crypto.randomUUID(),
      expected_version: store.session.version,
      ...(early.value
        ? {}
        : { choice: choice.value, reason: reason.value.trim() }),
    };
    store.session = await json<Training>(
      store.path(early.value ? "/end" : "/decision"),
      store.token,
      payload,
    );
    dialog.value = false;
    await router.push({ name: "report" });
  } catch (e) {
    finishError.value = problem(e);
    try {
      await store.refresh();
      if (store.session?.status !== "active") {
        dialog.value = false;
        await router.push({ name: "report" });
      }
    } catch {
      /* Keep the actionable error above. */
    }
  } finally {
    finishing.value = false;
  }
}
</script>
<template>
  <section class="workspace">
    <div class="page-strap">
      <span><i /> DIALOGUE ROOM</span><RouterLink to="/">返回训练台</RouterLink>
    </div>
    <div class="section-head">
      <div>
        <div class="kicker">CASE 001 / 校园求职</div>
        <h1 class="page-title">现场对话</h1>
      </div>
      <span class="tag"><i /> {{ active ? "训练进行中" : "只读回看" }}</span>
    </div>
    <div class="room-grid">
      <aside class="side panel">
        <div class="side-heading"><b>联系人</b><small>03</small></div>
        <div class="role-list">
          <button
            v-for="p in people"
            :key="p.id"
            :class="['role-btn', { selected: p.id === rid }]"
            :aria-pressed="p.id === rid"
            :disabled="sending"
            @click="switchTo(p.id)"
          >
            <span class="avatar" :class="p.id">{{ p.name[0] }}</span
            ><span
              ><b>{{ p.name }}</b
              ><small>{{ p.title }}</small></span
            >
          </button>
        </div>
        <div class="side-stage">
          <div class="kicker">CURRENT STAGE</div>
          <b
            >{{ store.session?.phase }} ·
            {{ phases[store.session?.phase || "S0"] }}</b
          >
          <p>核实和决策都可以提前进行，不必聊满固定轮数。</p>
        </div>
        <div class="side-actions" v-if="active">
          <button
            class="btn primary"
            :disabled="sending || loading"
            @click="openDecision()"
          >
            <Glyph name="flag" />提交决定</button
          ><button
            class="subtle"
            :disabled="sending"
            @click="openDecision(true)"
          >
            提前结束训练
          </button>
        </div>
        <RouterLink v-else class="btn primary" to="/report"
          >返回复盘 <Glyph name="arrow"
        /></RouterLink>
      </aside>
      <article class="conversation panel">
        <header class="con-head">
          <div class="avatar" :class="rid">{{ role.name[0] }}</div>
          <div>
            <h2>{{ role.name }}</h2>
            <span>{{ role.title }}</span>
          </div>
          <span class="private"><Glyph name="lock" :size="14" />独立私聊</span>
        </header>
        <div class="log" ref="box" role="log" aria-label="对话记录">
          <div v-if="loading && !messages.length" class="empty">
            正在读取对话…
          </div>
          <div v-else-if="!messages.length && !outgoing" class="empty">
            <span class="empty-ico"><Glyph name="chat" :size="25" /></span
            ><b>与{{ role.name }}的私聊</b
            ><span>{{
              active
                ? "从下面的问题开始，或用你自己的话提问。"
                : "这场训练没有与该角色对话。"
            }}</span>
          </div>
          <div
            v-for="m in messages"
            :key="m.id"
            class="line"
            :class="[m.sender, { highlight: m.id === route.query.msg }]"
            :id="'msg-' + m.id"
            :data-reply="m.sender === 'role' ? m.id : undefined"
          >
            <small>{{ m.sender === "user" ? "你" : role.name }}</small>
            <p>{{ m.content }}</p>
          </div>
          <template v-if="outgoing"
            ><div class="line user">
              <small>你</small>
              <p>{{ outgoing }}</p>
            </div>
            <div class="line role">
              <small>{{ role.name }} · 规则回复</small>
              <p>{{ partial || "…" }}</p>
            </div></template
          >
        </div>
        <div v-if="error" class="error inline-error" role="alert">
          {{ error }}
          <button class="text-btn" @click="load(false)">重读对话</button>
        </div>
        <form v-if="active" class="composer" @submit.prevent="send">
          <div class="chips">
            <button
              v-for="q in questions[rid]"
              type="button"
              :disabled="sending || loading"
              :key="q"
              @click="draft = q"
            >
              {{ q }}
            </button>
          </div>
          <label class="sr" for="message-text">你的提问</label
          ><textarea
            v-model="draft"
            id="message-text"
            maxlength="500"
            rows="2"
            placeholder="输入你的提问或判断，仅使用虚构信息…"
            :disabled="sending || loading"
            @keydown.ctrl.enter.prevent="send"
          />
          <div class="compose-foot">
            <small
              ><Glyph name="shield" :size="14" /> 不要输入真实个人资料</small
            ><button
              class="btn primary"
              :disabled="sending || loading || !draft.trim()"
            >
              {{ sending ? "回复中…" : "发送" }} <Glyph name="up" :size="15" />
            </button>
          </div>
        </form>
        <p v-else class="readonly">训练已结束；这里保留原始对话供复盘核对。</p>
      </article>
    </div>
  </section>
  <ElDialog
    v-model="dialog"
    :title="early ? '提前结束训练？' : '作出你的决定'"
    width="min(510px, 94vw)"
    append-to-body
    ><div v-if="early" class="help-body">
      现有对话仍会生成复盘，没有足够证据的维度会标为“证据不足”。结束后不能继续发消息。
    </div>
    <div v-else class="decision">
      <p>根据目前掌握的信息，你准备怎么做？提交后会结束本次训练。</p>
      <div class="choice-grid">
        <label
          v-for="(label, key) in choices"
          :key="key"
          :class="{ picked: choice === key }"
          ><input
            v-model="choice"
            type="radio"
            :value="key"
            name="decision"
          />{{ label }}</label
        >
      </div>
      <label for="reason">你的依据 <small>选填，最多 500 字</small></label
      ><textarea
        id="reason"
        v-model="reason"
        maxlength="500"
        rows="3"
        placeholder="哪些信息得到核实？哪些仍不足以作判断？"
      />
    </div>
    <p v-if="finishError" class="error" role="alert">{{ finishError }}</p>
    <template #footer
      ><div class="modal-foot">
        <button class="btn light" @click="dialog = false">返回对话</button
        ><button
          class="btn primary"
          :disabled="finishing || (!early && !choice)"
          @click="finish"
        >
          {{ finishing ? "生成中…" : "确认并查看复盘" }} <Glyph name="arrow" />
        </button></div></template
  ></ElDialog>
</template>
