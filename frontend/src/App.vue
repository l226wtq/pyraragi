<template>
  <div class="app-shell">
    <nav class="top-nav">
      <RouterLink class="nav-link" to="/"><ChevronRight :size="15" /> Archive Index</RouterLink>
      <RouterLink class="nav-link" to="/upload"><ChevronRight :size="15" /> Add Archives</RouterLink>
      <RouterLink class="nav-link" to="/convert"><ChevronRight :size="15" /> Archive Conversion</RouterLink>
      <RouterLink class="nav-link" to="/jobs"><ChevronRight :size="15" /> Tasks</RouterLink>
      <a class="nav-link muted" href="#" aria-disabled="true"><ChevronRight :size="15" /> Settings</a>
      <a class="nav-link muted" href="#" aria-disabled="true"><ChevronRight :size="15" /> Statistics</a>
    </nav>
    <RouterView />
  </div>
</template>

<script setup>
import { ChevronRight } from "lucide-vue-next";
</script>
