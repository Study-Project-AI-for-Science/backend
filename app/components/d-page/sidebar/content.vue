<script setup lang="ts">
import {
  LogOutIcon,
  PanelLeftClose,
  PanelRightClose,
  SaveIcon,
  XIcon,
  FolderIcon,
  FoldersIcon,
  FileIcon,
  SearchCheckIcon,
  WaypointsIcon,
  HomeIcon,
  TrashIcon,
} from "lucide-vue-next"
import { useSessionStorage } from "@vueuse/core"

const route = useRoute()

const links = [
  {
    name: "Home",
    to: "/",
    icon: HomeIcon,
  },
  {
    name: "Citation Checker",
    to: "/citation-checker",
    icon: SearchCheckIcon,
  },
  {
    name: "Argumentation Graph",
    to: "/argumentation-graph",
    icon: WaypointsIcon,
  },
]

const footerLinks = [
  {
    name: "Sign out",
    to: "/logout",
    icon: LogOutIcon,
  },
]

const collapsed = useSessionStorage("collapsed", false)

const organisationName = ref("AI for Science")

const emit = defineEmits(["close"])

function close() {
  emit("close")
}

const papers = ref(paperData)

function isLinkActive(link: string) {
  if (link === "/") {
    return route.path === link
  }
  return route.path.startsWith(link)
}
</script>

<template>
  <div class="flex h-screen flex-col">
    <nav class="flex flex-1 flex-col overflow-auto">
      <div class="p-2">
        <div
          class="group flex h-9 cursor-default items-center justify-between gap-2 rounded-md text-sm text-gray-700"
        >
          <NuxtLink to="/" v-show="!collapsed" class="flex items-center gap-2 px-2 py-2">
            <div class="line-clamp-1 leading-[1em] font-medium">{{ organisationName }}</div>
          </NuxtLink>
          <div
            class="hidden items-center rounded-md p-2 hover:bg-gray-200 sm:flex"
            :class="collapsed ? '' : 'opacity-0 group-hover:opacity-100'"
            @click="collapsed = !collapsed"
          >
            <PanelLeftClose v-show="!collapsed" class="size-4" />
            <PanelRightClose v-show="collapsed" class="size-4" />
          </div>
          <div class="block sm:hidden">
            <DButton :icon-left="XIcon" class="!px-1" @click="close" />
          </div>
        </div>
        <hr class="mt-1 mb-1.5 text-gray-200" />
        <div class="flex flex-col gap-0.5">
          <NuxtLink
            v-for="link in links"
            class="flex cursor-default items-center gap-2 rounded-md px-2 py-1.5 text-sm text-gray-700 hover:bg-gray-200"
            :to="link.to"
            :class="isLinkActive(link.to) ? 'bg-gray-200' : ''"
          >
            <div class="flex h-5 items-center justify-center">
              <component :is="link.icon" class="size-4" />
            </div>
            <div v-show="!collapsed">{{ link.name }}</div>
          </NuxtLink>
        </div>
        <hr class="mt-1 mb-1.5 text-gray-200" />
      </div>
      <div class="flex flex-1 flex-col overflow-auto" :class="collapsed ? 'hidden' : ''">
        <div class="ml-2 text-xs font-medium text-gray-500">Recent papers</div>
        <div class="flex flex-1 flex-col gap-0.5 overflow-auto p-2">
          <NuxtLink
            v-for="paper in papers"
            class="group flex cursor-default items-center gap-2 rounded-md py-0.5 pr-1 pl-2 text-sm text-gray-500 hover:bg-gray-200"
            :to="`/papers/${paper.id}`"
            :class="route.path.startsWith(`/papers/${paper.id}`) ? 'bg-gray-200 text-gray-700' : ''"
          >
            <div class="flex h-5 items-center justify-center">
              <FileIcon class="size-4" />
            </div>
            <div v-show="!collapsed" class="line-clamp-1">{{ paper.title }}</div>
            <div class="opacity-0 group-hover:opacity-100" :class="collapsed ? 'hidden' : ''">
              <DButton :icon-left="TrashIcon" variant="transparent" class="!px-1.5" />
            </div>
          </NuxtLink>
        </div>
      </div>
    </nav>

    <nav class="p-2">
      <NuxtLink
        v-for="link in footerLinks"
        class="flex cursor-default items-center gap-2 rounded-md px-2 py-1.5 text-sm text-gray-700 hover:bg-gray-200"
        :to="link.to"
        :class="route.path.startsWith(link.to) ? 'bg-gray-200' : ''"
      >
        <div class="flex h-5 items-center justify-center">
          <component :is="link.icon" class="size-4" />
        </div>
        <div v-show="!collapsed">{{ link.name }}</div>
      </NuxtLink>
    </nav>
  </div>
</template>
