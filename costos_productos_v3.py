
import json
from dataclasses import dataclass, asdict, field
from typing import List, Optional
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# =============================
# Data Models
# =============================

@dataclass
class Insumo:
    nombre: str
    unidad_compra: str           # kg, L, unidad, etc.
    costo_por_unidad_compra: float
    factor_uso: float = 1.0      # cuántas unidades de uso hay en 1 unidad de compra (ej.: 1 kg = 1000 g)

    def costo_por_unidad_uso(self) -> float:
        # costo por 1 unidad de uso (g, ml, etc.)
        return self.costo_por_unidad_compra / max(self.factor_uso, 1e-12)

@dataclass
class IngredienteDeProducto:
    insumo_nombre: str           # referencia al catálogo por nombre
    cantidad_uso: float          # cantidad usada en unidades de uso del insumo
    override_costo_uso: Optional[float] = None   # permite reemplazar costo por unidad de uso del insumo

    def costo_total(self, insumo: Insumo) -> float:
        costo_uso = self.override_costo_uso if (self.override_costo_uso is not None and self.override_costo_uso >= 0) else insumo.costo_por_unidad_uso()
        return max(self.cantidad_uso,0) * max(costo_uso,0)

@dataclass
class Producto:
    nombre: str = "Nuevo producto"
    unidades_por_tanda: int = 1
    ingredientes: List[IngredienteDeProducto] = field(default_factory=list)
    kwh: float = 0.0
    tarifa_kwh: float = 0.0
    m3_gas: float = 0.0
    tarifa_m3_gas: float = 0.0
    horas: float = 0.0
    tarifa_hora: float = 0.0
    cargas_sociales_pct: float = 0.0
    empaque_unitario: float = 0.0
    otros_por_tanda: float = 0.0
    merma_pct: float = 0.0
    margen_pct: float = 0.0
    iva_pct: float = 0.0
    otros_impuestos_pct: float = 0.0
    redondeo: float = 0.0

    # --- cálculos ---
    def costo_ingredientes(self, catalogo: List[Insumo]) -> float:
        lookup = {i.nombre: i for i in catalogo}
        total = 0.0
        for ing in self.ingredientes:
            ins = lookup.get(ing.insumo_nombre)
            if ins:
                total += ing.costo_total(ins)
        return total

    def costo_energia(self) -> float:
        return max(self.kwh,0)*max(self.tarifa_kwh,0) + max(self.m3_gas,0)*max(self.tarifa_m3_gas,0)

    def costo_mano_obra(self) -> float:
        base = max(self.horas,0)*max(self.tarifa_hora,0)
        return base + base*max(self.cargas_sociales_pct,0)/100.0

    def costo_tanda(self, catalogo: List[Insumo]) -> float:
        return self.costo_ingredientes(catalogo) + self.costo_energia() + self.costo_mano_obra() + max(self.otros_por_tanda,0)

    def unidades_utiles(self) -> float:
        return max(self.unidades_por_tanda*(1 - max(self.merma_pct,0)/100.0), 1e-9)

    def costo_por_unidad_base(self, catalogo: List[Insumo]) -> float:
        return self.costo_tanda(catalogo)/self.unidades_utiles() + max(self.empaque_unitario,0)

    def precio_sin_impuestos(self, catalogo: List[Insumo]) -> float:
        return self.costo_por_unidad_base(catalogo)*(1 + max(self.margen_pct,0)/100.0)

    def precio_con_iva(self, catalogo: List[Insumo]) -> float:
        return self.precio_sin_impuestos(catalogo)*(1 + max(self.iva_pct,0)/100.0)

    def precio_final(self, catalogo: List[Insumo]) -> float:
        return self.precio_con_iva(catalogo)*(1 + max(self.otros_impuestos_pct,0)/100.0) + max(self.redondeo,0)

@dataclass
class Biblioteca:
    catalogo: List[Insumo] = field(default_factory=list)
    productos: List[Producto] = field(default_factory=list)

