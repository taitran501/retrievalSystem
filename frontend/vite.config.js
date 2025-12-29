import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 3001,
    proxy: {
      '^/(TextQuery|ImageQuery|VisualConceptSearch|SequentialQuery|health|config|submit_to_dres|get_neighbor_frames)': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            if (err.code === 'ECONNREFUSED') {
              // Silence ECONNREFUSED (backend down)
            } else {
              console.log('proxy error', err);
            }
          });
        }
      },
      '/keyframes': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => { if (err.code === 'ECONNREFUSED') return; console.log(err); });
        }
      },
      '/videos': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path,
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => { if (err.code === 'ECONNREFUSED') return; console.log(err); });
        }
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => { if (err.code === 'ECONNREFUSED') return; console.log(err); });
        }
      }
    }
  }
})
