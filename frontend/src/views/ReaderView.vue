<template>
  <main class="reader-shell">
    <section class="reader-panel">
      <div class="reader-header">
        <h1 id="archive-title">{{ archive?.title || "..." }}</h1>
        <RouterLink class="icon-link" to="/" title="Return to Library"><ChevronDown :size="30" /></RouterLink>
      </div>
      <PageControls :page="page" :total="pageCount" @previous="previous" @next="next" @go="go" />
    </section>

    <section class="reader-stage" :class="{ loading }" @click="next">
      <div v-if="loading" class="loading-overlay">Loading...</div>
      <img v-if="pageCount" class="reader-image" :src="imageUrl" :alt="`Page ${page}`" @load="loading = false" />
      <div v-else class="empty-reader">Pages are not indexed yet. Return to the library and refresh after the worker finishes.</div>
    </section>

    <section class="reader-panel bottom-panel">
      <PageControls :page="page" :total="pageCount" @previous="previous" @next="next" @go="go" />
      <div class="reader-links">
        <a :href="imageUrl" target="_blank" rel="noreferrer">View full-size image</a>
        <a href="#" @click.prevent="showOverlay = !showOverlay">Archive Overview</a>
      </div>
    </section>

    <div v-if="showOverlay" class="overlay-shade" @click.self="showOverlay = false">
      <section class="base-overlay page-overlay">
        <h2 class="ih">Archive Overview</h2>
        <div class="overview-head">
          <img class="overview-cover" :src="`/api/archives/${archiveId}/cover`" alt="" />
          <div>
            <h3>{{ archive?.title }}</h3>
            <p>{{ pageCount }} pages</p>
            <div class="tag-line">
              <span v-for="tag in archive?.tags || []" :key="`${tag.namespace}:${tag.name}`" class="gt">
                {{ tag.namespace ? `${tag.namespace}:${tag.name}` : tag.name }}
              </span>
            </div>
          </div>
        </div>
        <div class="page-grid">
          <button v-for="item in pages" :key="item.page_index" type="button" class="page-chip" @click="go(item.page_index); showOverlay = false">
            {{ item.page_index }}
          </button>
        </div>
      </section>
    </div>
  </main>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { ChevronDown } from "lucide-vue-next";
import PageControls from "@/components/PageControls.vue";
import { fetchArchive, fetchPages } from "@/api/client";

const props = defineProps({
  archiveId: { type: String, required: true },
});

const archive = ref(null);
const pages = ref([]);
const page = ref(1);
const loading = ref(false);
const showOverlay = ref(false);

const pageCount = computed(() => pages.value.length);
const imageUrl = computed(() => `/api/archives/${props.archiveId}/page/${page.value}`);

function go(value) {
  if (!pageCount.value) return;
  page.value = Math.min(Math.max(Number(value) || 1, 1), pageCount.value);
  loading.value = true;
}

function previous() {
  go(page.value - 1);
}

function next() {
  go(page.value + 1);
}

function onKeydown(event) {
  if (event.key === "ArrowLeft" || event.key === "a") previous();
  if (event.key === "ArrowRight" || event.key === "d" || event.key === " ") next();
  if (event.key === "q") showOverlay.value = !showOverlay.value;
  if (event.key === "Backspace") window.location.href = "/";
}

onMounted(async () => {
  archive.value = await fetchArchive(props.archiveId);
  const payload = await fetchPages(props.archiveId);
  pages.value = payload.pages;
  loading.value = pageCount.value > 0;
  window.addEventListener("keydown", onKeydown);
});

onUnmounted(() => window.removeEventListener("keydown", onKeydown));
</script>
