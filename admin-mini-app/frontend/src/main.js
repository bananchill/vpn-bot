import { createApp } from 'vue'
import { createPinia } from 'pinia'
import WebApp from '@twa-dev/sdk'
import App from './App.vue'
import router from './router'
import './assets/styles/main.css'

// Notify Telegram that the Mini App is ready to be displayed
WebApp.ready()

// Expand the Mini App to full viewport height
WebApp.expand()

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
