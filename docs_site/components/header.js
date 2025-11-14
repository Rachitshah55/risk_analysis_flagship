class CustomHeader extends HTMLElement {
    connectedCallback() {
      const activeClass = 'text-indigo-600 font-semibold';
      const baseClass   = 'px-3 py-2 text-slate-600 hover:text-indigo-700';
      const here = (name) => location.pathname.split('/').pop() === name;
  
      const link = (href, label) =>
        `<a href="${href}" class="${baseClass} ${here(href) ? activeClass : ''}">${label}</a>`;
  
      this.innerHTML = `
        <header class="bg-white border-b border-slate-200">
          <div class="container mx-auto px-4 py-3 flex items-center justify-between">
            <a href="index.html" class="flex items-center gap-2">
              <svg width="24" height="24" viewBox="0 0 24 24" class="text-indigo-600"><path fill="currentColor" d="M3 11h18v2H3zM5 7h14v2H5zM7 15h10v2H7z"/></svg>
              <span class="text-slate-900 font-semibold">Risk Analysis Flagship</span>
            </a>
            <nav class="flex items-center">
              ${link('index.html','Home')}
              ${link('credit.html','Credit')}
              ${link('fraud.html','Fraud')}
              ${link('ops.html','Ops')}
            </nav>
          </div>
        </header>
      `;
    }
  }
  customElements.define('custom-header', CustomHeader);
  