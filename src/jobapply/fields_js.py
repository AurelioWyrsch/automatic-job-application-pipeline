"""JavaScript evaluated inside a Form page (and each of its frames) to enumerate fillable fields."""

DETECT_FIELDS_JS = r"""
() => {
  const cssEscape = (s) => (window.CSS && CSS.escape) ? CSS.escape(s) : s.replace(/([^\w-])/g, '\\$1');
  const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();

  function selectorFor(el) {
    if (el.id && document.querySelectorAll('#' + cssEscape(el.id)).length === 1) return '#' + cssEscape(el.id);
    const tag = el.tagName.toLowerCase();
    if (el.name) {
      const sel = tag + '[name="' + el.name.replace(/"/g, '\\"') + '"]';
      if (document.querySelectorAll(sel).length === 1) return sel;
    }
    const parts = [];
    let node = el;
    while (node && node.nodeType === 1 && node !== document.body) {
      let part = node.tagName.toLowerCase();
      if (node.id) { parts.unshift('#' + cssEscape(node.id)); break; }
      const siblings = Array.from(node.parentNode ? node.parentNode.children : []).filter(c => c.tagName === node.tagName);
      if (siblings.length > 1) part += ':nth-of-type(' + (siblings.indexOf(node) + 1) + ')';
      parts.unshift(part);
      node = node.parentNode;
    }
    return parts.join(' > ');
  }

  function labelFor(el) {
    const hints = [];
    if (el.id) {
      document.querySelectorAll('label[for="' + cssEscape(el.id) + '"]').forEach(l => hints.push(clean(l.textContent)));
    }
    const wrapping = el.closest('label');
    if (wrapping) hints.push(clean(wrapping.textContent));
    const labelledBy = el.getAttribute('aria-labelledby');
    if (labelledBy) {
      labelledBy.split(/\s+/).forEach(id => { const n = document.getElementById(id); if (n) hints.push(clean(n.textContent)); });
    }
    if (el.getAttribute('aria-label')) hints.push(clean(el.getAttribute('aria-label')));
    // Nearest preceding text in the same container, for label-less layouts
    if (hints.filter(Boolean).length === 0) {
      let container = el.parentElement;
      for (let depth = 0; container && depth < 3; depth++) {
        const text = clean(Array.from(container.childNodes)
          .filter(n => n !== el && !(n.nodeType === 1 && n.querySelector && n.contains(el)))
          .map(n => n.textContent).join(' '));
        if (text && text.length < 120) { hints.push(text); break; }
        container = container.parentElement;
      }
    }
    return hints.filter(Boolean);
  }

  function isVisible(el) {
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden') return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 0 || rect.height > 0;
  }

  const elements = Array.from(document.querySelectorAll('input, select, textarea'));
  const skipTypes = new Set(['hidden', 'submit', 'button', 'reset', 'image']);
  const fields = [];
  const radioGroups = new Map();

  for (const el of elements) {
    const tag = el.tagName.toLowerCase();
    const type = tag === 'input' ? (el.type || 'text').toLowerCase() : tag;
    if (skipTypes.has(type)) continue;
    if (el.disabled) continue;
    const visible = isVisible(el);
    if (!visible && type !== 'file') continue;

    if (type === 'radio') {
      const key = el.name || selectorFor(el);
      if (!radioGroups.has(key)) {
        radioGroups.set(key, {
          selector: el.name ? 'input[type="radio"][name="' + el.name.replace(/"/g, '\\"') + '"]' : selectorFor(el),
          type: 'radio', name: el.name || '', id: '', label: '', hints: [], placeholder: '',
          required: !!el.required, multiple: false, options: [], accept: '',
        });
        const group = el.closest('fieldset');
        const legend = group ? group.querySelector('legend') : null;
        const g = radioGroups.get(key);
        if (legend) g.label = clean(legend.textContent);
        else if (group && group.getAttribute('aria-label')) g.label = clean(group.getAttribute('aria-label'));
        const labelledBy = (el.closest('[role="radiogroup"]') || {}).getAttribute ? el.closest('[role="radiogroup"]').getAttribute('aria-labelledby') : null;
        if (!g.label && labelledBy) { const n = document.getElementById(labelledBy); if (n) g.label = clean(n.textContent); }
      }
      const g = radioGroups.get(key);
      g.options.push({ value: el.value, label: labelFor(el)[0] || el.value });
      continue;
    }

    const hints = labelFor(el);
    const field = {
      selector: selectorFor(el),
      type,
      name: el.name || '',
      id: el.id || '',
      label: hints[0] || '',
      hints: hints.slice(1),
      placeholder: el.getAttribute('placeholder') || '',
      autocomplete: el.getAttribute('autocomplete') || '',
      required: !!el.required || el.getAttribute('aria-required') === 'true',
      multiple: !!el.multiple,
      accept: el.getAttribute('accept') || '',
      options: [],
      visible,
    };
    if (tag === 'select') {
      field.options = Array.from(el.options).map(o => ({ value: o.value, label: clean(o.textContent) })).filter(o => o.label);
    }
    fields.push(field);
  }
  for (const g of radioGroups.values()) fields.push(g);
  return { title: document.title, fields };
}
"""
