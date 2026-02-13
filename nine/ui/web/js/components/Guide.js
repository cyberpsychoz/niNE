/**
 * Guide Component - Markdown-based knowledge base.
 *
 * Left sidebar with tabs, right panel with rendered markdown content.
 * Add new pages by placing .md files in /guide/ and adding entries to GUIDE_PAGES.
 */

const GUIDE_PAGES = [
    { id: 'from-creator', title: 'От создателя', file: 'guide/from-creator.md' },
    { id: 'about-game',   title: 'Об игре',      file: 'guide/about-game.md' },
];

class Guide {
    constructor(params = {}) {
        this.params = params;
        this.element = null;
        this.activePage = GUIDE_PAGES[0].id;
        this._cache = {};
        console.log('[Guide] Created');
    }

    async render() {
        const response = await fetch('templates/guide.html');
        const html = await response.text();

        const app = document.getElementById('app');
        app.innerHTML = html;

        this.element = document.getElementById('guide-screen');

        this._renderNav();
        await this._loadPage(this.activePage);
        this._attachListeners();

        console.log('[Guide] Rendered');
    }

    _renderNav() {
        const nav = document.getElementById('guide-nav');
        if (!nav) return;

        nav.innerHTML = GUIDE_PAGES.map(p =>
            `<button class="guide-nav-btn ${p.id === this.activePage ? 'active' : ''}" data-page="${p.id}">${p.title}</button>`
        ).join('');
    }

    async _loadPage(pageId) {
        const page = GUIDE_PAGES.find(p => p.id === pageId);
        if (!page) return;

        this.activePage = pageId;
        this._renderNav();

        const article = document.getElementById('guide-article');
        if (!article) return;

        // Show loading
        article.innerHTML = '<p style="color:var(--color-text-hint);">...</p>';

        try {
            let md;
            if (this._cache[pageId]) {
                md = this._cache[pageId];
            } else {
                const resp = await fetch(page.file);
                md = await resp.text();
                this._cache[pageId] = md;
            }
            article.innerHTML = this._renderMarkdown(md);
        } catch (e) {
            article.innerHTML = '<p style="color:#e05050;">Failed to load page.</p>';
            console.error('[Guide] Load error:', e);
        }

        // Scroll to top
        const content = document.getElementById('guide-content');
        if (content) content.scrollTop = 0;
    }

    _attachListeners() {
        // Nav buttons
        const nav = document.getElementById('guide-nav');
        if (nav) {
            nav.addEventListener('click', (e) => {
                const btn = e.target.closest('.guide-nav-btn');
                if (btn) this._loadPage(btn.dataset.page);
            });
        }

        // Back button
        const backBtn = document.getElementById('btn-guide-back');
        if (backBtn) {
            backBtn.addEventListener('click', () => {
                window.router.navigate('main-menu', {
                    backgrounds: window._menuBackgrounds || []
                });
            });
        }
    }

    // ==================== Lightweight Markdown Renderer ====================

    _renderMarkdown(md) {
        const lines = md.split('\n');
        let html = '';
        let inList = false;
        let inTable = false;
        let tableRows = [];

        const inline = (text) => {
            return text
                // Bold
                .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
                // Italic
                .replace(/\*(.+?)\*/g, '<em>$1</em>')
                // Inline code
                .replace(/`(.+?)`/g, '<code>$1</code>')
                // Links
                .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
        };

        const flushTable = () => {
            if (!inTable || tableRows.length === 0) return '';
            let t = '<table class="md-table"><thead><tr>';
            const headers = tableRows[0];
            headers.forEach(h => { t += `<th>${inline(h.trim())}</th>`; });
            t += '</tr></thead><tbody>';
            // Skip row 1 (separator ---)
            for (let i = 2; i < tableRows.length; i++) {
                t += '<tr>';
                tableRows[i].forEach(cell => { t += `<td>${inline(cell.trim())}</td>`; });
                t += '</tr>';
            }
            t += '</tbody></table>';
            tableRows = [];
            inTable = false;
            return t;
        };

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];

            // Table row
            if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
                if (!inTable) inTable = true;
                const cells = line.trim().slice(1, -1).split('|');
                tableRows.push(cells);
                continue;
            } else if (inTable) {
                html += flushTable();
            }

            // Close list if needed
            if (inList && !line.match(/^\s*-\s/)) {
                html += '</ul>';
                inList = false;
            }

            // Horizontal rule
            if (line.trim() === '---' || line.trim() === '***') {
                html += '<hr class="md-hr">';
                continue;
            }

            // Headers
            const hMatch = line.match(/^(#{1,4})\s+(.+)/);
            if (hMatch) {
                const level = hMatch[1].length;
                html += `<h${level} class="md-h${level}">${inline(hMatch[2])}</h${level}>`;
                continue;
            }

            // List item
            const liMatch = line.match(/^\s*-\s+(.+)/);
            if (liMatch) {
                if (!inList) { html += '<ul class="md-list">'; inList = true; }
                html += `<li>${inline(liMatch[1])}</li>`;
                continue;
            }

            // Empty line
            if (line.trim() === '') {
                continue;
            }

            // Paragraph
            html += `<p class="md-p">${inline(line)}</p>`;
        }

        if (inList) html += '</ul>';
        if (inTable) html += flushTable();

        return html;
    }

    destroy() {
        if (this.element) {
            this.element.remove();
            this.element = null;
        }
        console.log('[Guide] Destroyed');
    }
}

window.router.registerScreen('guide', Guide);
