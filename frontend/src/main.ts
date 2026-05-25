// @ts-nocheck
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import i18n from './i18n'
import './styles/businessTheme.css'

const app = createApp(App)

app.use(router)
app.use(i18n)

router.isReady()
  .then(() => {
    app.mount('#app')
  })
  .catch((error) => {
    console.error('Failed to initialize MiroConsumer workspace', error)
  })
