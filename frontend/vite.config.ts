/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

// https://vitejs.dev/config/
export default defineConfig({
  resolve: { alias: { './runtimeConfig': './runtimeConfig.browser' } },
  plugins: [
    {
      // npm overrides cannot reach @aws-amplify/ui-react's nested copies of
      // @aws-amplify/ui and @xstate/react, so Rollup deduplicates their
      // xstate imports up to the top-level v5 and the build fails with
      // `"actions" is not exported by xstate`. Redirect those imports to the
      // xstate-v4 alias at build time. Must be a top-level vite plugin (not
      // build.rollupOptions.plugins) with enforce: 'pre' to run before
      // Rollup's default resolver.
      name: 'resolve-xstate-v4-for-amplify',
      enforce: 'pre',
      async resolveId(source, importer) {
        if (
          source === 'xstate' &&
          importer &&
          importer.includes('@aws-amplify')
        ) {
          return this.resolve('xstate-v4', importer, { skipSelf: true });
        }
        return null;
      },
    },
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      devOptions: {
        enabled: true,
      },
      injectRegister: 'auto',
      workbox: {
        // Precache only the app shell. Lazily loaded chunks such as Mermaid
        // diagrams and syntax highlighting languages are cached when used.
        globPatterns: ['index.html', 'assets/index-*.{js,css}'],
        maximumFileSizeToCacheInBytes: 4 * 1024 * 1024,
        runtimeCaching: [
          {
            urlPattern: ({ url }) => url.pathname.startsWith('/assets/'),
            handler: 'CacheFirst',
            options: {
              cacheName: 'assets',
              plugins: [
                {
                  // CloudFront answers missing files with index.html, which
                  // must not be cached as a stale chunk after a deployment.
                  cacheWillUpdate: async ({ response }) =>
                    response.headers.get('content-type')?.includes('text/html')
                      ? null
                      : response,
                },
              ],
            },
          },
        ],
      },
      manifest: {
        name: 'Bedrock Chat',
        short_name: 'Bedrock Chat',
        description: 'AWS-native chatbot using Bedrock',
        start_url: '/index.html',
        display: 'standalone',
        theme_color: '#232F3E',
        icons: [
          {
            src: '/images/bedrock_icon_72.png',
            sizes: '72x72',
            type: 'image/png',
          },
          {
            src: '/images/bedrock_icon_96.png',
            sizes: '96x96',
            type: 'image/png',
          },
          {
            src: '/images/bedrock_icon_128.png',
            sizes: '128x128',
            type: 'image/png',
          },
          {
            src: '/images/bedrock_icon_144.png',
            sizes: '144x144',
            type: 'image/png',
          },
          {
            src: '/images/bedrock_icon_152.png',
            sizes: '152x152',
            type: 'image/png',
          },
          {
            src: '/images/bedrock_icon_192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: '/images/bedrock_icon_384.png',
            sizes: '384x384',
            type: 'image/png',
          },
          {
            src: '/images/bedrock_icon_512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
          {
            src: '/images/bedrock_icon_512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any',
          },
        ],
      },
    }),
  ],
  server: { host: true },
  // Tests that set process.env.TZ need child processes; worker threads ignore it.
  test: { pool: 'forks' },
});
