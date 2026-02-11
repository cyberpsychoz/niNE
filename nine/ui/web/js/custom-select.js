/**
 * Custom Select - Replaces native <select> elements with custom dropdowns.
 * Native <select> popups don't work in CEF offscreen rendering mode.
 *
 * Usage: call initCustomSelects() after DOM is ready.
 * The original <select> is hidden but kept in sync so form reads still work.
 */
(function() {
    window.initCustomSelects = function(container) {
        container = container || document;
        const selects = container.querySelectorAll('select:not([data-cs-init])');

        selects.forEach(select => {
            select.setAttribute('data-cs-init', 'true');
            select.style.display = 'none';

            // Create wrapper
            const wrapper = document.createElement('div');
            wrapper.className = 'custom-select';
            // Copy classes from original select for styling
            select.classList.forEach(cls => wrapper.classList.add(cls));

            // Display (shows current value)
            const display = document.createElement('div');
            display.className = 'cs-display';
            const label = document.createElement('span');
            label.className = 'cs-label';
            label.textContent = select.options[select.selectedIndex]?.text || '';
            const arrow = document.createElement('span');
            arrow.className = 'cs-arrow';
            display.appendChild(label);
            display.appendChild(arrow);

            // Dropdown list
            const dropdown = document.createElement('div');
            dropdown.className = 'cs-dropdown';

            function buildOptions() {
                dropdown.innerHTML = '';
                Array.from(select.options).forEach((option, i) => {
                    const item = document.createElement('div');
                    item.className = 'cs-option';
                    if (i === select.selectedIndex) item.classList.add('selected');
                    item.textContent = option.text;
                    item.dataset.value = option.value;

                    item.addEventListener('click', (e) => {
                        e.stopPropagation();
                        select.value = option.value;
                        select.dispatchEvent(new Event('change'));
                        label.textContent = option.text;
                        dropdown.querySelectorAll('.cs-option').forEach(o => o.classList.remove('selected'));
                        item.classList.add('selected');
                        close();
                    });

                    dropdown.appendChild(item);
                });
            }

            function close() {
                dropdown.classList.remove('open');
                wrapper.classList.remove('open');
            }

            display.addEventListener('click', (e) => {
                e.stopPropagation();
                // Close all other custom selects first
                document.querySelectorAll('.cs-dropdown.open').forEach(d => {
                    if (d !== dropdown) {
                        d.classList.remove('open');
                        d.parentElement.classList.remove('open');
                    }
                });
                dropdown.classList.toggle('open');
                wrapper.classList.toggle('open');
            });

            buildOptions();

            wrapper.appendChild(display);
            wrapper.appendChild(dropdown);
            select.parentNode.insertBefore(wrapper, select.nextSibling);
        });
    };

    // Close all custom selects on outside click
    document.addEventListener('click', () => {
        document.querySelectorAll('.cs-dropdown.open').forEach(d => {
            d.classList.remove('open');
            d.parentElement.classList.remove('open');
        });
    });
})();
