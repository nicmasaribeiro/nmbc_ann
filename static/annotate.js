// static/annotate.js
(function(){
  // ---- Elements ----
  const docEl       = document.getElementById('doc');
  const listEl      = document.getElementById('ann-list');
  const pop         = document.getElementById('ann-pop');
  const txt         = document.getElementById('ann-text');
  const btnSave     = document.getElementById('ann-save');
  const btnCancel   = document.getElementById('ann-cancel');
  const btnAnnotate = document.getElementById('annotate-btn');

  // Read-only viewer popup
  const viewPop     = document.getElementById('ann-view');
  const viewContent = document.getElementById('ann-view-content');
  const viewClose   = document.getElementById('ann-view-close');
  const viewDelete  = document.getElementById('ann-view-delete');

  if (!docEl) { console.warn('annotate.js: #doc not found'); return; }

  if (viewClose) viewClose.onclick = ()=> viewPop.classList.add('hidden');

  // Track what we've already drawn to prevent duplicates
  const RENDERED_IDS = new Set();

  // ---- Helpers (DOM/list) ----
  function escapeHTML(s){ return (s||"").replace(/[&<>"]/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c])); }

  function dedupeById(arr){
    const map = new Map();
    for (const a of arr || []) if (!map.has(a.id)) map.set(a.id, a);
    return [...map.values()];
  }

  function itemHTML(a){
    const del = a.can_delete ? `<a href="#" class="ann-del" data-id="${a.id}" style="margin-left:8px;">🗑 Delete</a>` : "";
    const contentRow = a.content ? `<div class="ann-note">${escapeHTML(a.content)}</div>` : '';
    const commentsBlock = a.comments && a.comments.length
      ? a.comments.map(c=>`<div class="muted">${escapeHTML(c.user)}: ${escapeHTML(c.text)}</div>`).join('')
      : '';
    return `<div class="item" data-id="${a.id}" data-can-delete="${a.can_delete ? '1' : '0'}">
      <div>
        <strong>${escapeHTML(a.user)}</strong> — <em>${escapeHTML(a.anchor.slice(0,64))}${a.anchor.length>64?'…':''}</em>
        ${del}
      </div>
      ${contentRow}
      ${commentsBlock}
    </div>`;
  }

  function ensureSingleListItem(a){
    if (!listEl) return;
    const existing = listEl.querySelector(`.item[data-id="${a.id}"]`);
    if (existing) return;
    listEl.insertAdjacentHTML('afterbegin', itemHTML(a));
    // Notify any glue code (for counters / filters)
    document.dispatchEvent(new CustomEvent('annotations:updated'));
  }

  function cleanupDuplicateMarks(){
    const groups = {};
    docEl.querySelectorAll('mark.ann').forEach(m => {
      const id = m.dataset.id || '';
      (groups[id] ||= []).push(m);
    });
    for (const id in groups){
      const marks = groups[id];
      for (let i=1; i<marks.length; i++){
        const m = marks[i];
        const p = m.parentNode;
        while (m.firstChild) p.insertBefore(m.firstChild, m);
        p.removeChild(m);
      }
    }
  }

  // ---- Load and render existing annotations ----
  fetch(`/api/documents/${DOC_ID}/annotations`)
    .then(r=>r.json())
    .then(anns=>{
      const uniq = dedupeById(anns);
      uniq.forEach(a=>{
        highlightByNormalizedRange(a.start, a.end, a.color, a.id, a.content || a.anchor);
        ensureSingleListItem(a);
      });
      cleanupDuplicateMarks();
    })
    .catch(e=>console.error('Failed to load annotations:', e));

  // ---- Selection & popover (create) ----
  if (typeof CAN_ANNOTATE !== "undefined" && CAN_ANNOTATE){
    docEl.addEventListener('mouseup', () => setTimeout(onMaybeSelect, 0));
    document.addEventListener('selectionchange', () => toggleAnnotateButton(window.getSelection()));
    if (btnAnnotate) btnAnnotate.addEventListener('click', () => {
      const sel = window.getSelection();
      if (sel && !sel.isCollapsed && docEl.contains(sel.anchorNode) && docEl.contains(sel.focusNode)) openPopoverFor(sel);
    });
  }
  function onMaybeSelect(){
    const sel = window.getSelection();
    toggleAnnotateButton(sel);
    if (sel && !sel.isCollapsed && docEl.contains(sel.anchorNode) && docEl.contains(sel.focusNode)) openPopoverFor(sel);
  }
  function toggleAnnotateButton(sel){
    if (!btnAnnotate) return;
    const ok = !!sel && !sel.isCollapsed && docEl.contains(sel.anchorNode) && docEl.contains(sel.focusNode);
    btnAnnotate.disabled = !ok;
  }

  function openPopoverFor(sel){
    const {start, end, anchor} = selectionNormalizedOffsets(docEl, sel);
    if (start === null) return;
    if (pop) pop.classList.remove('hidden');
    if (txt) txt.value = '';

    if (btnSave) btnSave.onclick = async () => {
      const note = (txt && txt.value ? txt.value : '').trim();
      const body = {start, end, anchor, color: undefined, note};
      try {
        const res = await fetch(`/api/documents/${DOC_ID}/annotations`, {
          method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify(body)
        });
        const text = await res.text();
        if (!res.ok) throw new Error(text || 'HTTP error');
        const {id} = JSON.parse(text);
        const tooltip = note || anchor;
        ensureSingleListItem({id, start, end, anchor, color:'yellow', user:'you', content: note, comments: note ? [{id:0, text:note, user:'you'}] : [], can_delete:true});
        highlightByNormalizedRange(start, end, 'yellow', id, tooltip);
      } catch (e){
        alert('Could not save annotation: ' + e.message);
      } finally {
        if (pop) pop.classList.add('hidden');
        sel.removeAllRanges();
        toggleAnnotateButton(window.getSelection());
      }
    };
    if (btnCancel) btnCancel.onclick = ()=>{ if (pop) pop.classList.add('hidden'); };
  }

  // ---- Delete from sidebar (🗑) ----
  if (listEl){
    listEl.addEventListener('click', async (e) => {
      const del = e.target.closest('.ann-del');
      if (!del) return;
      e.preventDefault();
      const id = del.dataset.id;
      if (!confirm('Delete this annotation?')) return;
      try{
        const res = await fetch(`/api/annotations/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error(await res.text());
        const item = listEl.querySelector(`.item[data-id="${id}"]`);
        if (item) item.remove();
        document.querySelectorAll(`mark.ann[data-id="${id}"]`).forEach(mark => {
          const p = mark.parentNode; while (mark.firstChild) p.insertBefore(mark.firstChild, mark); p.removeChild(mark);
        });
        RENDERED_IDS.delete(String(id));
        document.dispatchEvent(new CustomEvent('annotations:updated'));
      } catch (e){
        alert('Could not delete annotation: ' + e.message);
      }
    });

    // Clicking a list item scrolls to its highlight
    listEl.addEventListener('click', (e) => {
      const item = e.target.closest('.item');
      if (!item || e.target.closest('.ann-del')) return;
      const id = item.dataset.id;
      const mark = docEl.querySelector(`mark.ann[data-id="${id}"]`);
      if (!mark) return;
      mark.scrollIntoView({ behavior:'smooth', block:'center', inline:'nearest' });
      mark.classList.add('pulse');
      setTimeout(() => mark.classList.remove('pulse'), 1600);
    });
  }

  // ---- Click highlight to open read-only popup (+ delete there) ----
  docEl.addEventListener('click', (e) => {
    const m = e.target.closest('mark.ann');
    if (!m || !viewPop || !viewContent) return;
    const id = m.dataset.id;
    const item = listEl ? listEl.querySelector(`.item[data-id="${id}"]`) : null;

    const parts = [];
    const firstNote = item ? item.querySelector(':scope > .ann-note') : null;
    const comments = item ? [...item.querySelectorAll('.muted')].map(n=>n.textContent) : [];
    if (firstNote && firstNote.textContent.trim()) parts.push(firstNote.textContent.trim());
    if (comments.length) parts.push(comments.join('\n'));

    viewContent.textContent = parts.join('\n\n') || m.getAttribute('title') || 'No content.';
    viewPop.dataset.id = id;

    if (viewDelete) {
      const can = item && item.dataset.canDelete === '1';
      viewDelete.style.display = can ? '' : 'none';
    }

    viewPop.classList.remove('hidden');
  });

  if (viewDelete){
    viewDelete.addEventListener('click', async () => {
      const id = viewPop.dataset.id;
      if (!id) return;
      if (!confirm('Delete this annotation?')) return;
      try{
        const res = await fetch(`/api/annotations/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error(await res.text());
        viewPop.classList.add('hidden');
        const item = listEl ? listEl.querySelector(`.item[data-id="${id}"]`) : null;
        if (item) item.remove();
        document.querySelectorAll(`mark.ann[data-id="${id}"]`).forEach(mark => {
          const p = mark.parentNode; while (mark.firstChild) p.insertBefore(mark.firstChild, mark); p.removeChild(mark);
        });
        RENDERED_IDS.delete(String(id));
        document.dispatchEvent(new CustomEvent('annotations:updated'));
      } catch (e){
        alert('Could not delete annotation: ' + e.message);
      }
    });
  }

  // ---- Normalization (match server: collapse \s+ -> ' ') ----
  function normalizeAdvance(ch, inWS){ const isWS=/\s/.test(ch); if(isWS) return {delta: inWS?0:1, inWS:true}; return {delta:1, inWS:false}; }
  function normLen(s){ let n=0,inWS=false; for(let i=0;i<s.length;i++){ const r=normalizeAdvance(s[i],inWS); n+=r.delta; inWS=r.inWS; } return n; }
  function normIndexForRaw(s, off){ let n=0,inWS=false; for(let i=0;i<off;i++){ const r=normalizeAdvance(s[i],inWS); n+=r.delta; inWS=r.inWS; } return n; }

  function textNodes(root){
    const out=[]; const w=document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {acceptNode: ()=>NodeFilter.FILTER_ACCEPT});
    let n; while(n=w.nextNode()) out.push(n); return out;
  }

  function buildNormalizedPlain(nodes){
    let out="", inWS=false;
    for (const tn of nodes){
      const s=tn.nodeValue;
      for (let i=0;i<s.length;i++){
        const r = normalizeAdvance(s[i], inWS);
        if (r.delta) out += /\s/.test(s[i]) ? ' ' : s[i];
        inWS = r.inWS;
      }
    }
    return out.trim();
  }

  function selectionNormalizedOffsets(root, sel){
    const nodes = textNodes(root);
    if (!nodes.length) return {start:null,end:null,anchor:""};
    const range = sel.getRangeAt(0);
    let seenNorm=0, startNorm=null, endNorm=null;
    for (const tn of nodes){
      const t = tn.nodeValue;
      if (range.startContainer === tn) startNorm = seenNorm + normIndexForRaw(t, range.startOffset);
      if (range.endContainer === tn){ endNorm = seenNorm + normIndexForRaw(t, range.endOffset); break; }
      seenNorm += normLen(t);
    }
    if (startNorm===null || endNorm===null || endNorm<=startNorm) return {start:null,end:null,anchor:""};
    const fullPlain = buildNormalizedPlain(nodes);
    return { start:startNorm, end:endNorm, anchor: fullPlain.slice(startNorm, endNorm) };
  }

  function seekRawPosForNorm(nodes, targetNorm){
    let cumNorm=0;
    for (const tn of nodes){
      const t = tn.nodeValue, thisNorm = normLen(t);
      if (targetNorm <= cumNorm + thisNorm){
        const need = targetNorm - cumNorm;
        let n=0, inWS=false;
        for (let i=0;i<=t.length;i++){
          if (n >= need) return {node: tn, offset: i};
          const r = normalizeAdvance(t[i], inWS); n += r.delta; inWS = r.inWS;
        }
        return {node: tn, offset: t.length};
      }
      cumNorm += thisNorm;
    }
    const last = nodes[nodes.length-1];
    return {node:last, offset:last.nodeValue.length};
  }

  // ---- Render highlight (idempotent; yellow color) ----
  function highlightByNormalizedRange(startNorm, endNorm, color, id, tooltip){
    if (!id && id !== 0) return;
    if (RENDERED_IDS.has(String(id))) return;
    if (docEl.querySelector(`mark.ann[data-id="${id}"]`)) {
      RENDERED_IDS.add(String(id));
      return; // already present
    }

    // Force yellow highlight unless overridden
    const bg = color || 'yellow';

    const nodes = textNodes(docEl);
    const a = seekRawPosForNorm(nodes, startNorm);
    const b = seekRawPosForNorm(nodes, endNorm);

    const r = document.createRange();
    r.setStart(a.node, Math.min(a.offset, a.node.nodeValue.length));
    r.setEnd(b.node, Math.min(b.offset, b.node.nodeValue.length));

    const mark = document.createElement('mark');
    mark.className = 'ann';
    mark.dataset.id = id;
    mark.style.background = bg;           // <-- yellow
    mark.style.color = 'inherit';         // keep text readable
    if (tooltip) mark.title = tooltip;    // native hover tooltip

    try {
      const contents = r.extractContents();
      mark.appendChild(contents);
      r.insertNode(mark);
    } catch(e) { console.warn('Highlight insertion failed:', e); }

    // Click to open read-only viewer (mirror of docEl click handler, in case others attach later)
    if (viewPop && viewContent) {
      mark.addEventListener('click', () => {
        const item = listEl ? listEl.querySelector(`.item[data-id="${id}"]`) : null;
        const parts = [];
        const firstNote = item ? item.querySelector(':scope > .ann-note') : null;
        const comments = item ? [...item.querySelectorAll('.muted')].map(n=>n.textContent) : [];
        if (firstNote && firstNote.textContent.trim()) parts.push(firstNote.textContent.trim());
        if (comments.length) parts.push(comments.join('\n'));
        viewContent.textContent = parts.join('\n\n') || mark.getAttribute('title') || 'No content.';
        viewPop.dataset.id = id;
        if (viewDelete) {
          const can = item && item.dataset.canDelete === '1';
          viewDelete.style.display = can ? '' : 'none';
        }
        viewPop.classList.remove('hidden');
      });
    }

    RENDERED_IDS.add(String(id));
  }

})();
