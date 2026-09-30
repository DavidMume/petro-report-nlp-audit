import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base "./" keeps every asset path relative, so the build works from any static
// host or sub-path (GitHub Pages, Cloudflare Pages, a portfolio sub-route).
export default defineConfig({
  base: "./",
  plugins: [react()],
});
