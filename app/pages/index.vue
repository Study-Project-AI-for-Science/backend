<script setup lang="ts">
import { CloudUploadIcon, RabbitIcon, SearchIcon } from "lucide-vue-next"

const papers = ref(paperData)

const search = useRouteQuery<string>("q")

const debouncedSearch = useDebounce(search, 100)

const filteredPapers = computed(() => {
  if (!papers.value) return []
  if (!debouncedSearch.value) return papers.value

  return papers.value.filter((paper) => {
    let searchString = paper.title.toLowerCase() + paper.abstract.toLowerCase()
    return searchString.includes(debouncedSearch.value.toLowerCase())
  })
})

function highlightText(text: string, search: string) {
  return text.replace(
    new RegExp(search, "gi"),
    (match) => `<span class="bg-yellow-200">${match}</span>`,
  )
}
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
          v-model="search"
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
        v-if="search === '' || search === null || search === undefined || search?.length === 0"
        class="h-full"
      >
        <div
          class="flex h-full w-full flex-col items-center justify-center gap-2 p-4 text-center text-sm text-gray-500"
        >
          <div class="mx-auto flex w-full flex-col items-center">
            <div class="mb-4 rounded-md bg-gray-100 p-2">
              <RabbitIcon class="h-12 w-12 stroke-[1.5px] text-gray-500" />
            </div>
            <h2 class="mb-2 text-lg font-medium text-gray-700">Welcome {{ "{ user.name }" }}</h2>
            <p class="mx-auto max-w-xs">
              You can upload a paper to get started or search for a paper using the search bar
              above.
            </p>
            <div class="mt-5">
              <DButton :icon-left="CloudUploadIcon" @click="uploadPaper">Paper upload</DButton>
            </div>
          </div>
        </div>
      </div>
      <div
        v-else-if="filteredPapers.length > 0"
        class="grid gap-2.5 p-2"
        :style="{ gridTemplateColumns: `repeat(auto-fill, minmax(min(100%, 200px), 1fr))` }"
      >
        <NuxtLink
          v-for="paper in filteredPapers"
          :to="`/papers/${paper.id}`"
          class="h-[274px] cursor-pointer rounded-md border border-gray-200 p-4 transition-all hover:shadow"
        >
          <div
            class="mb-2 line-clamp-2 overflow-hidden text-sm font-medium overflow-ellipsis text-gray-900"
          >
            <div v-html="highlightText(paper.title, debouncedSearch)"></div>
          </div>
          <div class="line-clamp-12 overflow-hidden text-xs overflow-ellipsis text-gray-500">
            <div v-html="highlightText(paper.abstract, debouncedSearch)"></div>
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
              {{ debouncedQuery ? "No matching papers found" : "No papers found" }}
            </h2>
            <p>
              {{
                debouncedQuery
                  ? "Try adjusting your search terms or upload a new paper."
                  : "Try to change the search query or upload a new paper."
              }}
            </p>
          </div>
        </div>
      </div>
    </DPageContent>
  </DPage>
</template>
