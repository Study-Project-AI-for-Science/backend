<script setup lang="ts">
import { ArrowLeftIcon, RabbitIcon } from "lucide-vue-next"
import { marked } from "marked"
import DOMPurify from "dompurify"

const route = useRoute()
const paperId = route.params.id

const paper = computed(() => {
  return paperData.find((paper) => paper.id === paperId)
})

function markdownToHtml(markdown: string) {
  if (!markdown) return ""
  const html = marked(markdown) as string
  // sanitize the html
  const sanitizedHtml = DOMPurify.sanitize(html)
  return sanitizedHtml
}
</script>

<template>
  <DPage v-if="paper">
    <DHeader>
      <DButton to="/" :icon-left="ArrowLeftIcon" variant="secondary" class="!px-1.5"></DButton>
      <DHeaderTitle>{{ paper.title }}</DHeaderTitle>
    </DHeader>

    <DPageContent class="h-full flex-1 !p-0">
      <div class="grid h-full grid-cols-2">
        <div class="flex h-full flex-col gap-4 overflow-auto border-r border-gray-200 p-4 px-6">
          <div class="flex flex-col gap-2">
            <div class="text-xl font-semibold">Title</div>
            <div>{{ paper.title }}</div>
          </div>
          <div class="flex flex-col gap-2">
            <div class="text-xl font-semibold">Abstract</div>
            <div>{{ paper.abstract }}</div>
          </div>
          <div class="flex flex-col gap-2">
            <div class="text-xl font-semibold">Online Url</div>
            <div>
              <a :href="paper.onlineUrl" target="_blank">{{ paper.onlineUrl }}</a>
            </div>
          </div>
          <div></div>
          <div class="prose border-t border-gray-200 pt-5">
            <h2>Content</h2>
            <div v-html="markdownToHtml(paper.content)"></div>
            <!-- <pre>{{ paper.content }}</pre> -->
          </div>
        </div>
        <div class="overflow-auto p-4">
          <h2 class="mb-2 text-xl font-semibold">References</h2>
          <!-- <pre>{{ references }}</pre> -->
          <div class="flex flex-col gap-2">
            <div
              v-for="reference in paper.references"
              class="flex flex-col gap-2 rounded-md bg-gray-100 p-2"
            >
              <div class="font-semibold">{{ reference.title }}</div>
              <div>{{ reference.authors }}</div>
            </div>
          </div>
        </div>
        <div v-if="false" class="flex flex-col">
          <div class="flex-1">
            <div
              class="flex h-full w-full flex-col items-center justify-center gap-2 p-4 text-center text-sm text-gray-500"
            >
              <div class="flex flex-col items-center">
                <div class="mb-4 rounded-md bg-gray-100 p-2">
                  <RabbitIcon class="h-12 w-12 stroke-[1.5px] text-gray-500" />
                </div>
                <h2 class="mb-2 text-lg font-medium text-gray-700">Awaiting chat</h2>
                <p>Chatting with papers is currently not implemented.</p>
              </div>
            </div>
          </div>
          <div class="p-4">
            <input
              type="text"
              placeholder="Chat with paper"
              class="w-full rounded-md bg-gray-100 px-2.5 py-2.5 text-sm leading-0 ring-blue-600 outline-none placeholder:text-gray-500 focus:border-transparent focus:ring-2"
            />
          </div>
        </div>
      </div>
    </DPageContent>
  </DPage>
  <div v-else>Loading...</div>
</template>
