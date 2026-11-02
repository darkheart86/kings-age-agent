/* Run manually in the browser console AFTER logging in. Read-only; no network calls.
   Review the JSON before sharing it. Never share cookies, passwords or full page URLs. */
(() => {
  const trim = (s, max = 110) => String(s || '').replace(/\s+/g, ' ').trim().slice(0, max);
  const route = (url) => {
    try {
      const u = new URL(url, location.href);
      return u.host === location.host ? u.pathname : null; // Never include query, hash or tokens.
    } catch { return null; }
  };
  const hints = /resource|res[123]|wood|stone|iron|storage|castle|queue|build|madeira|pedra|ferro|armaz[eé]m|castelo|fila|constru/i;
  const elements = [...document.querySelectorAll('[id], [class]')]
    .filter(e => hints.test(`${e.id || ''} ${typeof e.className === 'string' ? e.className : ''}`))
    .slice(0, 70)
    .map(e => ({tag: e.tagName, id: trim(e.id, 60), class: trim(typeof e.className === 'string' ? e.className : '', 80), text: trim(e.innerText || e.textContent)}));
  const forms = [...document.forms].slice(0, 30).map(f => ({
    method: (f.method || 'get').toLowerCase(), action_path: route(f.action),
    fields: [...f.elements].slice(0, 40).map(e => ({tag: e.tagName, type: e.type || '', name: trim(e.name, 60)}))
  }));
  const controls = [...document.querySelectorAll('button, input[type=submit], a[href]')]
    .filter(e => hints.test(trim(e.innerText || e.value || e.textContent, 150)) || hints.test(e.id || '') || hints.test(typeof e.className === 'string' ? e.className : ''))
    .slice(0, 60).map(e => ({tag: e.tagName, text: trim(e.innerText || e.value || e.textContent, 70), path: e.href ? route(e.href) : null}));
  const snapshot = {host: location.host, page_path: location.pathname, elements, forms, controls};
  console.log(JSON.stringify(snapshot));
  return snapshot;
})();
