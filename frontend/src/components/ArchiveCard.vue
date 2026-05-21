<template>
  <article class="archive-card context-card" :class="{ selected }">
    <RouterLink class="archive-link" :to="`/reader/${archive.id}`">
      <div class="thumb-frame">
        <img
          class="thumb-image"
          :src="coverUrl"
          :alt="archive.title"
          loading="lazy"
          @error="coverFailed = true"
          v-if="!coverFailed"
        />
        <div class="thumb-placeholder" v-else>
          <ImageIcon :size="38" />
          <span>Thumbnail pending</span>
        </div>
      </div>
      <div class="archive-title-row">
        <Bookmark :size="15" class="bookmark" />
        <span class="archive-title">{{ archive.title }}</span>
      </div>
      <div class="archive-stat">{{ pageLabel }} · {{ formatBytes(archive.file_size) }}</div>
      <div class="tag-line">
        <span v-for="tag in archive.tags.slice(0, 3)" :key="`${tag.namespace}:${tag.name}`" class="gt">
          {{ formatTag(tag) }}
        </span>
      </div>
    </RouterLink>
  </article>
</template>

<script setup>
import { computed, ref } from "vue";
import { Bookmark, Image as ImageIcon } from "lucide-vue-next";

const props = defineProps({
  archive: { type: Object, required: true },
  selected: { type: Boolean, default: false },
});

const coverFailed = ref(false);
const coverUrl = computed(() => `/api/archives/${props.archive.id}/cover`);
const pageLabel = computed(() => (props.archive.page_count ? `${props.archive.page_count} pages` : "Indexing"));

function formatTag(tag) {
  return tag.namespace ? `${tag.namespace}:${tag.name}` : tag.name;
}

function formatBytes(value) {
  if (!value) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let size = value;
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024;
    unit += 1;
  }
  return `${size.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`;
}
</script>
