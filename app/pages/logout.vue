<script setup lang="ts">
const session = useUserSession()

onMounted(async () => {
  await session.clear()
  await navigateTo('/login')
})
</script>

<template></template>
