<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useTraining } from "../stores/training";
import { json, problem } from "../api/client";
import { choices, people, type Report } from "../types/training";
import Glyph from "../components/Glyph.vue";
const store = useTraining(),
  router = useRouter(),
  report = ref<Report | null>(null),
  error = ref(""),
  busy = ref(false);
async function load() {
  error.value = "";
  try {
    report.value = await json<Report>(store.path("/report"), store.token);
  } catch (e) {
    error.value = problem(e);
  }
}
async function again() {
  busy.value = true;
  try {
    await store.start();
    await router.push({ name: "room" });
  } catch (e) {
    error.value = problem(e);
  } finally {
    busy.value = false;
  }
}
onMounted(load);
</script>
<template>
  <section class="report">
    <div class="page-strap">
      <span><i /> FIELD REPORT</span><RouterLink to="/">返回训练台</RouterLink>
    </div>
    <div class="section-head">
      <div>
        <div class="kicker">CASE 001 / AFTER ACTION REVIEW</div>
        <h1 class="page-title">训练复盘</h1>
      </div>
      <span class="tag"><Glyph name="check" :size="14" />已结束</span>
    </div>
    <p v-if="error" class="error" role="alert">
      {{ error }} <button class="text-btn" @click="load">重新读取</button>
    </p>
    <p v-if="!report && !error">正在整理复盘…</p>
    <template v-if="report"
      ><div class="score-banner">
        <div>
          <div class="kicker">YOUR DECISION</div>
          <h2>
            {{
              report.decision ? choices[report.decision.choice] : "提前结束训练"
            }}
          </h2>
          <p>{{ report.decision?.reason || "本场未填写决策理由。" }}</p>
        </div>
        <div class="score-box">
          <small>综合表现 / 100</small><strong>{{ report.total ?? "—" }}</strong
          ><small>{{
            report.total === null
              ? "证据不足，不计算总分"
              : "按四项训练权重计算"
          }}</small>
        </div>
      </div>
      <div class="section-head tight">
        <div>
          <div class="kicker">EVIDENCE REVIEW</div>
          <h2>四个维度，看依据</h2>
        </div>
      </div>
      <div class="report-grid">
        <article
          v-for="(d, i) in report.dimensions"
          :key="d.key"
          class="panel dimension"
        >
          <div class="dim-top">
            <small>0{{ i + 1 }} / {{ d.weight }}%</small
            ><strong>{{
              d.score === null ? "证据不足" : `${d.score} 分`
            }}</strong>
          </div>
          <h3>{{ d.label }}</h3>
          <p>{{ d.explanation }}</p>
          <div v-for="(e, j) in d.evidence" :key="j" class="quote">
            <RouterLink
              v-if="e.role_id && e.message_id"
              :to="{
                name: 'room',
                params: { role: e.role_id },
                query: { msg: e.message_id },
              }"
              ><Glyph name="link" :size="13" /> 与{{
                people.find((r) => r.id === e.role_id)?.name
              }}的对话 · 回看原文</RouterLink
            ><small v-else>决策理由</small>
            <blockquote>{{ e.excerpt }}</blockquote>
          </div>
        </article>
      </div>
      <article class="panel guidance">
        <Glyph name="lens" :size="25" />
        <div>
          <h3>下次训练可以试试</h3>
          <p v-for="s in report.strengths" :key="s">已做到：{{ s }}</p>
          <ul>
            <li v-for="s in report.suggestions" :key="s">{{ s }}</li>
          </ul>
        </div>
      </article>
      <div class="report-end">
        <span>训练量表 {{ report.rubric_version }} · 仅作学习反馈</span
        ><button class="btn primary" :disabled="busy" @click="again">
          再练一次 <Glyph name="arrow" />
        </button></div
    ></template>
  </section>
</template>
