import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";
import angular from "@analogjs/astro-angular";
import tailwindcss from "@tailwindcss/vite";

// SITE_URL: pon tu dominio en Cloudflare (variables de entorno).
const site = process.env.SITE_URL || "https://example.pages.dev";

export default defineConfig({
  site,
  trailingSlash: "always",
  integrations: [
    // Componentes Angular (volt-ui) dentro de Astro. Solo se transforman los de src/components/ng.
    angular({ vite: { transformFilter: (_code, id) => id.includes("src/components/ng") } }),
    sitemap(),
  ],
  vite: {
    plugins: [tailwindcss()],
    ssr: { noExternal: ["@voltui/components", "ng-primitives", "ng-primitives/**"] },
  },
  build: { format: "directory" },
});
