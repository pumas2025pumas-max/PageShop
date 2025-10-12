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
  state = nextState;
  scheduleSave();
  render();
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
  const search = document.getElementById('productSearch').value.trim().toLowerCase();
  const ingredientsMap = new Map(state.ingredientes.map((ing) => [ing.id, ing]));
  const filtered = state.productos.filter((prod) => prod.nombre.toLowerCase().includes(search));

  if (!filtered.length) {
    const empty = document.createElement('div');
    empty.className = 'empty-state';
    empty.textContent = 'No hay productos. Crea uno nuevo para comenzar.';
    list.appendChild(empty);
    return;
  }

  filtered.forEach((prod) => {
    const item = document.createElement('button');
    item.type = 'button';
    item.className = `product-item${prod.id === state.seleccionado?.productoId ? ' active' : ''}`;
    item.setAttribute('role', 'option');
    item.setAttribute('aria-selected', prod.id === state.seleccionado?.productoId);

    const left = document.createElement('div');
    left.innerHTML = `<strong>${prod.nombre}</strong>`;

    const cost = document.createElement('span');
    cost.className = 'cost';
    cost.textContent = formatMoney(costoUnidad(prod, ingredientsMap));

    item.append(left, cost);
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
        <input type="text" id="productName" value="${product.nombre}" required />
      </div>
      <div class="form-row">
        <label for="productUnit">Unidad de salida</label>
        <input type="text" id="productUnit" value="${product.unidad_salida || ''}" />
      </div>
      <div class="form-row">
        <label for="productOutput">Cantidad de salida</label>
        <input type="number" id="productOutput" value="${product.cantidad_salida}" min="1" />
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
    return;
  }

  state.ingredientes.forEach((ing) => {
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
  }
}

function setupEvents() {
  document.getElementById('productSearch').addEventListener('input', renderProductsList);
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
  renderIngredients();
  updateButtonsState();
  updatePanelsForViewport();
}

window.addEventListener('resize', updatePanelsForViewport);

setupEvents();
render();
