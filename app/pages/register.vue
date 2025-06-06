<script setup lang="ts">
const form = reactive({ name: '', email: '', password: '' })
const loading = ref(false)

async function submit() {
  loading.value = true
  try {
    await $fetch('/api/register', { method: 'POST', body: form })
    await navigateTo('/login')
  } catch (err) {
    console.error(err)
    alert('Registration failed')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <DPage>
    <DPageEmpty>
      <form @submit.prevent="submit" class="flex w-full max-w-xs flex-col gap-2">
        <h1 class="mb-2 text-xl font-semibold">Register</h1>
        <DLabel>Name</DLabel>
        <DInput v-model="form.name" />
        <DLabel>Email</DLabel>
        <DInput v-model="form.email" type="email" />
        <DLabel>Password</DLabel>
        <DInput v-model="form.password" type="password" />
        <DButton type="submit" :loading="loading" textCenter>Register</DButton>
        <NuxtLink class="text-blue-600" to="/login">Back to login</NuxtLink>
      </form>
    </DPageEmpty>
  </DPage>
</template>
