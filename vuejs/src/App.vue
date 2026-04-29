<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import JSConfetti from 'js-confetti'
import { useToast } from "vue-toastification";
import { useRoute, useRouter } from 'vue-router';
import PortfolioView from '@/views/PortfolioView.vue';
import { parseJwtPayload } from '@/utils/auth';

const confetti = new JSConfetti()

const toast = useToast();

const route = useRoute()
const router = useRouter()

import NotAuth from '@/components/NotAuth/NotAuth.vue'
import Auth from '@/components/Auth/Auth.vue'

const has_token = ref(null)
const access_token = ref(null)



onMounted(async () => {
  try {
    const response = await axios.get('/api/users/refresh_token', { withCredentials: true })
    access_token.value = response.data?.access_token ?? null
    has_token.value = Boolean(access_token.value)
  } catch (_) {
    has_token.value = false
    access_token.value = null
  }
});

async function logout() {
  try {
    await axios.post('/api/users/logout', {}, { withCredentials: true })
  } catch (_) {
    // Keep local logout behavior even if the server call fails.
  }
  has_token.value = false;
  access_token.value = null;
  router.push('/')
}


async function login(token) {
  const payload = parseJwtPayload(token)
  if (!payload?.user_id) {
    has_token.value = false;
    access_token.value = null;
    return;
  }
  access_token.value = token;
  has_token.value = true;
}

const register = ref(false)


function signup(token) {
  const payload = parseJwtPayload(token)
  if (!payload?.user_id) {
    has_token.value = false;
    access_token.value = null;
    return;
  }
  access_token.value = token;
  has_token.value = true;
  register.value = true
}
</script>

<template>
  <Auth v-if="has_token === true && route.path !== '/portfolio'" :access_token="access_token" @logout="logout()" :register="register"
    @createPinModelClose="register = false" />
  <NotAuth v-if="has_token === false && route.path !== '/portfolio'" @login="(token) => { login(token) }" @signup="(token) => { signup(token) }" />
  <PortfolioView v-if="route.path === '/portfolio'"/>
</template>