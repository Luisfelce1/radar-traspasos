import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";

// SITE_URL: pon tu dominio en Cloudflare Pages (Settings → Environment variables).
const site = process.env.SITE_URL || "https://example.pages.dev";

export default defineConfig({
  site,
  trailingSlash: "always",
  integrations: [sitemap()],
  build: { format: "directory" },
});
