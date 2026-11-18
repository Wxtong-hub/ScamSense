<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useTraining } from "../stores/training";
import { people } from "../types/training";
import { problem } from "../api/client";
import Glyph from "../components/Glyph.vue";
import FieldDiagram from "../components/FieldDiagram.vue";
const store = useTraining(),
  router = useRouter(),
  busy = ref(false),
  error = ref("");
const intros = [
  "从岗位职责与面试流程开始了解。",
  "向项目对接人核对招聘说明。",
  "听听校园消息是怎样传来的。",
];
onMounted(async () => {
  if (store.id && !store.session) {
    busy.value = true;
    try {
      await store.refresh();
    } catch (e) {
      error.value = problem(e);
    } finally {
      busy.value = false;
    }
  }
});
async function enter(fresh = false) {
  busy.value = true;
  error.value = "";
  try {
    if (fresh || !store.id) await store.start();
    else await store.refresh();
    await router.push({
      name: store.session?.status === "active" ? "room" : "report",
    });
  } catch (e) {
    error.value = problem(e);
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <section class="home">
    <div class="page-strap">
      <span><i /> TRAINING DESK</span><span>实践训练台 <b>/</b> 案例库</span>
    </div>
    <article class="hero">
      <div class="hero-copy">
        <div class="eyebrow">
          <span class="case-tag">CASE 001</span> 校园求职 · 本地规则演示
        </div>
        <h1>一份招聘邀约，<br /><em>几分可信？</em></h1>
        <p class="lede">
          同一条招聘消息，三种不同的说法。<br />在对话中找证据，为自己的下一步作判断。
        </p>
        <div class="cta">
          <button class="btn primary" :disabled="busy" @click="enter()">
            {{
              busy
                ? "正在连接…"
                : store.session
                  ? store.session.status === "active"
                    ? "继续本次训练"
                    : "查看上次复盘"
                  : "进入训练"
            }}
            <Glyph name="arrow" /></button
          ><button
            v-if="store.session && store.session.status !== 'active'"
            class="subtle"
            :disabled="busy"
            @click="enter(true)"
          >
            重新训练</button
          ><span v-else class="muted inline"
            ><Glyph name="clock" :size="15" /> 自主节奏</span
          >
        </div>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
      </div>
      <FieldDiagram />
    </article>
    <section class="contacts">
      <div class="section-head">
        <div>
          <div class="kicker">FIELD CONTACTS</div>
          <h2>场景联系人</h2>
        </div>
        <span class="section-meta">03 人 <b>/</b> 独立对话</span>
      </div>
      <div class="cards">
        <article v-for="(r, i) in people" :key="r.id" class="contact">
          <span class="avatar" :class="r.id">{{ r.name[0] }}</span>
          <div>
            <small>CONTACT 0{{ i + 1 }}</small>
            <h3>
              {{ r.name }} <span>{{ r.title }}</span>
            </h3>
            <p>{{ intros[i] }}</p>
          </div>
        </article>
      </div>
    </section>
    <div class="home-note">
      <Glyph name="shield" />
      <p>
        <strong>只练判断，不交资料。</strong>
        所有角色与单位均为虚构，请勿输入真实个人信息。
      </p>
      <span class="version">规则演示 / v0.1</span>
    </div>
  </section>
</template>
