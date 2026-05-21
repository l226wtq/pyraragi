<template>
  <table class="itg archive-table">
    <thead>
      <tr>
        <th>Title</th>
        <th>Artist</th>
        <th>Series</th>
        <th>Tags</th>
        <th class="numeric">Pages</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="(archive, index) in archives" :key="archive.id" :class="index % 2 ? 'gtr1' : 'gtr0'">
        <td class="title-cell">
          <Bookmark :size="14" />
          <RouterLink :to="`/reader/${archive.id}`">{{ archive.title }}</RouterLink>
        </td>
        <td>{{ namespaceValue(archive, "artist") }}</td>
        <td>{{ namespaceValue(archive, "series") }}</td>
        <td class="tags-cell">
          <span v-for="tag in archive.tags.slice(0, 8)" :key="`${archive.id}-${tag.namespace}-${tag.name}`" class="gt">
            {{ tag.namespace ? `${tag.namespace}:${tag.name}` : tag.name }}
          </span>
        </td>
        <td class="numeric">{{ archive.page_count || "..." }}</td>
      </tr>
    </tbody>
  </table>
</template>

<script setup>
import { Bookmark } from "lucide-vue-next";

defineProps({
  archives: { type: Array, required: true },
});

function namespaceValue(archive, namespace) {
  return archive.tags
    .filter((tag) => tag.namespace === namespace)
    .map((tag) => tag.name)
    .join(", ");
}
</script>
