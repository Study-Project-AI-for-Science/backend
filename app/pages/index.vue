<script setup lang="ts">
import { CloudUploadIcon, LoaderCircleIcon, RabbitIcon, SearchIcon } from "lucide-vue-next"

const query = ref("")

const config = useRuntimeConfig()

const { data: data, refresh } = await useFetch(`${config.public.apiBase}/papers`, {
  params: { query: refDebounced(query, 250) },
  cache: "no-cache",
})

const papers = computed(() => data.value?.papers ?? [])

// async function refreshLoadingPapers() {
//   if (papers.value?.some((paper) => paper.status === "pending")) {
//     await refresh()
//   }
// }

// useTimeoutPoll(refreshLoadingPapers, 1000)

const { open, onChange } = useFileDialog({
  accept: "application/pdf",
})

onChange(async (files) => {
  if (!files) return

  for (const file of files) {
    const formData = new FormData()

    formData.append("file", file)

    await $fetch(`${config.public.apiBase}/papers`, {
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

// auto refresh
useIntervalFn(async () => {
  await refresh()
}, 1000)
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
        v-if="papers.length > 0"
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
            <h2 class="mb-2 text-lg font-medium text-gray-700">No papers found</h2>
            <p>Try to change the search query or upload a new paper.</p>
          </div>
        </div>
      </div>
    </DPageContent>
  </DPage>
</template>
