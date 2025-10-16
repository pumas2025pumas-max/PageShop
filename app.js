const STORAGE_KEY = 'costosApp';
const seed = {
  ingredientes: [
    { id: 'ing-harina', nombre: 'Harina', unidad: 'g', costo_por_unidad: 0.002 },
    { id: 'ing-queso', nombre: 'Queso', unidad: 'g', costo_por_unidad: 0.007 },
    { id: 'ing-salsa', nombre: 'Salsa', unidad: 'g', costo_por_unidad: 0.0012 }
  ],
  productos: [
    {
      id: 'prod-pizza-muzza',
      nombre: 'Pizza Muzza',
      unidad_salida: 'u',
      cantidad_salida: 1,
      componentes: [
        { ingrediente_id: 'ing-harina', cantidad_uso: 250 },
        { ingrediente_id: 'ing-queso', cantidad_uso: 200 },
        { ingrediente_id: 'ing-salsa', cantidad_uso: 80 }
      ]
    }
  ],
  seleccionado: { productoId: 'prod-pizza-muzza' }
};

let state = loadState();
let saveTimer = null;
let productSort = 'name-asc';
let ingredientSort = { field: 'nombre', direction: 'asc' };
const insightsCache = {
  productos: { value: null, sub: null },
  ingredientes: { value: null, sub: null },
  costo: { value: null, sub: null }
};

