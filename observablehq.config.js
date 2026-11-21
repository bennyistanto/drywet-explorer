// Observable Framework configuration. Source root is site/, build output is dist/.
// Framework generates relative links, so the built site works under /drywet-explorer/ on GitHub Pages.
export default {
  root: "site",
  output: "dist",
  title: "Drywet Explorer",
  theme: ["air", "alt", "wide"], // light only for now: the map colours are chosen against a light surface
  sidebar: false,
  toc: false,
  pager: false,
  pages: [],
  footer: 'Developed by <a href="https://benny.istan.to" target="_blank" rel="noopener">Benny Istanto</a> as a casual weekend project. Indices computed from TerraClimate v1.1. Admin boundaries: Badan Informasi Geospasial. Built with Observable Framework.'
};
