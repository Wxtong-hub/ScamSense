<script setup lang="ts">
const paths: Record<string, string> = {
  arrow: "M4 12h15m-6-6 6 6-6 6",
  up: "M12 19V5m-6 6 6-6 6 6",
  back: "M20 12H5m6-6-6 6 6 6",
  book: "M4 5h6l2 2 2-2h6v14h-6l-2 1-2-1H4z M12 7v13",
  shield: "M12 2l8 3v6c0 5-4 8-8 11-4-3-8-6-8-11V5z M8 12l3 3 5-6",
  chat: "M4 4h16v12H9l-5 4z M8 8h8m-8 4h5",
  lens: "M16.5 16.5 21 21 M18 10.5a7.5 7.5 0 1 1-15 0 7.5 7.5 0 0 1 15 0z",
  file: "M6 3h8l4 4v14H6z M14 3v5h4 M9 12h6m-6 4h6",
  lock: "M5 10h14v10H5z M8 10V7a4 4 0 1 1 8 0v3",
  clock: "M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z M12 6v6l4 2",
  flag: "M5 21V4m0 1c5-4 9 4 14 0v9c-5 4-9-4-14 0",
  layers: "M3 8l9-5 9 5-9 5z M3 12l9 5 9-5 M3 16l9 5 9-5",
  check: "M4 13l5 5L20 6",
  info: "M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z M12 11v6m0-11v1",
  link: "M9 15l6-6 M8 13l-2 2a3 3 0 0 0 4 4l3-3 M16 11l2-2a3 3 0 0 0-4-4l-3 3",
};
defineProps<{ name: string; size?: number }>();
</script>
<template>
  <svg
    aria-hidden="true"
    :width="size || 18"
    :height="size || 18"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.7"
    stroke-linecap="round"
    stroke-linejoin="round"
  >
    <path :d="paths[name]" />
  </svg>
</template>