function uid() {
  return `id-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function parseNumber(value) {
  if (typeof value !== 'string' && typeof value !== 'number') return null;
  const normalized = String(value).replace(',', '.').trim();
  if (normalized === '') return null;
  const result = Number(normalized);
  return Number.isFinite(result) ? result : null;
}

const moneyFormatter = new Intl.NumberFormat('es-AR', {
  style: 'currency',
  currency: 'ARS',
  minimumFractionDigits: 2
});

function formatMoney(value) {
  return moneyFormatter.format(value || 0);
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function highlightMatch(text, query) {
  if (!query) return escapeHtml(text);
  const safeText = escapeHtml(text);
  const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'ig');
  return safeText.replace(regex, '<mark>$1</mark>');
}

function triggerInsightPulse(card) {
  if (!card) return;
  card.classList.remove('bump');
  void card.offsetWidth;
  card.classList.add('bump');
}

function updateInsightCard(key, valueText, subText) {
  const valueEl = document.getElementById(`insight${key.charAt(0).toUpperCase()}${key.slice(1)}`);
  const subEl = document.getElementById(`insight${key.charAt(0).toUpperCase()}${key.slice(1)}Sub`);
  const cache = insightsCache[key];
  if (!valueEl || !subEl || !cache) return;

  if (cache.value !== valueText) {
    cache.value = valueText;
    valueEl.textContent = valueText;
    triggerInsightPulse(valueEl.closest('.insight-card'));
  } else {
    valueEl.textContent = valueText;
  }

  if (cache.sub !== subText) {
    cache.sub = subText;
    subEl.textContent = subText;
  } else {
    subEl.textContent = subText;
  }
}

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return JSON.parse(JSON.stringify(seed));
    }
    const parsed = JSON.parse(raw);
    return {
      ingredientes: Array.isArray(parsed.ingredientes) ? parsed.ingredientes : [],
      productos: Array.isArray(parsed.productos) ? parsed.productos : [],
      seleccionado: parsed.seleccionado || { productoId: null }
    };
  } catch (error) {
    console.error('Error cargando estado', error);
    return JSON.parse(JSON.stringify(seed));
  }
}

function scheduleSave() {
  if (saveTimer) {
    clearTimeout(saveTimer);
  }
  saveTimer = setTimeout(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }, 300);
}

function setState(updater) {
  const nextState = typeof updater === 'function' ? updater(state) : updater;

  const activeElement = document.activeElement;
  const shouldPreserve =
    activeElement &&
    activeElement.hasAttribute('data-preserve-focus') &&
    typeof activeElement.id === 'string' &&
    activeElement.id.length > 0;
  const activeId = shouldPreserve ? activeElement.id : null;
  let selection = null;
  if (shouldPreserve) {
    try {
      const { selectionStart, selectionEnd } = activeElement;
      if (typeof selectionStart === 'number' && typeof selectionEnd === 'number') {
        selection = { start: selectionStart, end: selectionEnd };
      }
    } catch (_) {
      selection = null;
    }
  }

  state = nextState;
  scheduleSave();
  render();

  if (!activeId) {
    return;
  }

  const element = document.getElementById(activeId);
  if (!element || typeof element.focus !== 'function') {
    return;
  }

  element.focus();
  if (
    selection &&
    typeof element.setSelectionRange === 'function' &&
    typeof element.value === 'string'
  ) {
    const length = element.value.length;
    const start = Math.min(selection.start, length);
    const end = Math.min(selection.end, length);
    element.setSelectionRange(start, end);
  }
}

function updateState(partial) {
  setState({ ...state, ...partial });
}

function costoTanda(producto, ingredientesMap) {
  if (!producto) return 0;
  return producto.componentes.reduce((acc, comp) => {
    const ing = ingredientesMap.get(comp.ingrediente_id);
    if (!ing) return acc;
    return acc + comp.cantidad_uso * ing.costo_por_unidad;
  }, 0);
}

function costoUnidad(producto, ingredientesMap) {
  const tanda = costoTanda(producto, ingredientesMap);
  const salida = Math.max(parseNumber(producto?.cantidad_salida) || 0, 1);
  return tanda / salida;
}

function showToast(message, type = 'info') {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.style.borderColor = type === 'error' ? 'var(--danger)' : 'var(--border)';
  toast.style.color = type === 'error' ? 'var(--danger)' : 'inherit';
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2500);
}

function selectProduct(productId) {
  updateState({ seleccionado: { productoId } });
}

function getSelectedProduct() {
  return state.productos.find((p) => p.id === state.seleccionado?.productoId) || null;
}

function renderProductsList() {
  const list = document.getElementById('productList');
  list.innerHTML = '';
  const searchInput = document.getElementById('productSearch');
  const searchRaw = searchInput.value.trim();
  const search = searchRaw.toLowerCase();
  const sortSelect = document.getElementById('productSort');
  if (sortSelect && sortSelect.value !== productSort) {
    sortSelect.value = productSort;
  }
  const ingredientsMap = new Map(state.ingredientes.map((ing) => [ing.id, ing]));
  const filtered = state.productos.filter((prod) => prod.nombre.toLowerCase().includes(search));

  const decorated = filtered.map((prod) => {
    const costUnit = costoUnidad(prod, ingredientsMap);
    const tandaCost = costoTanda(prod, ingredientsMap);
    return {
      prod,
      costUnit,
      tandaCost,
      components: prod.componentes.length
    };
  });

  decorated.sort((a, b) => {
    switch (productSort) {
      case 'name-desc':
        return b.prod.nombre.localeCompare(a.prod.nombre, 'es', { sensitivity: 'base' });
      case 'cost-asc':
        return a.costUnit - b.costUnit;
      case 'cost-desc':
        return b.costUnit - a.costUnit;
      case 'name-asc':
      default:
        return a.prod.nombre.localeCompare(b.prod.nombre, 'es', { sensitivity: 'base' });
    }
  });

  if (!decorated.length) {
    const empty = document.createElement('div');
    empty.className = 'empty-state';
    empty.textContent = 'No hay productos. Crea uno nuevo para comenzar.';
    list.appendChild(empty);
    return;
  }

  decorated.forEach(({ prod, costUnit, tandaCost, components }) => {
    const item = document.createElement('button');
    item.type = 'button';
    item.className = `product-item${prod.id === state.seleccionado?.productoId ? ' active' : ''}`;
    item.setAttribute('role', 'option');
    item.setAttribute('aria-selected', prod.id === state.seleccionado?.productoId);

    const meta = document.createElement('div');
    meta.className = 'meta';
    const highlightedName = highlightMatch(prod.nombre, searchRaw);
    const componentLabel = `${components || 0} ${components === 1 ? 'ingrediente' : 'ingredientes'}`;
    const outputLabel = `${prod.cantidad_salida} ${prod.unidad_salida || 'u'}`.trim();
    meta.innerHTML = `
      <span class="title">${highlightedName}</span>
      <small>${componentLabel} · ${formatMoney(tandaCost)} la tanda · ${outputLabel}</small>
    `;

    const cost = document.createElement('span');
    cost.className = 'cost';
    cost.textContent = formatMoney(costUnit);

    item.title = `Costo por unidad: ${formatMoney(costUnit)}`;
    item.append(meta, cost);
    item.addEventListener('click', () => selectProduct(prod.id));
    list.appendChild(item);
  });
}

function renderProductDetail() {
  const container = document.getElementById('productDetail');
  const tag = document.getElementById('detalleTag');
  const product = getSelectedProduct();

  if (!product) {
    tag.textContent = 'Sin seleccionar';
    container.innerHTML = '<div class="empty-state">Selecciona o crea un producto para ver sus detalles.</div>';
    return;
  }

  tag.textContent = product.nombre;

  const ingredientsMap = new Map(state.ingredientes.map((ing) => [ing.id, ing]));
  const tanda = costoTanda(product, ingredientsMap);
  const unidad = costoUnidad(product, ingredientsMap);

  container.innerHTML = `
    <form id="productForm" class="form-grid" autocomplete="off">
      <div class="form-row">
        <label for="productName">Nombre</label>
        <input type="text" id="productName" value="${product.nombre}" required data-preserve-focus />
      </div>
      <div class="form-row">
        <label for="productUnit">Unidad de salida</label>
        <input type="text" id="productUnit" value="${product.unidad_salida || ''}" data-preserve-focus />
      </div>
      <div class="form-row">
        <label for="productOutput">Cantidad de salida</label>
        <input type="number" id="productOutput" value="${product.cantidad_salida}" min="1" data-preserve-focus />
      </div>
    </form>
    <div class="stats-grid" aria-live="polite">
      <div class="card stat-card">
        <span class="stat-title">Costo de la tanda</span>
        <span class="stat-value">${formatMoney(tanda)}</span>
      </div>
      <div class="card stat-card">
        <span class="stat-title">Costo por unidad</span>
        <span class="stat-value">${formatMoney(unidad)}</span>
      </div>
    </div>
    <div class="table-wrapper" aria-live="polite">
      <table>
        <thead>
          <tr>
            <th>Ingrediente</th>
            <th>Unidad</th>
            <th>Costo/u</th>
            <th>Cantidad</th>
            <th>Costo línea</th>
            <th></th>
          </tr>
        </thead>
        <tbody id="componentsTable"></tbody>
      </table>
    </div>
    <form id="componentForm" class="component-form" autocomplete="off">
      <div>
        <label for="componentIngredient">Ingrediente</label>
        <select id="componentIngredient" required>
          <option value="">Selecciona ingrediente</option>
          ${state.ingredientes.map((ing) => `<option value="${ing.id}">${ing.nombre}</option>`).join('')}
        </select>
      </div>
      <div>
        <label for="componentQuantity">Cantidad</label>
        <input type="text" id="componentQuantity" placeholder="0" required />
      </div>
      <div class="form-actions">
        <button type="submit" class="btn btn-primary">Agregar / Actualizar</button>
      </div>
      <p class="message" id="componentMessage" role="alert"></p>
    </form>
    <section class="card component-insights" id="componentInsights" aria-live="polite"></section>
  `;

  const productForm = document.getElementById('productForm');
  productForm.addEventListener('input', handleProductFormChange);
  productForm.addEventListener('submit', (e) => e.preventDefault());

  const componentsTable = document.getElementById('componentsTable');
  componentsTable.innerHTML = '';

  product.componentes.forEach((comp) => {
    const ing = ingredientsMap.get(comp.ingrediente_id);
    const tr = document.createElement('tr');
    const nombre = ing ? ing.nombre : 'Ingrediente eliminado';
    const unidadIng = ing ? ing.unidad : '-';
    const costoIng = ing ? formatMoney(ing.costo_por_unidad) : '-';
    const costoLinea = ing ? formatMoney(comp.cantidad_uso * ing.costo_por_unidad) : '-';

    tr.innerHTML = `
      <td>${nombre}</td>
      <td>${unidadIng}</td>
      <td>${costoIng}</td>
      <td>
        <input type="number" min="0" step="any" class="component-quantity" data-id="${comp.ingrediente_id}" value="${comp.cantidad_uso}" />
      </td>
      <td>${costoLinea}</td>
      <td><button type="button" class="btn btn-danger btn-sm" data-remove="${comp.ingrediente_id}">Eliminar</button></td>
    `;

    componentsTable.appendChild(tr);
  });

  componentsTable.querySelectorAll('.component-quantity').forEach((input) => {
    input.addEventListener('change', (event) => {
      const id = event.target.dataset.id;
      const value = parseNumber(event.target.value);
      if (value === null || value < 0) {
        showToast('La cantidad debe ser un número mayor o igual a 0', 'error');
        const original = product.componentes.find((c) => c.ingrediente_id === id)?.cantidad_uso || 0;
        event.target.value = original;
        return;
      }
      updateComponentQuantity(product.id, id, value);
    });
  });

  componentsTable.querySelectorAll('[data-remove]').forEach((btn) => {
    btn.addEventListener('click', () => {
      removeComponent(product.id, btn.dataset.remove);
    });
  });

  const componentForm = document.getElementById('componentForm');
  componentForm.addEventListener('submit', handleComponentSubmit);
  componentForm.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      componentForm.reset();
      document.getElementById('componentMessage').textContent = '';
    }
  });

  renderComponentInsights(product, ingredientsMap, tanda);
}

function renderComponentInsights(product, ingredientsMap, tanda) {
  const container = document.getElementById('componentInsights');
  if (!container) return;

  if (!product.componentes.length) {
    container.innerHTML = '<p class="empty">Agrega ingredientes para analizar su impacto.</p>';
    return;
  }

  const breakdown = product.componentes
    .map((comp) => {
      const ing = ingredientsMap.get(comp.ingrediente_id);
      if (!ing) return null;
      const lineCost = comp.cantidad_uso * ing.costo_por_unidad;
      const percentage = tanda > 0 ? (lineCost / tanda) * 100 : 0;
      return {
        nombre: ing.nombre,
        lineCost,
        percentage
      };
    })
    .filter(Boolean)
    .sort((a, b) => b.lineCost - a.lineCost);

  if (!breakdown.length) {
    container.innerHTML = '<p class="empty">Los ingredientes eliminados no se incluyen en el análisis.</p>';
    return;
  }

  const listItems = breakdown
    .map(
      (item) => `
        <li>
          <div class="label-row">
            <strong>${escapeHtml(item.nombre)}</strong>
            <span>${formatMoney(item.lineCost)} · ${item.percentage.toFixed(1)}%</span>
          </div>
          <div class="progress" role="presentation">
            <div class="progress-bar" style="transform: scaleX(${Math.min(1, item.percentage / 100)});"></div>
          </div>
        </li>
      `
    )
    .join('');

  container.innerHTML = `
    <h3>Impacto de componentes</h3>
    <ul>${listItems}</ul>
  `;
}

function handleProductFormChange() {
  const product = getSelectedProduct();
  if (!product) return;

  const name = document.getElementById('productName').value.trim();
  const unidad = document.getElementById('productUnit').value.trim();
  const cantidadRaw = document.getElementById('productOutput').value;
  const cantidad = Math.max(parseInt(cantidadRaw, 10) || 1, 1);

  updateState({
    productos: state.productos.map((p) =>
      p.id === product.id
        ? { ...p, nombre: name || 'Sin nombre', unidad_salida: unidad, cantidad_salida: cantidad }
        : p
    )
  });
}

function handleComponentSubmit(event) {
  event.preventDefault();
  const product = getSelectedProduct();
  if (!product) return;

  const ingredientId = document.getElementById('componentIngredient').value;
  const quantityStr = document.getElementById('componentQuantity').value;
  const messageEl = document.getElementById('componentMessage');
  messageEl.textContent = '';

  const quantity = parseNumber(quantityStr);
  if (!ingredientId) {
    messageEl.textContent = 'Selecciona un ingrediente válido';
    return;
  }
  if (quantity === null || quantity < 0) {
    messageEl.textContent = 'La cantidad debe ser un número mayor o igual a 0';
    return;
  }

  addOrUpdateComponent(product.id, ingredientId, quantity);
  event.target.reset();
  showToast('Componente actualizado');
}

function updateComponentQuantity(productId, ingredientId, quantity) {
  updateState({
    productos: state.productos.map((prod) => {
      if (prod.id !== productId) return prod;
      return {
        ...prod,
        componentes: prod.componentes.map((comp) =>
          comp.ingrediente_id === ingredientId ? { ...comp, cantidad_uso: quantity } : comp
        )
      };
    })
  });
}

function addOrUpdateComponent(productId, ingredientId, quantity) {
  updateState({
    productos: state.productos.map((prod) => {
      if (prod.id !== productId) return prod;
      const existing = prod.componentes.find((c) => c.ingrediente_id === ingredientId);
      if (existing) {
        return {
          ...prod,
          componentes: prod.componentes.map((c) =>
            c.ingrediente_id === ingredientId ? { ...c, cantidad_uso: quantity } : c
          )
        };
      }
      return {
        ...prod,
        componentes: [...prod.componentes, { ingrediente_id: ingredientId, cantidad_uso: quantity }]
      };
    })
  });
}

function removeComponent(productId, ingredientId) {
  updateState({
    productos: state.productos.map((prod) =>
      prod.id === productId
        ? { ...prod, componentes: prod.componentes.filter((c) => c.ingrediente_id !== ingredientId) }
        : prod
    )
  });
  showToast('Ingrediente quitado del producto');
}

function renderIngredients() {
  const tbody = document.getElementById('ingredientsTable');
  tbody.innerHTML = '';

  if (!state.ingredientes.length) {
    const tr = document.createElement('tr');
    const td = document.createElement('td');
    td.colSpan = 3;
    td.className = 'muted';
    td.textContent = 'Aún no hay ingredientes';
    tr.appendChild(td);
    tbody.appendChild(tr);
    updateIngredientSortHeaders();
    return;
  }

  const sorted = [...state.ingredientes].sort((a, b) => {
    const { field, direction } = ingredientSort;
    if (field === 'costo_por_unidad') {
      const diff = (a.costo_por_unidad || 0) - (b.costo_por_unidad || 0);
      return direction === 'asc' ? diff : -diff;
    }
    const valueA = (a[field] || '').toString().toLowerCase();
    const valueB = (b[field] || '').toString().toLowerCase();
    const result = valueA.localeCompare(valueB, 'es', { sensitivity: 'base' });
    return direction === 'asc' ? result : -result;
  });

  sorted.forEach((ing) => {
    const tr = document.createElement('tr');
    tr.tabIndex = 0;
    tr.innerHTML = `
      <td>${ing.nombre}</td>
      <td>${ing.unidad || '-'}</td>
      <td>${formatMoney(ing.costo_por_unidad)}</td>
    `;
    tr.addEventListener('click', () => populateIngredientForm(ing.id));
    tr.addEventListener('keypress', (event) => {
      if (event.key === 'Enter') {
        populateIngredientForm(ing.id);
      }
    });
    tbody.appendChild(tr);
  });

  updateIngredientSortHeaders();
}

function updateIngredientSortHeaders() {
  document.querySelectorAll('.sort-header').forEach((button) => {
    if (button.dataset.field === ingredientSort.field) {
      button.dataset.direction = ingredientSort.direction;
    } else {
      delete button.dataset.direction;
    }
  });
}

function populateIngredientForm(id) {
  const ing = state.ingredientes.find((item) => item.id === id);
  if (!ing) return;
  document.getElementById('ingredientId').value = ing.id;
  document.getElementById('ingredientName').value = ing.nombre;
  document.getElementById('ingredientUnit').value = ing.unidad || '';
  document.getElementById('ingredientCost').value = String(ing.costo_por_unidad);
  document.getElementById('ingredientDeleteBtn').disabled = false;
  document.getElementById('ingredientMessage').textContent = '';
}

function clearIngredientForm() {
  document.getElementById('ingredientForm').reset();
  document.getElementById('ingredientId').value = '';
  document.getElementById('ingredientDeleteBtn').disabled = true;
  document.getElementById('ingredientMessage').textContent = '';
}

function handleIngredientFormSubmit(event) {
  event.preventDefault();
  const id = document.getElementById('ingredientId').value;
  const nombre = document.getElementById('ingredientName').value.trim();
  const unidad = document.getElementById('ingredientUnit').value.trim();
  const costoStr = document.getElementById('ingredientCost').value;
  const messageEl = document.getElementById('ingredientMessage');
  messageEl.textContent = '';

  if (!nombre) {
    messageEl.textContent = 'El nombre es obligatorio';
    return;
  }

  const costo = parseNumber(costoStr);
  if (costo === null || costo < 0) {
    messageEl.textContent = 'El costo debe ser un número mayor o igual a 0';
    return;
  }

  const nameExists = state.ingredientes.some(
    (ing) => ing.nombre.toLowerCase() === nombre.toLowerCase() && ing.id !== id
  );
  if (nameExists) {
    messageEl.textContent = 'Ya existe un ingrediente con ese nombre';
    return;
  }

  if (id) {
    updateState({
      ingredientes: state.ingredientes.map((ing) =>
        ing.id === id ? { ...ing, nombre, unidad, costo_por_unidad: costo } : ing
      )
    });
    showToast('Ingrediente actualizado');
  } else {
    const newIngredient = { id: uid(), nombre, unidad, costo_por_unidad: costo };
    updateState({ ingredientes: [...state.ingredientes, newIngredient] });
    showToast('Ingrediente agregado');
  }

  clearIngredientForm();
}

function deleteIngredient() {
  const id = document.getElementById('ingredientId').value;
  if (!id) return;

  updateState({
    ingredientes: state.ingredientes.filter((ing) => ing.id !== id),
    productos: state.productos.map((prod) => ({
      ...prod,
      componentes: prod.componentes.filter((comp) => comp.ingrediente_id !== id)
    }))
  });

  showToast('Ingrediente eliminado');
  clearIngredientForm();
}

function handleIngredientSort(field) {
  if (ingredientSort.field === field) {
    ingredientSort = {
      field,
      direction: ingredientSort.direction === 'asc' ? 'desc' : 'asc'
    };
  } else {
    ingredientSort = {
      field,
      direction: field === 'costo_por_unidad' ? 'desc' : 'asc'
    };
  }
  renderIngredients();
}

function renderInsightsBar() {
  const bar = document.getElementById('insightsBar');
  if (!bar) return;

  const productosCount = state.productos.length;
  const productosSub = productosCount
    ? `${productosCount === 1 ? 'Producto disponible' : 'Productos disponibles'}`
    : 'Sin registros';
  updateInsightCard('productos', String(productosCount), productosSub);

  const ingredientesCount = state.ingredientes.length;
  const ingredientesSub = ingredientesCount
    ? `${ingredientesCount === 1 ? 'Ingrediente activo' : 'Ingredientes activos'}`
    : 'Sin registros';
  updateInsightCard('ingredientes', String(ingredientesCount), ingredientesSub);

  const ingredientsMap = new Map(state.ingredientes.map((ing) => [ing.id, ing]));
  const costos = state.productos
    .map((prod) => costoUnidad(prod, ingredientsMap))
    .filter((value) => Number.isFinite(value) && value >= 0);

  if (!costos.length) {
    updateInsightCard('costo', formatMoney(0), 'Crea productos para ver métricas');
    return;
  }

  const total = costos.reduce((acc, value) => acc + value, 0);
  const promedio = total / costos.length;
  const minimo = Math.min(...costos);
  const maximo = Math.max(...costos);
  const subMensaje =
    minimo === maximo
      ? `Valor estable en ${formatMoney(minimo)}`
      : `Rango ${formatMoney(minimo)} – ${formatMoney(maximo)}`;

  updateInsightCard('costo', formatMoney(promedio), subMensaje);
}

function createProduct() {
  const newProduct = {
    id: uid(),
    nombre: 'Nuevo producto',
    unidad_salida: 'u',
    cantidad_salida: 1,
    componentes: []
  };

  updateState({
    productos: [...state.productos, newProduct],
    seleccionado: { productoId: newProduct.id }
  });
  showToast('Producto creado');
}

function deleteSelectedProduct() {
  const product = getSelectedProduct();
  if (!product) return;

  const remaining = state.productos.filter((p) => p.id !== product.id);
  const nextSelection = remaining[0]?.id || null;

  updateState({ productos: remaining, seleccionado: { productoId: nextSelection } });
  showToast('Producto eliminado');
}

function duplicateSelectedProduct() {
  const product = getSelectedProduct();
  if (!product) return;

  const baseName = `${product.nombre} (copia)`;
  let uniqueName = baseName;
  let counter = 2;
  while (state.productos.some((p) => p.nombre === uniqueName)) {
    uniqueName = `${baseName} ${counter++}`;
  }

  const duplicate = {
    ...JSON.parse(JSON.stringify(product)),
    id: uid(),
    nombre: uniqueName
  };

  updateState({
    productos: [...state.productos, duplicate],
    seleccionado: { productoId: duplicate.id }
  });
  showToast('Producto duplicado');
}

function exportState() {
  const data = JSON.stringify(state, null, 2);
  const blob = new Blob([data], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'costos.json';
  a.click();
  URL.revokeObjectURL(url);
}

function importState(file) {
  const reader = new FileReader();
  reader.onload = (event) => {
    try {
      const parsed = JSON.parse(event.target.result);
      if (!Array.isArray(parsed.ingredientes) || !Array.isArray(parsed.productos)) {
        throw new Error('Formato inválido');
      }

      const confirmReplace = window.confirm('¿Reemplazar datos actuales?');
      if (!confirmReplace) return;

      state = {
        ingredientes: parsed.ingredientes,
        productos: parsed.productos,
        seleccionado: parsed.seleccionado || { productoId: null }
      };
      scheduleSave();
      render();
      showToast('Datos importados correctamente');
    } catch (error) {
      console.error(error);
      showToast('Archivo inválido', 'error');
    }
  };
  reader.readAsText(file);
}

function resetState() {
  const confirmReset = window.confirm('Esto borrará los datos actuales. ¿Continuar?');
  if (!confirmReset) return;
  state = JSON.parse(JSON.stringify(seed));
  scheduleSave();
  render();
  showToast('Datos restablecidos');
}

function handleGlobalShortcuts(event) {
  if (event.key === 'Escape') {
    clearIngredientForm();
    const componentForm = document.getElementById('componentForm');
    if (componentForm) {
      componentForm.reset();
      const message = document.getElementById('componentMessage');
      if (message) {
        message.textContent = '';
      }
    }
    return;
  }

  const target = event.target;
  const tag = target?.tagName?.toLowerCase();
  if (tag === 'input' || tag === 'textarea' || tag === 'select' || target?.isContentEditable) {
    return;
  }

  if (event.key === '/') {
    event.preventDefault();
    document.getElementById('productSearch').focus();
  }
}

function setupEvents() {
  document.getElementById('productSearch').addEventListener('input', renderProductsList);
  document.getElementById('productSort').addEventListener('change', (event) => {
    productSort = event.target.value;
    renderProductsList();
  });
  document.getElementById('newProductBtn').addEventListener('click', createProduct);
  document.getElementById('deleteProductBtn').addEventListener('click', deleteSelectedProduct);
  document.getElementById('duplicateProductBtn').addEventListener('click', duplicateSelectedProduct);

  document.getElementById('ingredientForm').addEventListener('submit', handleIngredientFormSubmit);
  document.getElementById('ingredientClearBtn').addEventListener('click', clearIngredientForm);
  document.getElementById('ingredientDeleteBtn').addEventListener('click', deleteIngredient);
  document.getElementById('ingredientForm').addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      event.preventDefault();
      clearIngredientForm();
    }
  });

  document.querySelectorAll('.sort-header').forEach((button) => {
    button.addEventListener('click', () => {
      handleIngredientSort(button.dataset.field);
      updateIngredientSortHeaders();
    });
  });

  document.getElementById('exportBtn').addEventListener('click', exportState);
  document.getElementById('importInput').addEventListener('change', (event) => {
    const [file] = event.target.files;
    if (file) {
      importState(file);
    }
    event.target.value = '';
  });
  document.getElementById('resetBtn').addEventListener('click', resetState);

  document.addEventListener('keydown', handleGlobalShortcuts);

  const mobileTabs = document.getElementById('mobileTabs');
  mobileTabs.querySelectorAll('button').forEach((button) => {
    button.addEventListener('click', () => {
      mobileTabs.querySelectorAll('button').forEach((b) => b.classList.remove('active'));
      button.classList.add('active');
      const target = button.dataset.target;
      document.querySelectorAll('.panel').forEach((panel) => {
        panel.classList.toggle('active', panel.id === `${target}Panel`);
      });
    });
  });
}

function ensureSelection() {
  const current = state.seleccionado?.productoId ?? null;
  const first = state.productos[0]?.id ?? null;
  if (current === first) {
    return;
  }
  updateState({ seleccionado: { productoId: first } });
}

function updateButtonsState() {
  const hasSelection = Boolean(getSelectedProduct());
  document.getElementById('deleteProductBtn').disabled = !hasSelection;
  document.getElementById('duplicateProductBtn').disabled = !hasSelection;
  const tag = document.getElementById('detalleTag');
  tag.classList.toggle('muted', !hasSelection);
}

function updatePanelsForViewport() {
  if (window.innerWidth <= 900) {
    const activeTab = document.querySelector('.mobile-tabs button.active')?.dataset.target || 'productos';
    document.querySelectorAll('.panel').forEach((panel) => {
      panel.classList.toggle('active', panel.id === `${activeTab}Panel`);
    });
  } else {
    document.querySelectorAll('.panel').forEach((panel) => panel.classList.add('active'));
  }
}

function render() {
  ensureSelection();
  renderProductsList();
  renderProductDetail();
  renderInsightsBar();
  renderIngredients();
  updateButtonsState();
  updatePanelsForViewport();
}

window.addEventListener('resize', updatePanelsForViewport);

setupEvents();
render();
