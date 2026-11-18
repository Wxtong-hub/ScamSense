<script setup lang="ts">
import { ref } from "vue";
import { ElDialog } from "element-plus";
import Glyph from "./components/Glyph.vue";
const help = ref(false),
  mark = `${import.meta.env.BASE_URL}mark.svg`;
</script>
<template>
  <header class="top">
    <div class="shell top-inner">
      <RouterLink class="brand" to="/" aria-label="拆招训练首页"
        ><img :src="mark" alt="" /><span>拆招</span><b>ScamSense</b></RouterLink
      >
      <div class="top-tools">
        <span class="labtag"><i /> 求职安全实验室</span
        ><button class="subtle help" @click="help = true">
          <Glyph name="book" />训练说明
        </button>
      </div>
    </div>
  </header>
  <main class="shell"><RouterView /></main>
  <footer class="shell foot">
    <span>SCAMSENSE <b>/</b> 拆招实验室</span
    ><span>虚构训练 · 不处理真实求职申请</span>
  </footer>
  <ElDialog
    v-model="help"
    title="训练说明"
    width="min(480px, 92vw)"
    append-to-body
    ><div class="help-body">
      <p>
        你扮演一名正在了解实习机会的学生。三位角色分别与你私聊，看不到彼此的消息。
      </p>
      <ol>
        <li>选一位联系人，自由提问或从推荐问题开始。</li>
        <li>比较不同来源，明确说出你发现的疑点。</li>
        <li>提交决定和理由，在复盘中回看自己的原话。</li>
      </ol>
      <p class="notice">
        <Glyph
          name="shield"
        />本版使用本地规则，不调用大模型。只用虚构称呼，不要输入真实联系方式、证件或住址。训练记录有效期
        7 天。
      </p>
    </div>
    <template #footer
      ><button class="btn primary" @click="help = false">
        明白了
      </button></template
    ></ElDialog
  >
</template>
