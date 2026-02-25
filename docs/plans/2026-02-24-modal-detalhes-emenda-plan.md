# Modal de Detalhes da Emenda - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a centered modal popup that opens when clicking a historico table row, showing Município, Destino, and Valor.

**Architecture:** Single-file change to `index.html`. Add modal HTML markup, two JS functions (`openEmendaModal`/`closeEmendaModal`), wire onclick to table rows, add Escape key listener. No backend changes.

**Tech Stack:** HTML, vanilla JavaScript, Tailwind CSS (CDN)

---

### Task 1: Add Modal HTML Markup

**Files:**
- Modify: `index.html:309` (insert before the Mobile Bottom Sheet section)

**Step 1: Add the modal HTML**

Insert this block right before `<!-- Mobile Bottom Sheet -->` (line 310):

```html
<!-- Emenda Detail Modal -->
<div id="emendaModal" class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center hidden transition-opacity duration-200 opacity-0" onclick="if(event.target===this)closeEmendaModal()">
    <div id="emendaModalCard" class="bg-white rounded-2xl shadow-2xl p-6 mx-4 max-w-md w-full transform transition-transform duration-200 scale-95">
        <!-- Header -->
        <div class="flex items-center justify-between mb-6">
            <h3 class="text-lg font-bold text-primary font-display">Detalhes da Emenda</h3>
            <button onclick="closeEmendaModal()" class="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 transition-colors">
                <span class="material-symbols-outlined text-gray-400 hover:text-gray-600">close</span>
            </button>
        </div>
        <!-- Fields -->
        <div class="space-y-5">
            <div>
                <p class="text-xs text-gray-500 uppercase tracking-wider mb-1">Município</p>
                <p id="modalMunicipio" class="text-lg font-semibold text-gray-900"></p>
            </div>
            <div>
                <p class="text-xs text-gray-500 uppercase tracking-wider mb-1">Destino</p>
                <p id="modalDestino" class="text-lg font-semibold text-gray-900"></p>
            </div>
            <div>
                <p class="text-xs text-gray-500 uppercase tracking-wider mb-1">Valor</p>
                <p id="modalValor" class="text-2xl font-bold text-blue-600"></p>
            </div>
        </div>
    </div>
</div>
```

**Step 2: Verify the modal is present in the DOM**

Open the app in browser, inspect the page, confirm `#emendaModal` element exists and is hidden.

**Step 3: Commit**

```bash
git add index.html
git commit -m "feat: add emenda detail modal HTML markup"
```

---

### Task 2: Add Modal Open/Close JavaScript Functions

**Files:**
- Modify: `index.html` (inside the `<script>` block, after the `closeSheet()` function around line 451)

**Step 1: Add the modal functions**

Insert after the `closeSheet()` function (after line 451):

```javascript
// --- Emenda Detail Modal ---
function openEmendaModal(municipio, destino, valorRaw) {
    document.getElementById('modalMunicipio').textContent = municipio;
    document.getElementById('modalDestino').textContent = destino;
    document.getElementById('modalValor').textContent = formatCurrency(valorRaw);
    const modal = document.getElementById('emendaModal');
    modal.classList.remove('hidden');
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            modal.classList.remove('opacity-0');
            document.getElementById('emendaModalCard').classList.remove('scale-95');
        });
    });
    document.body.style.overflow = 'hidden';
}

function closeEmendaModal() {
    const modal = document.getElementById('emendaModal');
    modal.classList.add('opacity-0');
    document.getElementById('emendaModalCard').classList.add('scale-95');
    setTimeout(() => {
        modal.classList.add('hidden');
        document.body.style.overflow = '';
    }, 200);
}

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !document.getElementById('emendaModal').classList.contains('hidden')) {
        closeEmendaModal();
    }
});
```

**Step 2: Verify functions exist**

Open browser console, type `openEmendaModal('São Paulo', 'Hospital ABC', 150000)`. Confirm modal appears with correct data. Press Escape to close.

**Step 3: Commit**

```bash
git add index.html
git commit -m "feat: add openEmendaModal/closeEmendaModal JS functions"
```

---

### Task 3: Wire Table Row Clicks to Modal

**Files:**
- Modify: `index.html:688-716` (the `data.historico.forEach` loop in `renderDashboard`)

**Step 1: Add onclick handler to each table row**

In the `renderDashboard` function, after `tr.innerHTML = ...` and before `tbody.appendChild(tr)` (around line 715-716), add:

```javascript
tr.addEventListener('click', () => {
    openEmendaModal(row.municipio, row.destino, row.valor_raw);
});
```

**Step 2: Manual test**

1. Open the app in browser
2. Search for a parlamentar (e.g., any name that returns results)
3. Click on a row in the "Histórico de Emendas" table
4. Confirm modal opens with correct Município, Destino, and Valor
5. Close via X button, clicking overlay, and Escape key - all three should work

**Step 3: Commit**

```bash
git add index.html
git commit -m "feat: wire historico table rows to emenda detail modal"
```

---

### Task 4: Final Verification

**Step 1: Full manual test**

1. Load page fresh
2. Search for a parlamentar
3. Click different rows - verify each shows correct data
4. Test close: X button, overlay click, Escape key
5. Test on mobile viewport (resize browser to ~375px width) - modal should be nearly full-width with `mx-4`
6. Verify body scroll is locked when modal is open and restored when closed

**Step 2: Final commit (squash if needed)**

```bash
git add index.html
git commit -m "feat: add emenda detail modal to historico table

Clicking a row in the historico table opens a centered modal
showing Município, Destino, and Valor. Closes via X button,
overlay click, or Escape key."
```
