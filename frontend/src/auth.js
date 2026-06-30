import { ref } from 'vue'
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signInWithPopup,
  GoogleAuthProvider,
  signOut,
} from 'firebase/auth'
import { auth } from './firebase'

// Reactive auth state shared across the app.
export const currentUser = ref(null)
export const authReady = ref(false)

onAuthStateChanged(auth, (user) => {
  currentUser.value = user
  authReady.value = true
})

export function loginWithEmail(email, password) {
  return signInWithEmailAndPassword(auth, email, password)
}

export function loginWithGoogle() {
  return signInWithPopup(auth, new GoogleAuthProvider())
}

export function logout() {
  return signOut(auth)
}

// Always-fresh Firebase ID token for the backend Authorization header.
export async function getIdToken() {
  if (!auth.currentUser) return null
  return auth.currentUser.getIdToken()
}
