import type { CapacitorConfig } from '@capacitor/cli'

/**
 * Android wrapper configuration.
 *
 * The UI is bundled into the APK from dist/, so the app opens instantly and
 * without a network round trip. The AI itself cannot be bundled: the disease,
 * soil and validator models run under TensorFlow on the FastAPI backend, so
 * every analysis call goes to that server over the network. Build with
 * `--mode android` so VITE_API_BASE_URL in .env.android points at it.
 *
 * androidScheme stays http and cleartext is allowed because that backend is
 * served over plain http on the local network. If the backend ever moves to a
 * real https host, set VITE_API_BASE_URL to it and turn cleartext off.
 */
const config: CapacitorConfig = {
  appId: 'com.sgbit.smartsugarcaneai',
  appName: 'Smart Sugarcane AI',
  webDir: 'dist',
  android: {
    allowMixedContent: true,
  },
  server: {
    androidScheme: 'http',
    cleartext: true,
  },
}

export default config
