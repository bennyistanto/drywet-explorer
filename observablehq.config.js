// Observable Framework configuration. Source root is site/, build output is dist/.
// Framework generates relative links, so the built site works under /drywet-explorer/ on GitHub Pages.
import {readFileSync} from "node:fs";

// The favicon is site/icon.svg, the same file the page title shows. It is written into the head as a data
// URI so that it needs no path, and so works under any base path. Base64, because Framework rewrites
// percent signs in a head link and that breaks a percent-encoded SVG.
const icon = `data:image/svg+xml;base64,${readFileSync(new URL("./site/icon.svg", import.meta.url)).toString("base64")}`;

export default {
  root: "site",
  output: "dist",
  title: "Drywet Explorer",
  theme: ["air", "alt", "wide"], // light only for now: the map colours are chosen against a light surface
  sidebar: false,
  toc: false,
  pager: false,
  pages: [],
  // Google Analytics 4 (owner's property). Loaded on every page of the built site.
  head: `<link rel="icon" type="image/svg+xml" href="${icon}">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-M3QLZ5F6EX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-M3QLZ5F6EX');
</script>`,
  footer: 'Developed by <a href="https://benny.istan.to" target="_blank" rel="noopener">Benny Istanto</a> as a casual weekend project. Indices computed from TerraClimate v1.1. Admin boundaries: Badan Informasi Geospasial. Built with Observable Framework.'
};
