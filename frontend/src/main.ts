import { createApp } from "vue";
import { createPinia } from "pinia";
import router from "@/router";
import App from "@/App.vue";
import "@/styles/tokens.css";
import "@/styles/prototype.css"; // 1:1 prototype component styles

const app = createApp(App);
app.use(createPinia());
app.use(router);

// Global logout signal from the axios refresh interceptor.
window.addEventListener("hermes:logout", () => {
  router.push({ name: "login" });
});

app.mount("#app");
