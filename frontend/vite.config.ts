import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

/** Backend origin the dev server proxies to. Override with BACKEND_ORIGIN if you run
 *  the API somewhere other than port 8001. */
const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN ?? "http://127.0.0.1:8001";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    // Proxy /api to the backend so the browser only ever talks to the vite origin.
    //
    // Without this, the frontend calls the backend's absolute URL cross-origin, so every
    // request needs the backend's CORS list to contain the exact origin the page was
    // loaded from. That list has localhost and 127.0.0.1 but not the LAN address vite
    // prints as "Network:" — so opening the app at http://192.168.x.x:5173 (or from a
    // phone on the same wifi) had every request blocked, surfacing as
    // "Unable to load data / Failed to fetch" on every page.
    //
    // Proxying makes the request same-origin, so it works from localhost, 127.0.0.1 and
    // any LAN address without touching CORS config or chasing a DHCP-assigned IP.
    proxy: {
      "/api": {
        target: BACKEND_ORIGIN,
        changeOrigin: true,
      },
    },
  },
});
