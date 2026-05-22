<template>
  <main class="ido conversion-panel">
    <h1 class="ih">Archive Conversion</h1>

    <div class="conversion-layout">
      <section class="left-column">
        <h2 class="ih">New conversion</h2>

        <label class="field-label">
          Source path
          <input v-model="form.source_path" class="stdinput wide-input" type="text" placeholder="/home/lyy/Books" />
        </label>

        <label class="field-label">
          Destination path
          <input v-model="form.destination_path" class="stdinput wide-input" type="text" placeholder="storage/archives or /data/archives" />
        </label>

        <div class="choice-row">
          <span>Output:</span>
          <button
            class="favtag-btn"
            :class="{ toggled: form.output_extension === 'cbz' }"
            type="button"
            @click="form.output_extension = 'cbz'"
          >
            CBZ
          </button>
          <button
            class="favtag-btn"
            :class="{ toggled: form.output_extension === 'zip' }"
            type="button"
            @click="form.output_extension = 'zip'"
          >
            ZIP
          </button>
        </div>

        <label class="check-line">
          <input v-model="form.overwrite" type="checkbox" />
          <span>Overwrite existing output</span>
        </label>
        <label class="check-line danger-check">
          <input v-model="form.delete_source" type="checkbox" />
          <span>Delete source after success</span>
        </label>

        <button class="stdbtn primary" type="button" :disabled="submitting || !form.source_path.trim()" @click="startJob">
          <RefreshCw :size="16" /> Start conversion
        </button>

        <section class="upload-source-box">
          <h2 class="ih">Upload sources</h2>
          <label class="drop-zone compact-drop">
            <Archive :size="28" />
            <span>{{ selectedFiles.length ? `${selectedFiles.length} selected` : "Select RAR or 7Z files" }}</span>
            <input type="file" accept=".rar,.cbr,.7z,.cb7" multiple @change="onFileSelect" />
          </label>
          <button class="stdbtn" type="button" :disabled="!selectedFiles.length || uploading" @click="uploadSelected">
            <UploadCloud :size="16" /> Convert selected
          </button>
        </section>

        <div v-if="error" class="json-error">{{ error }}</div>

        <section class="tool-strip">
          <h2 class="ih">Tools</h2>
          <div class="tool-grid">
            <span v-for="tool in toolRows" :key="tool.name" class="tool-chip" :class="{ ready: tool.ready }">
              {{ tool.name }}: {{ tool.ready ? "ready" : "missing" }}
            </span>
          </div>
        </section>
      </section>

      <section class="right-column">
        <h2 class="ih">Current progress</h2>
        <div class="progress">
          <div class="bar" :style="{ width: `${activeProgress}%` }"></div>
        </div>
        <div class="job-summary">
          <strong>{{ activeJob ? activeJob.status : "idle" }}</strong>
          <span>{{ activeProgress }}%</span>
        </div>
        <div v-if="activeJob" class="job-detail">
          <div>Current: {{ activeJob.current_source || "-" }}</div>
          <div>
            Done {{ activeJob.completed_files }} / {{ activeJob.total_files }},
            skipped {{ activeJob.skipped_files }},
            failed {{ activeJob.failed_files }}
          </div>
        </div>
        <pre v-if="activeJob?.log" class="job-log">{{ activeJob.log }}</pre>
      </section>
    </div>

    <section class="history-section">
      <div class="history-head">
        <h2 class="ih">History</h2>
        <button class="icon-link" type="button" @click="loadJobs"><RefreshCw :size="18" /></button>
      </div>
      <table class="itg conversion-table">
        <thead>
          <tr>
            <th>Status</th>
            <th>Source</th>
            <th>Output</th>
            <th>Progress</th>
            <th>Started</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="job in jobs" :key="job.id" :class="rowClass(job)">
            <td>{{ job.status }}</td>
            <td>{{ job.source_path }}</td>
            <td>{{ outputLabel(job) }}</td>
            <td>{{ job.completed_files }}/{{ job.total_files }} - S {{ job.skipped_files }} - F {{ job.failed_files }}</td>
            <td>{{ formatDate(job.created_at) }}</td>
          </tr>
          <tr v-if="!jobs.length">
            <td colspan="5">No conversion history.</td>
          </tr>
        </tbody>
      </table>
    </section>
  </main>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from "vue";
import { Archive, RefreshCw, UploadCloud } from "lucide-vue-next";
import { createConversionJob, fetchConversionJobs, fetchConversionTools, uploadConversionArchive } from "@/api/client";

const form = reactive({
  source_path: "",
  destination_path: "",
  output_extension: "cbz",
  overwrite: false,
  delete_source: false,
});
const jobs = ref([]);
const tools = ref({});
const error = ref("");
const submitting = ref(false);
const uploading = ref(false);
const selectedFiles = ref([]);
let timer = null;

const activeJob = computed(() => jobs.value.find((job) => ["queued", "running"].includes(job.status)) || jobs.value[0] || null);
const activeProgress = computed(() => progressFor(activeJob.value));
const toolRows = computed(() => [
  { name: "zip", ready: Boolean(tools.value.zip) },
  { name: "unrar", ready: Boolean(tools.value.unrar) },
  { name: "7z", ready: Boolean(tools.value.seven_zip) },
  { name: "unar", ready: Boolean(tools.value.unar) },
]);

async function startJob() {
  submitting.value = true;
  error.value = "";
  try {
    await createConversionJob({
      source_path: form.source_path.trim(),
      destination_path: form.destination_path.trim(),
      output_extension: form.output_extension,
      overwrite: form.overwrite,
      delete_source: form.delete_source,
    });
    await loadJobs();
  } catch (err) {
    error.value = err.message;
  } finally {
    submitting.value = false;
  }
}

function onFileSelect(event) {
  selectedFiles.value = Array.from(event.target.files || []);
}

async function uploadSelected() {
  uploading.value = true;
  error.value = "";
  for (const file of selectedFiles.value) {
    const body = new FormData();
    body.append("file", file);
    body.append("destination_path", form.destination_path.trim());
    body.append("output_extension", form.output_extension);
    body.append("overwrite", String(form.overwrite));
    try {
      await uploadConversionArchive(body);
      await loadJobs();
    } catch (err) {
      error.value = err.message;
      break;
    }
  }
  uploading.value = false;
}

async function loadJobs() {
  try {
    const payload = await fetchConversionJobs();
    jobs.value = payload.data;
  } catch (err) {
    error.value = err.message;
  }
}

async function loadTools() {
  try {
    tools.value = await fetchConversionTools();
  } catch (err) {
    error.value = err.message;
  }
}

function progressFor(job) {
  if (!job || !job.total_files) return 0;
  const finished = job.completed_files + job.skipped_files + job.failed_files;
  return Math.min(100, Math.round((finished / job.total_files) * 100));
}

function outputLabel(job) {
  const dest = job.destination_path || "source folder";
  return `${dest} - .${job.output_extension}`;
}

function rowClass(job) {
  return {
    failed: job.status === "failed",
    completed: job.status === "completed",
  };
}

function formatDate(value) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

onMounted(async () => {
  await Promise.all([loadJobs(), loadTools()]);
  timer = window.setInterval(loadJobs, 1500);
});

onUnmounted(() => {
  if (timer) window.clearInterval(timer);
});
</script>
