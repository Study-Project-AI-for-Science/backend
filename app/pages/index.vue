<script setup lang="ts">
const content = ref("")

const { data: posts, refresh } = await useFetch("/api/posts")

async function createPost() {
  console.log("createPost", content.value)

  await $fetch("/api/posts", {
    method: "POST",
    body: {
      content: content.value,
    },
  })
  await refresh()
}
</script>

<template>
  <div class="flex flex-col p-12">
    <h2>create a post</h2>
    <form @submit.prevent="createPost" class="flex flex-col">
      <input v-model="content" type="text" name="content" placeholder="Content" class="border" />
      <button type="submit" class="bg-black text-white">Submit</button>
    </form>

    <h2>posts</h2>

    <div class="flex flex-col gap-2">
      <div v-for="post in posts" class="border p-2">
        {{ post.content }}
      </div>
    </div>
  </div>
</template>
