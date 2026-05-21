<template>
  <main class="ido upload-panel">
    <h1 class="ih">Adding Archives to the Library</h1>
    <p class="subtle">Add files to your Pyrragi instance from your computer. URL downloaders and plugins will come later.</p>

    <div class="upload-layout">
      <section class="left-column">
        <h2 class="ih">From your computer</h2>
        <p>You can drag and drop files into this window, or click the upload button.</p>

        <label
          class="drop-zone"
          :class="{ dragging }"
          @dragover.prevent="dragging = true"
          @dragleave.prevent="dragging = false"
          @drop.prevent="onDrop"
        >
          <Download :size="34" />
          <span>Add from your computer</span>
          <input type="file" accept=".zip,.cbz" multiple @change="onSelect" />
        </label>

        <label class="field-label">
          Tags
          <input v-model="tags" class="stdinput" type="text" placeholder="artist:name, series:title, language:english" />
        </label>

        <button class="stdbtn primary" type="button" :disabled="!files.length || uploading" @click="upload">
          <UploadCloud :size="16" /> Upload {{ files.length || "" }}
        </button>

        <RouterLink class="stdbtn return-link" to="/">Return to Library</RouterLink>
      </section>

      <section class="right-column">
        <h2 class="ih">{{ progressTitle }}</h2>
        <div class="progress">
          <div class="bar" :style="{ width: `${progress}%` }"></div>
        </div>
        <table class="itg upload-table">
          <tbody>
            <tr v-for="item in queue" :key="item.name" :class="item.status === 'failed' ? 'failed' : ''">
              <td>{{ item.name }}</td>
              <td>{{ item.status }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>
  </main>
</template>

<script setup>
import { computed, ref } from "vue";
import { Download, UploadCloud } from "lucide-vue-next";
import { uploadArchive } from "@/api/client";

const files = ref([]);
const queue = ref([]);
const tags = ref("");
const uploading = ref(false);
const dragging = ref(false);

const progress = computed(() => {
  if (!queue.value.length) return 0;
  const done = queue.value.filter((item) => item.status === "queued" || item.status === "failed").length;
  return Math.round((done / queue.value.length) * 100);
});
const progressTitle = computed(() => (queue.value.length ? `${progress.value}% processed` : "No uploads queued"));

function onSelect(event) {
  files.value = Array.from(event.target.files || []);
  queue.value = files.value.map((file) => ({ name: file.name, status: "waiting" }));
}

function onDrop(event) {
  dragging.value = false;
  files.value = Array.from(event.dataTransfer.files || []).filter((file) => /\.(zip|cbz)$/i.test(file.name));
  queue.value = files.value.map((file) => ({ name: file.name, status: "waiting" }));
}

async function upload() {
  uploading.value = true;
  for (const file of files.value) {
    const item = queue.value.find((entry) => entry.name === file.name);
    item.status = "uploading";
    const form = new FormData();
    form.append("file", file);
    form.append("tags", tags.value);
    try {
      await uploadArchive(form);
      item.status = "queued";
    } catch (err) {
      item.status = "failed";
      item.error = err.message;
    }
  }
  uploading.value = false;
}
</script>
