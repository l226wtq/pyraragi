<template>
  <main class="ido library-panel">
    <h1 class="ih">Pyrragi Archive Index</h1>

    <section class="toppane">
      <div class="idi">
        <div class="category-row">
          <button class="favtag-btn toggled" type="button">All Archives</button>
          <button class="favtag-btn" type="button">New</button>
          <button class="favtag-btn" type="button">Untagged</button>
        </div>
        <div class="search-line">
          <input
            v-model="draftQuery"
            class="stdinput search-input"
            type="search"
            placeholder="Search Title, Artist, Series, Language or Tags"
            @keydown.enter="applySearch"
          />
          <button class="stdbtn" type="button" @click="applySearch"><Search :size="15" /> Apply Filter</button>
          <button class="stdbtn" type="button" @click="clearSearch"><X :size="15" /> Clear Filter</button>
          <button class="stdbtn" type="button" @click="toggleSelect"><CheckSquare :size="15" /> Select Archives</button>
        </div>
      </div>

      <section class="option-flyout carousel-strip">
        <button class="collapsible-title" type="button" @click="carouselOpen = !carouselOpen">
          <ChevronRight :class="{ rotated: carouselOpen }" :size="18" />
          <span>Recently indexed</span>
        </button>
        <div class="collapsible-right">
          <button class="icon-link" type="button" @click="loadArchives"><RefreshCw :size="19" /></button>
          <button class="icon-link" type="button" @click="scan"><ScanSearch :size="19" /></button>
          <button class="icon-link" type="button"><Ellipsis :size="21" /></button>
        </div>
        <div v-if="carouselOpen" class="carousel-body">
          <ArchiveCard v-for="archive in archives.slice(0, 8)" :key="`recent-${archive.id}`" :archive="archive" />
          <div v-if="!archives.length && !loading" class="empty-state">No results here.</div>
          <div v-if="loading" class="empty-state">Loading...</div>
        </div>
      </section>

      <div class="table-options">
        <div class="thumbnail-options">
          <span>Sort by:</span>
          <select v-model="sort" class="favtag-btn" @change="loadArchives">
            <option value="title">Title</option>
            <option value="created">Date</option>
            <option value="last_read">Last read</option>
            <option value="pages">Pages</option>
            <option value="size">Size</option>
          </select>
          <button class="table-option" type="button" @click="toggleDirection">
            <ArrowDownAZ v-if="!desc" :size="24" />
            <ArrowUpZA v-else :size="24" />
          </button>
        </div>
        <div class="compact-options">
          <span>View:</span>
          <button class="favtag-btn" :class="{ toggled: viewMode === 'thumbs' }" type="button" @click="viewMode = 'thumbs'">
            Thumbnails
          </button>
          <button class="favtag-btn" :class="{ toggled: viewMode === 'list' }" type="button" @click="viewMode = 'list'">
            Compact
          </button>
        </div>
        <div class="page-summary">{{ total }} archives</div>
      </div>

      <div v-if="error" class="json-error">{{ error }}</div>

      <div v-if="viewMode === 'thumbs'" class="thumbs-container">
        <ArchiveCard v-for="archive in archives" :key="archive.id" :archive="archive" />
      </div>
      <ArchiveList v-else :archives="archives" />
    </section>
  </main>
</template>

<script setup>
import { onMounted, ref, watch } from "vue";
import {
  ArrowDownAZ,
  ArrowUpZA,
  CheckSquare,
  ChevronRight,
  Ellipsis,
  RefreshCw,
  ScanSearch,
  Search,
  X,
} from "lucide-vue-next";
import { fetchArchives, scanLibrary } from "@/api/client";
import ArchiveCard from "@/components/ArchiveCard.vue";
import ArchiveList from "@/components/ArchiveList.vue";

const archives = ref([]);
const total = ref(0);
const loading = ref(false);
const error = ref("");
const draftQuery = ref("");
const query = ref("");
const sort = ref(localStorage.getItem("pyrragi.sort") || "title");
const desc = ref(localStorage.getItem("pyrragi.desc") === "true");
const viewMode = ref(localStorage.getItem("pyrragi.viewMode") || "thumbs");
const carouselOpen = ref(localStorage.getItem("pyrragi.carouselOpen") !== "false");
const selectMode = ref(false);

watch(viewMode, (value) => localStorage.setItem("pyrragi.viewMode", value));
watch(carouselOpen, (value) => localStorage.setItem("pyrragi.carouselOpen", String(value)));

async function loadArchives() {
  loading.value = true;
  error.value = "";
  localStorage.setItem("pyrragi.sort", sort.value);
  localStorage.setItem("pyrragi.desc", String(desc.value));
  try {
    const payload = await fetchArchives({
      q: query.value,
      sort: sort.value,
      desc: String(desc.value),
      limit: "120",
      offset: "0",
    });
    archives.value = payload.data;
    total.value = payload.total;
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

function applySearch() {
  query.value = draftQuery.value.trim();
  loadArchives();
}

function clearSearch() {
  draftQuery.value = "";
  query.value = "";
  loadArchives();
}

function toggleDirection() {
  desc.value = !desc.value;
  loadArchives();
}

function toggleSelect() {
  selectMode.value = !selectMode.value;
}

async function scan() {
  error.value = "";
  try {
    await scanLibrary();
    error.value = "Scan queued. Refresh in a moment.";
  } catch (err) {
    error.value = err.message;
  }
}

onMounted(loadArchives);
</script>
