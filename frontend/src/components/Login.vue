<template>
  <div class="login">
    <div class="login-box">
      <h1>Sign in</h1>
      <p class="note">Access is invite-only.</p>

      <button class="google-btn" @click="googleLogin" :disabled="busy">
        Continue with Google
      </button>

      <div class="divider">or</div>

      <form @submit.prevent="emailLogin">
        <div class="field">
          <label for="login-email">Email</label>
          <input id="login-email" v-model="email" type="email" required />
        </div>
        <div class="field">
          <label for="login-password">Password</label>
          <input id="login-password" v-model="password" type="password" required />
        </div>
        <button type="submit" :disabled="busy || !email || !password">
          {{ busy ? 'Signing in...' : 'Sign in' }}
        </button>
      </form>

      <p v-if="error" class="error">{{ error }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { loginWithEmail, loginWithGoogle } from '../auth'

const email = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

const googleLogin = async () => {
  error.value = ''
  busy.value = true
  try {
    await loginWithGoogle()
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

const emailLogin = async () => {
  error.value = ''
  busy.value = true
  try {
    await loginWithEmail(email.value, password.value)
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.login {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
}

.login-box {
  width: 320px;
  border: 1px solid #000;
  padding: 24px;
}

h1 {
  margin-bottom: 4px;
}

.note {
  font-size: 13px;
  margin-bottom: 16px;
}

.google-btn {
  width: 100%;
  border: 1px solid #000;
  background: #fff;
  color: #000;
  padding: 10px;
}

.divider {
  text-align: center;
  font-size: 12px;
  margin: 14px 0;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
}

label {
  font-size: 13px;
}

input {
  border: 1px solid #000;
  padding: 6px;
  background: #fff;
  color: #000;
}

button[type='submit'] {
  width: 100%;
  border: 1px solid #000;
  background: #fff;
  color: #000;
  padding: 8px;
}

button:disabled {
  opacity: 0.4;
  cursor: default;
}

.error {
  margin-top: 12px;
  font-size: 13px;
}
</style>
