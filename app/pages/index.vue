<script setup lang="ts">
import { CloudUploadIcon, RabbitIcon, SearchIcon } from "lucide-vue-next"

const query = ref("")
const debouncedQuery = refDebounced(query, 300)

const { data, refresh } = await useFetch(`/api/papers`, {
  query: computed(() => ({ search: debouncedQuery.value })),
  watch: [debouncedQuery]
})

const papers = computed(() => data.value?.papers)

const { open, onChange } = useFileDialog({
  accept: "application/pdf",
})

onChange(async (files) => {
  if (!files) return

  for (const file of files) {
    const formData = new FormData()

    formData.append("file", file)

    await $fetch(`/api/papers`, {
      method: "POST",
      body: formData,
    })
  }

  await refresh()
})

function uploadPaper() {
  query.value = ""
  open()
}

// Intelligent auto-refresh: only refresh when no search query is active
// This allows users to see newly uploaded papers without spamming API during search
const { pause, resume } = useIntervalFn(() => {
  // Only refresh if there's no active search query
  if (!debouncedQuery.value.trim()) {
    refresh()
  }
}, 5000) // Refresh every 5 seconds when idle

// Pause auto-refresh when user is actively searching
watch(debouncedQuery, (newQuery) => {
  if (newQuery.trim()) {
    pause()
  } else {
    // Resume auto-refresh after a brief delay when search is cleared
    setTimeout(() => {
      if (!debouncedQuery.value.trim()) {
        resume()
      }
    }, 1000)
  }
})
</script>

<template>
  <DPage>
    <DHeader>
      <DHeaderTitle>Papers</DHeaderTitle>

      <div class="relative ml-2 w-[400px] max-w-full">
        <div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-2.5">
          <SearchIcon class="size-4 text-gray-500" />
        </div>
        <input
          v-model="query"
          type="text"
          id="search"
          class="w-full rounded-md bg-gray-100 p-2.5 py-1.5 pl-8.5 text-sm text-gray-900 focus:border-transparent focus:ring-2 focus:ring-blue-500 focus:outline-none"
          placeholder="Search papers"
          required
        />
      </div>

      <template #right>
        <DButton :icon-left="CloudUploadIcon" @click="uploadPaper">Paper upload</DButton>
      </template>
    </DHeader>
    <DPageContent>
      <div
        v-if="papers && papers.length > 0"
        class="grid gap-2.5 p-2"
        :style="{ gridTemplateColumns: `repeat(auto-fill, minmax(min(100%, 200px), 1fr))` }"
      >
        <NuxtLink
          v-for="paper in papers"
          :to="`/papers/${paper.id}`"
          class="h-[274px] cursor-pointer rounded-md border border-gray-200 p-4 transition-all hover:shadow"
        >
          <div
            class="mb-2 line-clamp-2 overflow-hidden text-sm font-medium overflow-ellipsis text-gray-900"
          >
            {{ paper.title }}
          </div>
          <div class="line-clamp-12 overflow-hidden text-xs overflow-ellipsis text-gray-500">
            {{ paper.abstract }}
          </div>
        </NuxtLink>
      </div>
      <div v-else class="h-full">
        <div
          class="flex h-full w-full flex-col items-center justify-center gap-2 p-4 text-center text-sm text-gray-500"
        >
          <div class="flex flex-col items-center">
            <div class="mb-4 rounded-md bg-gray-100 p-2">
              <RabbitIcon class="h-12 w-12 stroke-[1.5px] text-gray-500" />
            </div>
            <h2 class="mb-2 text-lg font-medium text-gray-700">
              {{ debouncedQuery ? 'No matching papers found' : 'No papers found' }}
            </h2>
            <p>
              {{ debouncedQuery 
                ? 'Try adjusting your search terms or upload a new paper.' 
                : 'Try to change the search query or upload a new paper.' 
              }}
            </p>
          </div>
        </div>
      </div>
    </DPageContent>
  </DPage>
</template>
