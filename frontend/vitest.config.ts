import {defineConfig} from 'vitest/config';
import {fileURLToPath} from 'node:url';
export default defineConfig({resolve:{alias:{
  '/js/api.js':fileURLToPath(new URL('./src/test-api.ts',import.meta.url)),
  '/components/notifications/notification-store.js':fileURLToPath(new URL('./src/test-notifications.ts',import.meta.url)),
  '/components/messages/action-buttons/simple-action-buttons.js':fileURLToPath(new URL('./src/test-notifications.ts',import.meta.url)),
}}});