# =============================
# App
# =============================

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Costos de Productos — Productos + Catálogo de Insumos")
        self.geometry("1400x840")
        self.minsize(1200, 760)

        self.data = Biblioteca()
        self.current_index: Optional[int] = None  # producto seleccionado

        self._build_ui()
        self._wire_events()
        self._refresh_lists()

    # ---------- UI
    def _build_ui(self):
        # Top summary
        top = ttk.Frame(self, padding=(10,8))
        top.pack(fill="x")
        self.product_name_var = tk.StringVar(value="")
        ttk.Label(top, text="Producto:", font=("TkDefaultFont", 10, "bold")).pack(side="left")
        self.product_name_entry = ttk.Entry(top, textvariable=self.product_name_var, width=40)
        self.product_name_entry.pack(side="left", padx=6)

        self.quick_cost_var = tk.StringVar(value="Costo por unidad: $ 0,00")
        self.quick_price_var = tk.StringVar(value="Precio final: $ 0,00")
        ttk.Label(top, textvariable=self.quick_cost_var, font=("TkDefaultFont", 14, "bold"), foreground="#0B7285").pack(side="left", padx=16)
        ttk.Label(top, textvariable=self.quick_price_var, font=("TkDefaultFont", 14, "bold"), foreground="#2B8A3E").pack(side="left", padx=10)

        # Paned: Productos | Detalle | Catálogo
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True)

        # ---- Productos (izquierda)
        left = ttk.Frame(paned, padding=8)
        paned.add(left, weight=1)

        header_left = ttk.Frame(left)
        header_left.pack(fill="x")
        ttk.Label(header_left, text="Productos", font=("TkDefaultFont", 11, "bold")).pack(side="left")
        self.search_prod_var = tk.StringVar()
        ttk.Entry(header_left, textvariable=self.search_prod_var, width=20).pack(side="right")
        self.search_prod_var.trace_add("write", lambda *_: self._refresh_product_list())

        cols = ("nombre","costo_u","precio_u")
        self.products_tree = ttk.Treeview(left, columns=cols, show="headings", height=16)
        self.products_tree.heading("nombre", text="Nombre")
        self.products_tree.heading("costo_u", text="Costo / unidad")
        self.products_tree.heading("precio_u", text="Precio final")
        self.products_tree.column("nombre", width=200)
        self.products_tree.column("costo_u", width=120, anchor="e")
        self.products_tree.column("precio_u", width=120, anchor="e")
        self.products_tree.pack(fill="both", expand=True, pady=6)
        self.products_tree.bind("<<TreeviewSelect>>", self._on_select_product)

        btns_left = ttk.Frame(left)
        btns_left.pack(fill="x")
        ttk.Button(btns_left, text="Nuevo", command=self.new_product).pack(side="left")
        ttk.Button(btns_left, text="Duplicar", command=self.duplicate_product).pack(side="left", padx=4)
        ttk.Button(btns_left, text="Eliminar", command=self.delete_product).pack(side="left")
        ttk.Button(btns_left, text="Guardar biblioteca…", command=self.save_library).pack(side="right")
        ttk.Button(btns_left, text="Abrir biblioteca…", command=self.open_library).pack(side="right", padx=4)

        # ---- Detalle del Producto (centro)
        center = ttk.Frame(paned, padding=8)
        paned.add(center, weight=2)

        top_detail = ttk.Frame(center)
        top_detail.pack(fill="x")
        ttk.Label(top_detail, text="Unidades por tanda:").grid(row=0, column=0, sticky='w')
        self.unidades_var = tk.StringVar(value="1")
        ttk.Entry(top_detail, textvariable=self.unidades_var, width=10).grid(row=0, column=1, sticky='w', padx=6)

        # Ingredientes del producto
        ing_frame = ttk.LabelFrame(center, text="Ingredientes del producto (seleccionados del catálogo)", padding=8)
        ing_frame.pack(fill="both", expand=True, pady=6)

        icolumns = ("insumo","cantidad","costo_uso","costo_total")
        self.ing_tree = ttk.Treeview(ing_frame, columns=icolumns, show="headings", height=10)
        for c, title in zip(icolumns, ["Insumo", "Cantidad usada (unidad de uso)", "Costo unidad (override opcional)", "Costo total"]):
            self.ing_tree.heading(c, text=title)
            self.ing_tree.column(c, width=180 if c!="costo_total" else 120, anchor='center')
        self.ing_tree.grid(row=0, column=0, columnspan=6, sticky='nsew')
        ing_frame.rowconfigure(0, weight=1); ing_frame.columnconfigure(0, weight=1)
        scroll = ttk.Scrollbar(ing_frame, orient="vertical", command=self.ing_tree.yview)
        self.ing_tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=0, column=6, sticky='ns')

        form = ttk.Frame(ing_frame)
        form.grid(row=1, column=0, columnspan=7, sticky='ew', pady=4)
        for i in range(10): form.columnconfigure(i, weight=1)

        self.insumo_sel_var = tk.StringVar()
        self.cant_sel_var = tk.StringVar()
        self.override_sel_var = tk.StringVar()

        ttk.Label(form, text="Insumo").grid(row=0, column=0, sticky='w')
        self.insumo_combo = ttk.Combobox(form, textvariable=self.insumo_sel_var, values=[], width=28, state="readonly")
        self.insumo_combo.grid(row=1, column=0, sticky='we', padx=3)
        ttk.Label(form, text="Cantidad usada").grid(row=0, column=1, sticky='w')
        ttk.Entry(form, textvariable=self.cant_sel_var, width=12).grid(row=1, column=1, sticky='we', padx=3)
        ttk.Label(form, text="Override $ / unidad uso (opcional)").grid(row=0, column=2, sticky='w')
        ttk.Entry(form, textvariable=self.override_sel_var, width=18).grid(row=1, column=2, sticky='we', padx=3)
        ttk.Button(form, text="Agregar/Actualizar", command=self.add_or_update_ing).grid(row=1, column=3, padx=6)
        ttk.Button(form, text="Eliminar", command=self.remove_selected_ing).grid(row=1, column=4)

        # Costos adicionales
        extras = ttk.LabelFrame(center, text="Costos adicionales", padding=8)
        extras.pack(fill="x", pady=6)
        self.kwh_var = tk.StringVar(value="0"); self.tarifa_kwh_var = tk.StringVar(value="0")
        self.m3_var = tk.StringVar(value="0"); self.tarifa_m3_var = tk.StringVar(value="0")
        self.horas_var = tk.StringVar(value="0"); self.tarifa_hora_var = tk.StringVar(value="0")
        self.cargas_var = tk.StringVar(value="0")
        self.empaque_var = tk.StringVar(value="0"); self.otros_tanda_var = tk.StringVar(value="0")
        self.merma_var = tk.StringVar(value="0"); self.margen_var = tk.StringVar(value="0")
        self.iva_var = tk.StringVar(value="0"); self.otros_imp_var = tk.StringVar(value="0"); self.redondeo_var = tk.StringVar(value="0")

        grid = [
            ("kWh", self.kwh_var), ("$/kWh", self.tarifa_kwh_var),
            ("m³ gas", self.m3_var), ("$/m³", self.tarifa_m3_var),
            ("Horas", self.horas_var), ("$/hora", self.tarifa_hora_var), ("% cargas", self.cargas_var),
            ("Empaque/u", self.empaque_var), ("Otros por tanda", self.otros_tanda_var),
            ("% Merma", self.merma_var), ("% Margen", self.margen_var),
            ("% IVA", self.iva_var), ("% Otros imp.", self.otros_imp_var), ("Redondeo $", self.redondeo_var)
        ]
        for i,(label,var) in enumerate(grid):
            ttk.Label(extras, text=label).grid(row=i//4*2, column=i%4*2, sticky='w', padx=2, pady=1)
            ttk.Entry(extras, textvariable=var, width=10).grid(row=i//4*2+1, column=i%4*2, sticky='we', padx=2, pady=1)

        ttk.Button(center, text="Calcular", command=self.calculate).pack(anchor="w", pady=6)

        # Resultados
        res = ttk.LabelFrame(center, text="Resultados", padding=8)
        res.pack(fill="x", pady=6)
        self.costo_ing_var = tk.StringVar(value="$ 0.00")
        self.costo_ener_var = tk.StringVar(value="$ 0.00")
        self.costo_mo_var = tk.StringVar(value="$ 0.00")
        self.costo_tanda_var = tk.StringVar(value="$ 0.00")
        self.unidades_utiles_var = tk.StringVar(value="0")
        self.costo_u_var = tk.StringVar(value="$ 0.00")
        self.precio_u_sin_var = tk.StringVar(value="$ 0.00")
        self.precio_u_iva_var = tk.StringVar(value="$ 0.00")
        self.precio_u_final_var = tk.StringVar(value="$ 0.00")

        rows = [
            ("Ingredientes (tanda)", self.costo_ing_var),
            ("Energía (tanda)", self.costo_ener_var),
            ("Mano de obra (tanda)", self.costo_mo_var),
            ("TOTAL TANDA", self.costo_tanda_var),
            ("Unidades útiles", self.unidades_utiles_var),
            ("Costo base por unidad", self.costo_u_var),
            ("Precio sin impuestos", self.precio_u_sin_var),
            ("Precio con IVA", self.precio_u_iva_var),
            ("Precio final sugerido", self.precio_u_final_var),
        ]
        for r,(label,var) in enumerate(rows):
            ttk.Label(res, text=label).grid(row=r, column=0, sticky='w', pady=2)
            ttk.Label(res, textvariable=var, font=("TkDefaultFont", 11, "bold")).grid(row=r, column=1, sticky='w', padx=8)

        # ---- Catálogo (derecha)
        right = ttk.Frame(paned, padding=8)
        paned.add(right, weight=1)

        header_right = ttk.Frame(right)
        header_right.pack(fill="x")
        ttk.Label(header_right, text="Catálogo de Insumos", font=("TkDefaultFont", 11, "bold")).pack(side="left")
        self.search_insumo_var = tk.StringVar()
        ttk.Entry(header_right, textvariable=self.search_insumo_var, width=20).pack(side="right")
        self.search_insumo_var.trace_add("write", lambda *_: self._refresh_catalog())

        ccols = ("nombre", "unidad_compra", "costo_unidad", "factor_uso", "costo_uso")
        self.catalog_tree = ttk.Treeview(right, columns=ccols, show="headings", height=16)
        for c,t in zip(ccols, ["Nombre", "Unidad compra", "$/unidad compra", "Factor uso", "$/unidad uso"]):
            self.catalog_tree.heading(c, text=t)
            self.catalog_tree.column(c, width=140 if c!="costo_uso" else 120, anchor='center')
        self.catalog_tree.pack(fill="both", expand=True, pady=6)
        self.catalog_tree.bind("<<TreeviewSelect>>", self._on_select_insumo)

        form_cat = ttk.LabelFrame(right, text="Editar/Agregar Insumo", padding=8)
        form_cat.pack(fill="x")
        self.in_nombre_var = tk.StringVar(); self.in_unidad_var = tk.StringVar()
        self.in_costo_var = tk.StringVar(); self.in_factor_var = tk.StringVar(value="1")
        ttk.Label(form_cat, text="Nombre").grid(row=0, column=0, sticky='w'); ttk.Entry(form_cat, textvariable=self.in_nombre_var, width=22).grid(row=1, column=0, sticky='we', padx=3)
        ttk.Label(form_cat, text="Unidad compra").grid(row=0, column=1, sticky='w'); ttk.Entry(form_cat, textvariable=self.in_unidad_var, width=14).grid(row=1, column=1, sticky='we', padx=3)
        ttk.Label(form_cat, text="$/unidad compra").grid(row=0, column=2, sticky='w'); ttk.Entry(form_cat, textvariable=self.in_costo_var, width=14).grid(row=1, column=2, sticky='we', padx=3)
        ttk.Label(form_cat, text="Factor uso").grid(row=0, column=3, sticky='w'); ttk.Entry(form_cat, textvariable=self.in_factor_var, width=10).grid(row=1, column=3, sticky='we', padx=3)
        ttk.Button(form_cat, text="Agregar/Actualizar", command=self.add_or_update_insumo).grid(row=1, column=4, padx=6)
        ttk.Button(form_cat, text="Eliminar", command=self.remove_selected_insumo).grid(row=1, column=5)

    # ---------- Events & helpers
    def _wire_events(self):
        for var in [
            self.product_name_var, self.unidades_var, self.kwh_var, self.tarifa_kwh_var, self.m3_var, self.tarifa_m3_var,
            self.horas_var, self.tarifa_hora_var, self.cargas_var, self.empaque_var, self.otros_tanda_var,
            self.merma_var, self.margen_var, self.iva_var, self.otros_imp_var, self.redondeo_var
        ]:
            var.trace_add("write", lambda *_: self.calculate())
        self.product_name_var.trace_add("write", lambda *_: self._sync_product_name())

    def _num(self, s):
        try: return float(str(s).replace(",", "."))
        except: return 0.0

    # ---------- Catalog CRUD
    def _refresh_catalog(self):
        query = self.search_insumo_var.get().strip().lower()
        self.catalog_tree.delete(*self.catalog_tree.get_children())
        for ins in self.data.catalogo:
            if query and query not in ins.nombre.lower():
                continue
            self.catalog_tree.insert("", "end", values=(
                ins.nombre, ins.unidad_compra, f"{ins.costo_por_unidad_compra:,.2f}", f"{ins.factor_uso:,.2f}", f"{ins.costo_por_unidad_uso():,.4f}"
            ))
        # actualizar combo de ingredientes
        self.insumo_combo["values"] = [i.nombre for i in self.data.catalogo]

    def _on_select_insumo(self, _):
        sel = self.catalog_tree.selection()
        if not sel: return
        v = self.catalog_tree.item(sel[0], "values")
        self.in_nombre_var.set(v[0]); self.in_unidad_var.set(v[1])
        self.in_costo_var.set(str(v[2]).replace(",","").replace(" ",""))
        self.in_factor_var.set(str(v[3]).replace(",","").replace(" ",""))

    def add_or_update_insumo(self):
        try:
            nombre = self.in_nombre_var.get().strip()
            unidad = self.in_unidad_var.get().strip()
            costo = float(self.in_costo_var.get().replace(",", "."))
            factor = float(self.in_factor_var.get().replace(",", "."))
        except:
            messagebox.showerror("Datos inválidos", "Completá nombre y números válidos."); return
        if not nombre:
            messagebox.showerror("Falta nombre", "Ingresá un nombre."); return

        # update or insert
        updated = False
        for i, ins in enumerate(self.data.catalogo):
            if ins.nombre == nombre:
                self.data.catalogo[i] = Insumo(nombre, unidad, costo, factor)
                updated = True; break
        if not updated:
            self.data.catalogo.append(Insumo(nombre, unidad, costo, factor))

        self._refresh_catalog()
        self.calculate()  # propaga costos a productos
        self.in_nombre_var.set(""); self.in_unidad_var.set(""); self.in_costo_var.set(""); self.in_factor_var.set("1")

    def remove_selected_insumo(self):
        sel = self.catalog_tree.selection()
        if not sel: return
        name = self.catalog_tree.item(sel[0], "values")[0]
        if not messagebox.askyesno("Eliminar insumo", f"Eliminar '{name}' del catálogo?\nLos productos que lo usen quedarán con referencia huérfana."):
            return
        self.data.catalogo = [i for i in self.data.catalogo if i.nombre != name]
        # Quitar ingredientes huérfanos
        for p in self.data.productos:
            p.ingredientes = [ing for ing in p.ingredientes if ing.insumo_nombre != name]
        self._refresh_catalog()
        self._refresh_product_list()
        self._refresh_product_detail()
        self.calculate()

    # ---------- Products CRUD
    def _refresh_product_list(self):
        query = self.search_prod_var.get().strip().lower()
        self.products_tree.delete(*self.products_tree.get_children())
        for idx, p in enumerate(self.data.productos):
            if query and query not in p.nombre.lower():
                continue
            cost_u = p.costo_por_unidad_base(self.data.catalogo)
            price_u = p.precio_final(self.data.catalogo)
            self.products_tree.insert("", "end", iid=str(idx), values=(p.nombre, f"$ {cost_u:,.2f}", f"$ {price_u:,.2f}"))
        # Ensure selection
        if self.current_index is not None and str(self.current_index) in self.products_tree.get_children(""):
            self.products_tree.selection_set(str(self.current_index))

    def _on_select_product(self, _):
        sel = self.products_tree.selection()
        if not sel: return
        self.current_index = int(sel[0])
        self._refresh_product_detail()

    def _refresh_product_detail(self):
        # load into UI
        p = self.data.productos[self.current_index] if self.current_index is not None and self.current_index < len(self.data.productos) else None
        if not p:
            self.product_name_var.set("")
            self.unidades_var.set("1")
            self.ing_tree.delete(*self.ing_tree.get_children())
            for var in [self.kwh_var,self.tarifa_kwh_var,self.m3_var,self.tarifa_m3_var,self.horas_var,self.tarifa_hora_var,self.cargas_var,
                        self.empaque_var,self.otros_tanda_var,self.merma_var,self.margen_var,self.iva_var,self.otros_imp_var,self.redondeo_var]:
                var.set("0")
            self.calculate(); return

        self.product_name_var.set(p.nombre)
        self.unidades_var.set(str(p.unidades_por_tanda))
        # ingredientes table
        self.ing_tree.delete(*self.ing_tree.get_children())
        lookup = {i.nombre:i for i in self.data.catalogo}
        for ing in p.ingredientes:
            ins = lookup.get(ing.insumo_nombre)
            costo_uso = ing.override_costo_uso if ing.override_costo_uso is not None else (ins.costo_por_unidad_uso() if ins else 0.0)
            total = (costo_uso * ing.cantidad_uso) if ins or ing.override_costo_uso is not None else 0.0
            self.ing_tree.insert("", "end", values=(ing.insumo_nombre, f"{ing.cantidad_uso:,.2f}", f"{costo_uso:,.4f}", f"$ {total:,.2f}"))
        # extras
        self.kwh_var.set(str(p.kwh)); self.tarifa_kwh_var.set(str(p.tarifa_kwh))
        self.m3_var.set(str(p.m3_gas)); self.tarifa_m3_var.set(str(p.tarifa_m3_gas))
        self.horas_var.set(str(p.horas)); self.tarifa_hora_var.set(str(p.tarifa_hora)); self.cargas_var.set(str(p.cargas_sociales_pct))
        self.empaque_var.set(str(p.empaque_unitario)); self.otros_tanda_var.set(str(p.otros_por_tanda))
        self.merma_var.set(str(p.merma_pct)); self.margen_var.set(str(p.margen_pct)); self.iva_var.set(str(p.iva_pct))
        self.otros_imp_var.set(str(p.otros_impuestos_pct)); self.redondeo_var.set(str(p.redondeo))
        self.calculate()

    def _sync_product_from_ui(self):
        if self.current_index is None or self.current_index >= len(self.data.productos): return
        p = self.data.productos[self.current_index]
        p.nombre = self.product_name_var.get().strip() or "Producto"
        try: p.unidades_por_tanda = int(float(self.unidades_var.get().replace(",", ".")))
        except: p.unidades_por_tanda = 1
        p.kwh = self._num(self.kwh_var.get()); p.tarifa_kwh = self._num(self.tarifa_kwh_var.get())
        p.m3_gas = self._num(self.m3_var.get()); p.tarifa_m3_gas = self._num(self.tarifa_m3_var.get())
        p.horas = self._num(self.horas_var.get()); p.tarifa_hora = self._num(self.tarifa_hora_var.get()); p.cargas_sociales_pct = self._num(self.cargas_var.get())
        p.empaque_unitario = self._num(self.empaque_var.get()); p.otros_por_tanda = self._num(self.otros_tanda_var.get())
        p.merma_pct = self._num(self.merma_var.get()); p.margen_pct = self._num(self.margen_var.get())
        p.iva_pct = self._num(self.iva_var.get()); p.otros_impuestos_pct = self._num(self.otros_imp_var.get()); p.redondeo = self._num(self.redondeo_var.get())

    def _sync_product_name(self):
        if self.current_index is None or self.current_index >= len(self.data.productos): return
        self.data.productos[self.current_index].nombre = self.product_name_var.get().strip() or "Producto"
        self._refresh_product_list()

    def new_product(self):
        self.data.productos.append(Producto())
        self.current_index = len(self.data.productos)-1
        self._refresh_product_list()
        self._refresh_product_detail()

    def duplicate_product(self):
        if self.current_index is None: 
            messagebox.showinfo("Duplicar", "Seleccioná un producto."); return
        import copy
        pcopy = copy.deepcopy(self.data.productos[self.current_index])
        pcopy.nombre = pcopy.nombre + " (copia)"
        self.data.productos.append(pcopy)
        self.current_index = len(self.data.productos)-1
        self._refresh_product_list()
        self._refresh_product_detail()

    def delete_product(self):
        if self.current_index is None: 
            messagebox.showinfo("Eliminar", "Seleccioná un producto."); return
        name = self.data.productos[self.current_index].nombre
        if not messagebox.askyesno("Eliminar producto", f"Eliminar '{name}'?"): return
        del self.data.productos[self.current_index]
        self.current_index = None if not self.data.productos else 0
        self._refresh_product_list()
        self._refresh_product_detail()

    # ---------- Ingredients in product
    def add_or_update_ing(self):
        if self.current_index is None: 
            messagebox.showinfo("Ingrediente", "Primero creá o seleccioná un producto."); return
        pname = self.insumo_sel_var.get().strip()
        if not pname:
            messagebox.showerror("Insumo", "Elegí un insumo del catálogo."); return
        try:
            cant = float(self.cant_sel_var.get().replace(",", "."))
        except:
            messagebox.showerror("Cantidad", "Ingresá una cantidad válida."); return
        override = self.override_sel_var.get().strip()
        ovalue = None
        if override:
            try: ovalue = float(override.replace(",", "."))
            except: messagebox.showerror("Override", "Override debe ser número."); return

        p = self.data.productos[self.current_index]
        # update if exists
        updated = False
        for ing in p.ingredientes:
            if ing.insumo_nombre == pname:
                ing.cantidad_uso = cant
                ing.override_costo_uso = ovalue
                updated = True; break
        if not updated:
            p.ingredientes.append(IngredienteDeProducto(insumo_nombre=pname, cantidad_uso=cant, override_costo_uso=ovalue))

        self.cant_sel_var.set(""); self.override_sel_var.set("")
        self._refresh_product_detail()

    def remove_selected_ing(self):
        if self.current_index is None: return
        sel = self.ing_tree.selection()
        if not sel: return
        insumo_name = self.ing_tree.item(sel[0], "values")[0]
        p = self.data.productos[self.current_index]
        p.ingredientes = [i for i in p.ingredientes if i.insumo_nombre != insumo_name]
        self._refresh_product_detail()

    # ---------- Save / Open biblioteca
    def save_library(self):
        self._sync_product_from_ui()
        data = {
            "catalogo": [asdict(i) for i in self.data.catalogo],
            "productos": [asdict(p) for p in self.data.productos],
        }
        path = filedialog.asksaveasfilename(title="Guardar biblioteca", defaultextension=".json",
                                            filetypes=[("JSON","*.json")], initialfile="productos_catalogo.json")
        if not path: return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self._refresh_product_list()
            messagebox.showinfo("Guardado", "Biblioteca guardada correctamente.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def open_library(self):
        path = filedialog.askopenfilename(title="Abrir biblioteca", filetypes=[("JSON","*.json")])
        if not path: return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.data.catalogo = [Insumo(**d) for d in data.get("catalogo",[])]
            self.data.productos = [Producto(**d) for d in data.get("productos",[])]
            self.current_index = 0 if self.data.productos else None
            self._refresh_lists()
            messagebox.showinfo("Cargado", "Biblioteca cargada.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ---------- Calc
    def calculate(self):
        # ensure UI → model sync
        self._sync_product_from_ui()

        p = self.data.productos[self.current_index] if self.current_index is not None and self.current_index < len(self.data.productos) else None
        if not p:
            self.quick_cost_var.set("Costo por unidad: $ 0,00")
            self.quick_price_var.set("Precio final: $ 0,00")
            return

        ci = p.costo_ingredientes(self.data.catalogo)
        ce = p.costo_energia()
        cm = p.costo_mano_obra()
        ct = p.costo_tanda(self.data.catalogo)
        uu = p.unidades_utiles()
        cu = p.costo_por_unidad_base(self.data.catalogo)
        ps = p.precio_sin_impuestos(self.data.catalogo)
        pi = p.precio_con_iva(self.data.catalogo)
        pf = p.precio_final(self.data.catalogo)

        self.costo_ing_var.set(f"$ {ci:,.2f}")
        self.costo_ener_var.set(f"$ {ce:,.2f}")
        self.costo_mo_var.set(f"$ {cm:,.2f}")
        self.costo_tanda_var.set(f"$ {ct:,.2f}")
        self.unidades_utiles_var.set(f"{uu:,.2f}")
        self.costo_u_var.set(f"$ {cu:,.2f}")
        self.precio_u_sin_var.set(f"$ {ps:,.2f}")
        self.precio_u_iva_var.set(f"$ {pi:,.2f}")
        self.precio_u_final_var.set(f"$ {pf:,.2f}")

        self.quick_cost_var.set(f"Costo por unidad: $ {cu:,.2f}")
        self.quick_price_var.set(f"Precio final: $ {pf:,.2f}")
        # update products list numbers
        self._refresh_product_list()

        # update ingredient table totals
        self._refresh_product_detail()  # re-renders row totals

    def _refresh_lists(self):
        self._refresh_catalog()
        self._refresh_product_list()
        if self.data.productos:
            self.current_index = 0
        self._refresh_product_detail()

if __name__ == "__main__":
    app = App()
    app.mainloop()
