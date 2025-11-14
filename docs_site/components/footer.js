class CustomFooter extends HTMLElement {
    connectedCallback() {
      const year = new Date().getFullYear();
      this.innerHTML = `
        <footer class="mt-8 border-t border-slate-200 bg-white">
          <div class="container mx-auto px-4 py-4 text-sm text-slate-600 flex flex-wrap items-center justify-between">
            <span>© ${year} Risk Analysis Flagship</span>
            <span>Demo site • Data from local pipelines or bundled samples</span>
          </div>
        </footer>
      `;
    }
  }
  customElements.define('custom-footer', CustomFooter);
  