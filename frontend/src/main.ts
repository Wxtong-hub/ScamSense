import { createApp } from "vue";
import { createPinia } from "pinia";
import { createRouter, createWebHashHistory } from "vue-router";
import "element-plus/es/components/dialog/style/css";
import "./style.css";
import App from "./App.vue";
import Home from "./views/Home.vue";
import Room from "./views/Room.vue";
import ReportView from "./views/Report.vue";
import { useTraining } from "./stores/training";

const app = createApp(App);
app.use(createPinia());
const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: "/", name: "home", component: Home },
    { path: "/room/:role?", name: "room", component: Room },
    { path: "/report", name: "report", component: ReportView },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
  scrollBehavior(to, from) {
    if (to.name !== from.name) return { top: 0 };
  },
});
router.beforeEach(async (to) => {
  if (to.name === "home") return true;
  const store = useTraining();
  if (!store.session && store.id) {
    try {
      await store.refresh();
    } catch {
      return { name: "home" };
    }
  }
  if (!store.session) return { name: "home" };
  if (to.name === "report" && store.session.status === "active")
    return { name: "room" };
  return true;
});
app.use(router).mount("#app");
