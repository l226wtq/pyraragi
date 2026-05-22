import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import App from "./App.vue";
import LibraryView from "./views/LibraryView.vue";
import ConversionView from "./views/ConversionView.vue";
import JobsView from "./views/JobsView.vue";
import ReaderView from "./views/ReaderView.vue";
import UploadView from "./views/UploadView.vue";
import "./styles.css";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: LibraryView },
    { path: "/upload", component: UploadView },
    { path: "/convert", component: ConversionView },
    { path: "/jobs", component: JobsView },
    { path: "/reader/:archiveId", component: ReaderView, props: true },
  ],
});

createApp(App).use(router).mount("#app");
