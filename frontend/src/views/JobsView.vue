<template>
  <main class="ido jobs-panel">
    <h1 class="ih">Background Tasks</h1>

    <section class="job-actions">
      <button class="stdbtn primary" type="button" @click="runJob('scan_library')">
        <FolderSearch :size="16" /> Scan Library
      </button>
      <button class="stdbtn" type="button" @click="runJob('generate_thumbnails')">
        <Image :size="16" /> Generate Covers
      </button>
      <button class="stdbtn" type="button" @click="runJob('check_duplicates')">
        <CopyCheck :size="16" /> Check Duplicates
      </button>
      <button class="icon-link" type="button" @click="refreshAll"><RefreshCw :size="18" /></button>
    </section>

    <div v-if="error" class="json-error">{{ error }}</div>

    <section class="job-grid">
      <article v-for="job in jobs" :key="job.id" class="job-card">
        <div class="job-card-head">
          <strong>{{ labelFor(job.job_type) }}</strong>
          <span :class="['status-pill', job.status]">{{ job.status }}</span>
        </div>
        <div class="progress">
          <div class="bar" :style="{ width: `${progressFor(job)}%` }"></div>
        </div>
        <div class="job-summary">
          <span>{{ progressFor(job) }}%</span>
          <span>{{ job.completed_items }}/{{ job.total_items }}</span>
        </div>
        <div class="job-detail">
          <div>Current: {{ job.current_item || "-" }}</div>
          <div>Skipped {{ job.skipped_items }} - Failed {{ job.failed_items }}</div>
          <div>{{ formatDate(job.created_at) }}</div>
        </div>
        <div class="job-card-actions">
          <button class="stdbtn" type="button" :disabled="!canStop(job)" @click="requestStop(job.id)">
            <Square :size="15" /> Stop
          </button>
        </div>
        <pre v-if="job.log" class="job-log">{{ job.log }}</pre>
      </article>
      <div v-if="!jobs.length" class="empty-state">No jobs yet.</div>
    </section>

    <section class="duplicates-section">
      <div class="history-head">
        <h2 class="ih">Confirmed File Duplicates</h2>
        <button class="icon-link" type="button" @click="loadDuplicates"><RefreshCw :size="18" /></button>
      </div>

      <article v-for="group in duplicateGroups" :key="group.id" class="duplicate-card">
        <div class="duplicate-head">
          <strong>{{ group.member_count }} files</strong>
          <span>{{ formatSize(group.file_size) }}</span>
          <code>{{ group.full_sha256.slice(0, 16) }}</code>
        </div>
        <table class="itg duplicate-table">
          <tbody>
            <tr v-for="member in group.members" :key="member.file_path">
              <td>{{ member.filename }}</td>
              <td>{{ member.file_path }}</td>
              <td>{{ member.archive_id || "-" }}</td>
            </tr>
          </tbody>
        </table>
      </article>

      <div v-if="!duplicateGroups.length" class="empty-state">No confirmed duplicates.</div>
    </section>
  </main>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from "vue";
import { CopyCheck, FolderSearch, Image, RefreshCw, Square } from "lucide-vue-next";
import { fetchDuplicateGroups, fetchJobs, startJob, stopJob } from "@/api/client";

const jobs = ref([]);
const duplicateGroups = ref([]);
const error = ref("");
let timer = null;

async function runJob(jobType) {
  error.value = "";
  try {
    await startJob(jobType);
    await refreshAll();
  } catch (err) {
    error.value = err.message;
  }
}

async function requestStop(jobId) {
  error.value = "";
  try {
    await stopJob(jobId);
    await loadJobs();
  } catch (err) {
    error.value = err.message;
  }
}

async function refreshAll() {
  await Promise.all([loadJobs(), loadDuplicates()]);
}

async function loadJobs() {
  try {
    const payload = await fetchJobs();
    jobs.value = payload.data;
  } catch (err) {
    error.value = err.message;
  }
}

async function loadDuplicates() {
  try {
    const payload = await fetchDuplicateGroups();
    duplicateGroups.value = payload.data;
  } catch (err) {
    error.value = err.message;
  }
}

function progressFor(job) {
  if (!job.total_items) return job.status === "completed" ? 100 : 0;
  const finished = job.completed_items + job.skipped_items + job.failed_items;
  return Math.min(100, Math.round((finished / job.total_items) * 100));
}

function canStop(job) {
  return ["queued", "running"].includes(job.status) && !job.stop_requested;
}

function labelFor(jobType) {
  return {
    scan_library: "Scan Library",
    generate_thumbnails: "Generate Covers",
    check_duplicates: "Check Duplicates",
  }[jobType] || jobType;
}

function formatDate(value) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

function formatSize(bytes) {
  if (!bytes) return "0 MB";
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

onMounted(async () => {
  await refreshAll();
  timer = window.setInterval(refreshAll, 1500);
});

onUnmounted(() => {
  if (timer) window.clearInterval(timer);
});
</script>
