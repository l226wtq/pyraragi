<template>
  <div class="page-controls">
    <button class="stdbtn icon-button" type="button" :disabled="page <= 1" @click="$emit('previous')">
      <ChevronLeft :size="18" />
    </button>
    <label class="page-input-label">
      <input class="stdinput page-input" type="number" min="1" :max="total" :value="page" @change="onChange" />
      <span>/ {{ total || "..." }}</span>
    </label>
    <button class="stdbtn icon-button" type="button" :disabled="page >= total" @click="$emit('next')">
      <ChevronRight :size="18" />
    </button>
  </div>
</template>

<script setup>
import { ChevronLeft, ChevronRight } from "lucide-vue-next";

defineProps({
  page: { type: Number, required: true },
  total: { type: Number, required: true },
});

const emit = defineEmits(["go", "previous", "next"]);

function onChange(event) {
  emit("go", Number(event.target.value));
}
</script>
