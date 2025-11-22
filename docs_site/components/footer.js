class CustomFooter extends HTMLElement {
  connectedCallback() {
    const year = new Date().getFullYear();
    this.innerHTML = `
      <footer class="mt-8 border-t border-slate-200 bg-white">
        <div class="container mx-auto px-4 py-4 text-sm text-slate-600 flex flex-wrap items-center justify-between gap-2">
          <span>© ${year} Risk Analysis Flagship</span>
          <div class="flex flex-wrap items-center gap-4">
            <span>Demo site • Data from local pipelines or bundled samples</span>
            <a
              href="https://rachit-personal-website.pages.dev/"
              target="_blank"
              rel="noreferrer"
              class="hover:text-indigo-600 underline"
            >
              Main site
            </a>
          </div>
        </div>
      </footer>
    `;
  }
}
customElements.define('custom-footer', CustomFooter);
