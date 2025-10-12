import json
import copy
from dataclasses import dataclass, field, asdict
from typing import List, Optional
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


# -----------------------------
# Data models
# -----------------------------

@dataclass
class Insumo:
    nombre: str
    unidad_compra: str
    costo_por_unidad_compra: float
    factor_uso: float

    def costo_por_unidad_uso(self) -> float:
        factor = self.factor_uso if self.factor_uso > 0 else 1e-9
        return self.costo_por_unidad_compra / factor


@dataclass
class IngredienteDeProducto:
    insumo_nombre: str
    cantidad_uso: float
    override_costo_uso: Optional[float] = None

    def costo_total(self, insumo: Insumo) -> float:
        if self.override_costo_uso is not None and self.override_costo_uso >= 0:
            costo_unitario = self.override_costo_uso
        else:
            costo_unitario = insumo.costo_por_unidad_uso()
        cantidad = self.cantidad_uso if self.cantidad_uso >= 0 else 0
        return cantidad * max(costo_unitario, 0)


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

    def costo_ingredientes(self, catalogo: List[Insumo]) -> float:
        lookup = {insumo.nombre: insumo for insumo in catalogo}
        total = 0.0
        for ingrediente in self.ingredientes:
            insumo = lookup.get(ingrediente.insumo_nombre)
            if insumo:
                total += ingrediente.costo_total(insumo)
        return total

    def costo_energia(self) -> float:
        return max(self.kwh, 0) * max(self.tarifa_kwh, 0) + max(self.m3_gas, 0) * max(self.tarifa_m3_gas, 0)

    def costo_mano_obra(self) -> float:
        base = max(self.horas, 0) * max(self.tarifa_hora, 0)
        return base + base * max(self.cargas_sociales_pct, 0) / 100.0

    def costo_tanda(self, catalogo: List[Insumo]) -> float:
        return self.costo_ingredientes(catalogo) + self.costo_energia() + self.costo_mano_obra() + max(self.otros_por_tanda, 0)

    def unidades_utiles(self) -> float:
        merma_factor = 1 - max(self.merma_pct, 0) / 100.0
        return max(self.unidades_por_tanda * merma_factor, 1e-9)

    def costo_por_unidad_base(self, catalogo: List[Insumo]) -> float:
        return self.costo_tanda(catalogo) / self.unidades_utiles() + max(self.empaque_unitario, 0)

    def precio_sin_impuestos(self, catalogo: List[Insumo]) -> float:
        return self.costo_por_unidad_base(catalogo) * (1 + max(self.margen_pct, 0) / 100.0)

    def precio_con_iva(self, catalogo: List[Insumo]) -> float:
        return self.precio_sin_impuestos(catalogo) * (1 + max(self.iva_pct, 0) / 100.0)

    def precio_final(self, catalogo: List[Insumo]) -> float:
        return self.precio_con_iva(catalogo) * (1 + max(self.otros_impuestos_pct, 0) / 100.0) + max(self.redondeo, 0)


@dataclass
class Biblioteca:
    catalogo: List[Insumo] = field(default_factory=list)
    productos: List[Producto] = field(default_factory=list)


# -----------------------------
# Utilidades
# -----------------------------

def parse_float(value: str, default: float = 0.0) -> float:
    if value is None:
        return default
    value = value.strip().replace(",", ".")
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        raise


def parse_int(value: str, default: int = 0) -> int:
    try:
        return int(round(parse_float(value, default)))
    except ValueError:
        raise


def format_currency(value: float) -> str:
    text = f"{value:,.2f}"
    text = text.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"$ {text}"


def format_number(value: float) -> str:
    text = f"{value:,.2f}"
    text = text.replace(",", "X").replace(".", ",").replace("X", ".")
    return text


# -----------------------------
# Aplicación
# -----------------------------


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Costos de Productos")
        self.geometry("1500x900")
        self.minsize(1300, 780)

        self.data = Biblioteca()
        self.current_index: Optional[int] = None
        self.current_insumo: Optional[str] = None
        self._updating_ui = False

        self.product_search_var = tk.StringVar()
        self.catalog_search_var = tk.StringVar()

        self.product_name_var = tk.StringVar()
        self.quick_cost_var = tk.StringVar(value="Costo por unidad: $ 0,00")
        self.quick_price_var = tk.StringVar(value="Precio final: $ 0,00")

        # Mapeo de campos del producto a StringVar
        self.product_vars = {
            "unidades_por_tanda": tk.StringVar(value="1"),
            "kwh": tk.StringVar(value="0"),
            "tarifa_kwh": tk.StringVar(value="0"),
            "m3_gas": tk.StringVar(value="0"),
            "tarifa_m3_gas": tk.StringVar(value="0"),
            "horas": tk.StringVar(value="0"),
            "tarifa_hora": tk.StringVar(value="0"),
            "cargas_sociales_pct": tk.StringVar(value="0"),
            "empaque_unitario": tk.StringVar(value="0"),
            "otros_por_tanda": tk.StringVar(value="0"),
            "merma_pct": tk.StringVar(value="0"),
            "margen_pct": tk.StringVar(value="0"),
            "iva_pct": tk.StringVar(value="0"),
            "otros_impuestos_pct": tk.StringVar(value="0"),
            "redondeo": tk.StringVar(value="0"),
        }

        self.costo_ing_var = tk.StringVar(value="$ 0,00")
        self.costo_ener_var = tk.StringVar(value="$ 0,00")
        self.costo_mo_var = tk.StringVar(value="$ 0,00")
        self.costo_tanda_var = tk.StringVar(value="$ 0,00")
        self.unidades_utiles_var = tk.StringVar(value="0,00")
        self.costo_u_var = tk.StringVar(value="$ 0,00")
        self.precio_u_sin_var = tk.StringVar(value="$ 0,00")
        self.precio_u_iva_var = tk.StringVar(value="$ 0,00")
        self.precio_u_final_var = tk.StringVar(value="$ 0,00")

        self.insumo_vars = {
            "nombre": tk.StringVar(),
            "unidad_compra": tk.StringVar(),
            "costo_por_unidad_compra": tk.StringVar(),
            "factor_uso": tk.StringVar(value="1"),
        }

        self.insumo_sel_var = tk.StringVar()
        self.cant_sel_var = tk.StringVar()
        self.override_sel_var = tk.StringVar()

        self._build_ui()
        self._wire_traces()
        self._refresh_all()

    # -------------------------
    # Construcción de UI
    # -------------------------

    def _build_ui(self) -> None:
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True)

        left_frame = ttk.Frame(paned, padding=8)
        center_frame = ttk.Frame(paned, padding=8)
        right_frame = ttk.Frame(paned, padding=8)

        paned.add(left_frame, weight=1)
        paned.add(center_frame, weight=2)
        paned.add(right_frame, weight=1)

        self._build_products_panel(left_frame)
        self._build_product_detail_panel(center_frame)
        self._build_catalog_panel(right_frame)

    def _build_products_panel(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Productos", font=("TkDefaultFont", 12, "bold")).pack(anchor="w")

        search_frame = ttk.Frame(parent)
        search_frame.pack(fill="x", pady=(6, 4))
        ttk.Label(search_frame, text="Buscar:").pack(side="left")
        entry = ttk.Entry(search_frame, textvariable=self.product_search_var)
        entry.pack(side="left", fill="x", expand=True, padx=(4, 0))

        columns = ("nombre", "costo", "precio")
        self.product_tree = ttk.Treeview(parent, columns=columns, show="headings", height=18)
        self.product_tree.heading("nombre", text="Nombre")
        self.product_tree.heading("costo", text="Costo / unidad")
        self.product_tree.heading("precio", text="Precio final")
        self.product_tree.column("nombre", width=220)
        self.product_tree.column("costo", width=120, anchor="e")
        self.product_tree.column("precio", width=120, anchor="e")
        scroll = ttk.Scrollbar(parent, orient="vertical", command=self.product_tree.yview)
        self.product_tree.configure(yscrollcommand=scroll.set)
        self.product_tree.pack(fill="both", expand=True, side="left")
        scroll.pack(fill="y", side="left")

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill="x", pady=8)
        ttk.Button(btn_frame, text="Nuevo", command=self.new_product).pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="Duplicar", command=self.duplicate_product).pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="Eliminar", command=self.delete_product).pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="Guardar biblioteca…", command=self.save_library).pack(fill="x", pady=(12, 2))
        ttk.Button(btn_frame, text="Abrir biblioteca…", command=self.open_library).pack(fill="x", pady=2)

    def _build_product_detail_panel(self, parent: ttk.Frame) -> None:
        summary = ttk.LabelFrame(parent, text="Resumen")
        summary.pack(fill="x", pady=(0, 10))
        ttk.Label(summary, textvariable=self.quick_cost_var, font=("TkDefaultFont", 14, "bold"), foreground="#004c99").pack(side="left", padx=8, pady=4)
        ttk.Label(summary, textvariable=self.quick_price_var, font=("TkDefaultFont", 14, "bold"), foreground="#007a33").pack(side="left", padx=8, pady=4)
        ttk.Button(summary, text="Calcular", command=self._update_results).pack(side="right", padx=8, pady=4)

        general = ttk.LabelFrame(parent, text="Datos generales del producto")
        general.pack(fill="x", pady=6)
        self._create_labeled_entry(general, "Nombre", self.product_name_var, 0, 0, columnspan=3)
        self._create_labeled_entry(general, "Unidades por tanda", self.product_vars["unidades_por_tanda"], 0, 3)

        # Ingredientes
        ing_frame = ttk.LabelFrame(parent, text="Ingredientes del producto")
        ing_frame.pack(fill="both", expand=True, pady=6)

        edit_frame = ttk.Frame(ing_frame)
        edit_frame.pack(fill="x", pady=4)
        ttk.Label(edit_frame, text="Insumo:").grid(row=0, column=0, sticky="w", padx=2, pady=2)
        self.insumo_combo = ttk.Combobox(edit_frame, textvariable=self.insumo_sel_var, state="readonly")
        self.insumo_combo.grid(row=0, column=1, sticky="ew", padx=2, pady=2)
        edit_frame.columnconfigure(1, weight=1)

        ttk.Label(edit_frame, text="Cantidad usada").grid(row=0, column=2, sticky="w", padx=6, pady=2)
        ttk.Entry(edit_frame, textvariable=self.cant_sel_var, width=12).grid(row=0, column=3, sticky="w", padx=2, pady=2)

        ttk.Label(edit_frame, text="Override costo uso").grid(row=0, column=4, sticky="w", padx=6, pady=2)
        ttk.Entry(edit_frame, textvariable=self.override_sel_var, width=12).grid(row=0, column=5, sticky="w", padx=2, pady=2)

        ttk.Button(edit_frame, text="Agregar/Actualizar", command=self.add_or_update_ing).grid(row=0, column=6, padx=6)
        ttk.Button(edit_frame, text="Eliminar", command=self.remove_selected_ing).grid(row=0, column=7, padx=2)

        ing_columns = ("insumo", "cantidad", "costo_unit", "costo_total")
        self.ing_tree = ttk.Treeview(ing_frame, columns=ing_columns, show="headings", height=10)
        self.ing_tree.heading("insumo", text="Insumo")
        self.ing_tree.heading("cantidad", text="Cantidad usada")
        self.ing_tree.heading("costo_unit", text="Costo unidad")
        self.ing_tree.heading("costo_total", text="Costo total")
        self.ing_tree.column("insumo", width=200)
        self.ing_tree.column("cantidad", width=120, anchor="e")
        self.ing_tree.column("costo_unit", width=120, anchor="e")
        self.ing_tree.column("costo_total", width=120, anchor="e")
        ing_scroll = ttk.Scrollbar(ing_frame, orient="vertical", command=self.ing_tree.yview)
        self.ing_tree.configure(yscrollcommand=ing_scroll.set)
        self.ing_tree.pack(side="left", fill="both", expand=True)
        ing_scroll.pack(side="left", fill="y")

        # Costos adicionales
        energia = ttk.LabelFrame(parent, text="Costos de energía (por tanda)")
        energia.pack(fill="x", pady=4)
        self._create_labeled_entry(energia, "kWh", self.product_vars["kwh"], 0, 0)
        self._create_labeled_entry(energia, "Tarifa kWh", self.product_vars["tarifa_kwh"], 0, 1)
        self._create_labeled_entry(energia, "m³ gas", self.product_vars["m3_gas"], 0, 2)
        self._create_labeled_entry(energia, "Tarifa m³ gas", self.product_vars["tarifa_m3_gas"], 0, 3)

        mano_obra = ttk.LabelFrame(parent, text="Mano de obra (por tanda)")
        mano_obra.pack(fill="x", pady=4)
        self._create_labeled_entry(mano_obra, "Horas", self.product_vars["horas"], 0, 0)
        self._create_labeled_entry(mano_obra, "Tarifa hora", self.product_vars["tarifa_hora"], 0, 1)
        self._create_labeled_entry(mano_obra, "Cargas sociales %", self.product_vars["cargas_sociales_pct"], 0, 2)

        generales = ttk.LabelFrame(parent, text="Costos generales")
        generales.pack(fill="x", pady=4)
        self._create_labeled_entry(generales, "Empaque unitario", self.product_vars["empaque_unitario"], 0, 0)
        self._create_labeled_entry(generales, "Otros por tanda", self.product_vars["otros_por_tanda"], 0, 1)

        impuestos = ttk.LabelFrame(parent, text="Impuestos y margen")
        impuestos.pack(fill="x", pady=4)
        self._create_labeled_entry(impuestos, "Merma %", self.product_vars["merma_pct"], 0, 0)
        self._create_labeled_entry(impuestos, "Margen %", self.product_vars["margen_pct"], 0, 1)
        self._create_labeled_entry(impuestos, "IVA %", self.product_vars["iva_pct"], 0, 2)
        self._create_labeled_entry(impuestos, "Otros impuestos %", self.product_vars["otros_impuestos_pct"], 0, 3)
        self._create_labeled_entry(impuestos, "Redondeo", self.product_vars["redondeo"], 0, 4)

        resultados = ttk.LabelFrame(parent, text="Resultados")
        resultados.pack(fill="x", pady=6)

        self._create_result_row(resultados, "Costo ingredientes (tanda)", self.costo_ing_var, 0)
        self._create_result_row(resultados, "Costo energía (tanda)", self.costo_ener_var, 1)
        self._create_result_row(resultados, "Costo mano de obra (tanda)", self.costo_mo_var, 2)
        self._create_result_row(resultados, "Total de la tanda", self.costo_tanda_var, 3)
        self._create_result_row(resultados, "Unidades útiles", self.unidades_utiles_var, 4)
        self._create_result_row(resultados, "Costo base por unidad", self.costo_u_var, 5)
        self._create_result_row(resultados, "Precio sin impuestos", self.precio_u_sin_var, 6)
        self._create_result_row(resultados, "Precio con IVA", self.precio_u_iva_var, 7)
        self._create_result_row(resultados, "Precio final sugerido", self.precio_u_final_var, 8)

    def _build_catalog_panel(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Catálogo de Insumos", font=("TkDefaultFont", 12, "bold")).pack(anchor="w")

        search_frame = ttk.Frame(parent)
        search_frame.pack(fill="x", pady=(6, 4))
        ttk.Label(search_frame, text="Buscar:").pack(side="left")
        entry = ttk.Entry(search_frame, textvariable=self.catalog_search_var)
        entry.pack(side="left", fill="x", expand=True, padx=(4, 0))

        columns = ("nombre", "unidad", "costo_compra", "factor", "costo_uso")
        self.catalog_tree = ttk.Treeview(parent, columns=columns, show="headings", height=16)
        self.catalog_tree.heading("nombre", text="Nombre")
        self.catalog_tree.heading("unidad", text="Unidad compra")
        self.catalog_tree.heading("costo_compra", text="Costo unidad compra")
        self.catalog_tree.heading("factor", text="Factor uso")
        self.catalog_tree.heading("costo_uso", text="Costo unidad uso")
        self.catalog_tree.column("nombre", width=160)
        self.catalog_tree.column("unidad", width=100)
        self.catalog_tree.column("costo_compra", width=120, anchor="e")
        self.catalog_tree.column("factor", width=100, anchor="e")
        self.catalog_tree.column("costo_uso", width=120, anchor="e")
        scroll = ttk.Scrollbar(parent, orient="vertical", command=self.catalog_tree.yview)
        self.catalog_tree.configure(yscrollcommand=scroll.set)
        self.catalog_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="left", fill="y")

        form = ttk.LabelFrame(parent, text="Detalle de insumo")
        form.pack(fill="x", pady=8)
        self._create_labeled_entry(form, "Nombre", self.insumo_vars["nombre"], 0, 0, columnspan=2)
        self._create_labeled_entry(form, "Unidad de compra", self.insumo_vars["unidad_compra"], 1, 0, columnspan=2)
        self._create_labeled_entry(form, "Costo por unidad de compra", self.insumo_vars["costo_por_unidad_compra"], 2, 0, columnspan=2)
        self._create_labeled_entry(form, "Factor de uso", self.insumo_vars["factor_uso"], 3, 0, columnspan=2)

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill="x", pady=6)
        ttk.Button(btn_frame, text="Nuevo", command=self.new_insumo).pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="Guardar/Actualizar", command=self.save_insumo).pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="Eliminar", command=self.delete_insumo).pack(fill="x", pady=2)

    def _create_labeled_entry(self, parent: ttk.Widget, label: str, variable: tk.StringVar, row: int, column: int, columnspan: int = 1) -> None:
        lbl = ttk.Label(parent, text=label)
        lbl.grid(row=row, column=column * 2, sticky="w", padx=4, pady=4)
        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row, column=column * 2 + 1, sticky="ew", padx=4, pady=4, columnspan=columnspan)
        parent.grid_columnconfigure(column * 2 + 1, weight=1)

    def _create_result_row(self, parent: ttk.Frame, label: str, variable: tk.StringVar, row: int) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=6, pady=2)
        ttk.Label(parent, textvariable=variable, font=("TkDefaultFont", 10, "bold"), foreground="#333333").grid(row=row, column=1, sticky="e", padx=6, pady=2)
        parent.grid_columnconfigure(1, weight=1)

    # -------------------------
    # Wire events
    # -------------------------

    def _wire_traces(self) -> None:
        self.product_tree.bind("<<TreeviewSelect>>", self._on_product_selected)
        self.catalog_tree.bind("<<TreeviewSelect>>", self._on_insumo_selected)
        self.ing_tree.bind("<<TreeviewSelect>>", self._on_ingredient_selected)

        self.product_search_var.trace_add("write", lambda *_: self._refresh_product_list())
        self.catalog_search_var.trace_add("write", lambda *_: self._refresh_catalog())
        self.product_name_var.trace_add("write", lambda *_: self._on_product_field_change())
        for var in self.product_vars.values():
            var.trace_add("write", lambda *_: self._on_product_field_change())

    # -------------------------
    # Refrescos
    # -------------------------

    def _refresh_all(self) -> None:
        self._refresh_catalog()
        self._refresh_product_list()
        self._refresh_product_detail()

    def _refresh_product_list(self) -> None:
        if self._updating_ui:
            return
        self._sync_product_from_ui()
        search = self.product_search_var.get().strip().lower()
        selected = str(self.current_index) if self.current_index is not None else None

        for item in self.product_tree.get_children():
            self.product_tree.delete(item)

        for idx, producto in enumerate(self.data.productos):
            if search and search not in producto.nombre.lower():
                continue
            costo = producto.costo_por_unidad_base(self.data.catalogo) if self.data.catalogo or producto.ingredientes else producto.costo_por_unidad_base(self.data.catalogo)
            precio = producto.precio_final(self.data.catalogo)
            self.product_tree.insert("", "end", iid=str(idx), values=(producto.nombre, format_currency(costo), format_currency(precio)))

        if selected and self.product_tree.exists(selected):
            self.product_tree.selection_set(selected)
            self.product_tree.focus(selected)
        elif self.product_tree.get_children():
            first = self.product_tree.get_children()[0]
            self.product_tree.selection_set(first)
            self.product_tree.focus(first)
            self.current_index = int(first)
        else:
            self.current_index = None
        self._refresh_product_detail()

    def _refresh_product_detail(self) -> None:
        self._updating_ui = True
        try:
            for item in self.ing_tree.get_children():
                self.ing_tree.delete(item)
            if self.current_index is None or self.current_index >= len(self.data.productos):
                self.product_name_var.set("")
                for var in self.product_vars.values():
                    var.set("0")
                self.quick_cost_var.set("Costo por unidad: $ 0,00")
                self.quick_price_var.set("Precio final: $ 0,00")
                self.costo_ing_var.set("$ 0,00")
                self.costo_ener_var.set("$ 0,00")
                self.costo_mo_var.set("$ 0,00")
                self.costo_tanda_var.set("$ 0,00")
                self.unidades_utiles_var.set("0,00")
                self.costo_u_var.set("$ 0,00")
                self.precio_u_sin_var.set("$ 0,00")
                self.precio_u_iva_var.set("$ 0,00")
                self.precio_u_final_var.set("$ 0,00")
                return

            producto = self.data.productos[self.current_index]
            self.product_name_var.set(producto.nombre)
            for field, var in self.product_vars.items():
                value = getattr(producto, field)
                if isinstance(value, float):
                    var.set(format_number(value))
                else:
                    var.set(str(value))

            for ingrediente in producto.ingredientes:
                insumo = self._find_insumo(ingrediente.insumo_nombre)
                cantidad = format_number(ingrediente.cantidad_uso)
                if insumo:
                    costo_unit = ingrediente.override_costo_uso if ingrediente.override_costo_uso is not None and ingrediente.override_costo_uso >= 0 else insumo.costo_por_unidad_uso()
                    costo_total = ingrediente.costo_total(insumo)
                    self.ing_tree.insert("", "end", iid=ingrediente.insumo_nombre, values=(ingrediente.insumo_nombre, cantidad, format_currency(costo_unit), format_currency(costo_total)))
                else:
                    self.ing_tree.insert("", "end", iid=ingrediente.insumo_nombre, values=(ingrediente.insumo_nombre + " (faltante)", cantidad, "-", "-"))

            self._update_results()
        finally:
            self._updating_ui = False

    def _refresh_catalog(self) -> None:
        search = self.catalog_search_var.get().strip().lower()
        for item in self.catalog_tree.get_children():
            self.catalog_tree.delete(item)
        for insumo in self.data.catalogo:
            if search and search not in insumo.nombre.lower():
                continue
            self.catalog_tree.insert(
                "",
                "end",
                iid=insumo.nombre,
                values=(
                    insumo.nombre,
                    insumo.unidad_compra,
                    format_currency(insumo.costo_por_unidad_compra),
                    format_number(insumo.factor_uso),
                    format_currency(insumo.costo_por_unidad_uso()),
                ),
            )
        self.insumo_combo["values"] = [insumo.nombre for insumo in self.data.catalogo]
        if self.current_insumo and self.catalog_tree.exists(self.current_insumo):
            self.catalog_tree.selection_set(self.current_insumo)
            self.catalog_tree.focus(self.current_insumo)

    # -------------------------
    # Manejo de selección
    # -------------------------

    def _on_product_selected(self, event: tk.Event) -> None:
        if not self.product_tree.selection():
            return
        iid = self.product_tree.selection()[0]
        try:
            index = int(iid)
        except ValueError:
            return
        if index < 0 or index >= len(self.data.productos):
            return
        self._sync_product_from_ui()
        self.current_index = index
        self._refresh_product_detail()

    def _on_insumo_selected(self, event: tk.Event) -> None:
        sel = self.catalog_tree.selection()
        if not sel:
            return
        nombre = sel[0]
        insumo = self._find_insumo(nombre)
        if not insumo:
            return
        self.current_insumo = nombre
        self.insumo_vars["nombre"].set(insumo.nombre)
        self.insumo_vars["unidad_compra"].set(insumo.unidad_compra)
        self.insumo_vars["costo_por_unidad_compra"].set(format_number(insumo.costo_por_unidad_compra))
        self.insumo_vars["factor_uso"].set(format_number(insumo.factor_uso))

    def _on_ingredient_selected(self, event: tk.Event) -> None:
        sel = self.ing_tree.selection()
        if not sel:
            return
        insumo_name = self.ing_tree.item(sel[0], "values")[0]
        clean_name = insumo_name.replace(" (faltante)", "")
        self.insumo_sel_var.set(clean_name)
        if self.current_index is None:
            return
        producto = self.data.productos[self.current_index]
        for ingrediente in producto.ingredientes:
            if ingrediente.insumo_nombre == clean_name:
                self.cant_sel_var.set(format_number(ingrediente.cantidad_uso))
                if ingrediente.override_costo_uso is not None:
                    self.override_sel_var.set(format_number(ingrediente.override_costo_uso))
                else:
                    self.override_sel_var.set("")
                break

    # -------------------------
    # CRUD Productos
    # -------------------------

    def new_product(self) -> None:
        self._sync_product_from_ui()
        self.data.productos.append(Producto())
        self.current_index = len(self.data.productos) - 1
        self._refresh_product_list()

    def duplicate_product(self) -> None:
        if self.current_index is None or self.current_index >= len(self.data.productos):
            messagebox.showerror("Productos", "Seleccioná un producto para duplicar.")
            return
        self._sync_product_from_ui()
        nuevo = copy.deepcopy(self.data.productos[self.current_index])
        nuevo.nombre = f"{nuevo.nombre} (copia)"
        self.data.productos.append(nuevo)
        self.current_index = len(self.data.productos) - 1
        self._refresh_product_list()

    def delete_product(self) -> None:
        if self.current_index is None or self.current_index >= len(self.data.productos):
            messagebox.showerror("Productos", "Seleccioná un producto para eliminar.")
            return
        producto = self.data.productos[self.current_index]
        if not messagebox.askyesno("Eliminar producto", f"¿Eliminar '{producto.nombre}'?"):
            return
        del self.data.productos[self.current_index]
        if self.data.productos:
            self.current_index = max(0, self.current_index - 1)
        else:
            self.current_index = None
        self._refresh_product_list()

    # -------------------------
    # CRUD Insumos
    # -------------------------

    def new_insumo(self) -> None:
        for var in self.insumo_vars.values():
            var.set("")
        self.insumo_vars["factor_uso"].set("1")
        self.current_insumo = None
        self.catalog_tree.selection_remove(self.catalog_tree.selection())

    def save_insumo(self) -> None:
        nombre = self.insumo_vars["nombre"].get().strip()
        if not nombre:
            messagebox.showerror("Insumos", "Ingresá un nombre de insumo.")
            return
        unidad = self.insumo_vars["unidad_compra"].get().strip()
        if not unidad:
            messagebox.showerror("Insumos", "Ingresá la unidad de compra.")
            return
        try:
            costo = parse_float(self.insumo_vars["costo_por_unidad_compra"].get())
            factor = parse_float(self.insumo_vars["factor_uso"].get(), default=1.0)
        except ValueError:
            messagebox.showerror("Insumos", "Ingresá números válidos para costo y factor.")
            return
        if factor <= 0:
            messagebox.showerror("Insumos", "El factor de uso debe ser mayor que cero.")
            return

        existente = self._find_insumo(nombre)
        if self.current_insumo and self.current_insumo != nombre and existente:
            messagebox.showerror("Insumos", "Ya existe un insumo con ese nombre.")
            return

        if self.current_insumo and self.current_insumo == nombre and existente:
            existente.unidad_compra = unidad
            existente.costo_por_unidad_compra = costo
            existente.factor_uso = factor
        elif self.current_insumo and self.current_insumo != nombre:
            viejo = self._find_insumo(self.current_insumo)
            if viejo:
                viejo.nombre = nombre
                viejo.unidad_compra = unidad
                viejo.costo_por_unidad_compra = costo
                viejo.factor_uso = factor
                for producto in self.data.productos:
                    for ingrediente in producto.ingredientes:
                        if ingrediente.insumo_nombre == self.current_insumo:
                            ingrediente.insumo_nombre = nombre
        elif existente:
            existente.unidad_compra = unidad
            existente.costo_por_unidad_compra = costo
            existente.factor_uso = factor
        else:
            self.data.catalogo.append(Insumo(nombre=nombre, unidad_compra=unidad, costo_por_unidad_compra=costo, factor_uso=factor))

        self.current_insumo = nombre
        self._refresh_catalog()
        self._refresh_product_detail()
        self._refresh_product_list()

    def delete_insumo(self) -> None:
        if not self.catalog_tree.selection():
            messagebox.showerror("Insumos", "Seleccioná un insumo para eliminar.")
            return
        nombre = self.catalog_tree.selection()[0]
        insumo = self._find_insumo(nombre)
        if not insumo:
            return
        if not messagebox.askyesno("Eliminar insumo", f"¿Eliminar '{nombre}' del catálogo?"):
            return
        self.data.catalogo = [i for i in self.data.catalogo if i.nombre != nombre]
        removed = 0
        for producto in self.data.productos:
            originales = len(producto.ingredientes)
            producto.ingredientes = [ing for ing in producto.ingredientes if ing.insumo_nombre != nombre]
            removed += originales - len(producto.ingredientes)
        if removed:
            messagebox.showinfo("Insumos", f"Se eliminaron {removed} ingredientes que usaban '{nombre}'.")
        self.current_insumo = None
        self._refresh_catalog()
        self._refresh_product_detail()
        self._refresh_product_list()

    # -------------------------
    # Ingredientes
    # -------------------------

    def add_or_update_ing(self) -> None:
        if self.current_index is None or self.current_index >= len(self.data.productos):
            messagebox.showerror("Ingredientes", "Primero seleccioná un producto.")
            return
        nombre = self.insumo_sel_var.get().strip()
        if not nombre:
            messagebox.showerror("Ingredientes", "Seleccioná un insumo del catálogo.")
            return
        insumo = self._find_insumo(nombre)
        if not insumo:
            messagebox.showerror("Ingredientes", "El insumo seleccionado no existe.")
            return
        try:
            cantidad = parse_float(self.cant_sel_var.get())
        except ValueError:
            messagebox.showerror("Ingredientes", "Ingresá una cantidad válida.")
            return
        override_valor = self.override_sel_var.get().strip()
        override = None
        if override_valor:
            try:
                override = parse_float(override_valor)
            except ValueError:
                messagebox.showerror("Ingredientes", "Ingresá un valor numérico válido para el override.")
                return
            if override < 0:
                messagebox.showerror("Ingredientes", "El override debe ser mayor o igual a cero.")
                return

        producto = self.data.productos[self.current_index]
        for ingrediente in producto.ingredientes:
            if ingrediente.insumo_nombre == nombre:
                ingrediente.cantidad_uso = cantidad
                ingrediente.override_costo_uso = override
                break
        else:
            producto.ingredientes.append(IngredienteDeProducto(insumo_nombre=nombre, cantidad_uso=cantidad, override_costo_uso=override))
        self.cant_sel_var.set("")
        self.override_sel_var.set("")
        self._refresh_product_detail()
        self._refresh_product_list()

    def remove_selected_ing(self) -> None:
        if self.current_index is None or self.current_index >= len(self.data.productos):
            return
        selection = self.ing_tree.selection()
        if not selection:
            messagebox.showerror("Ingredientes", "Seleccioná un ingrediente para eliminar.")
            return
        insumo_nombre = self.ing_tree.item(selection[0], "values")[0].replace(" (faltante)", "")
        producto = self.data.productos[self.current_index]
        producto.ingredientes = [ing for ing in producto.ingredientes if ing.insumo_nombre != insumo_nombre]
        self._refresh_product_detail()
        self._refresh_product_list()

    # -------------------------
    # Persistencia
    # -------------------------

    def save_library(self) -> None:
        self._sync_product_from_ui()
        data = {
            "catalogo": [asdict(insumo) for insumo in self.data.catalogo],
            "productos": [self._producto_to_dict(prod) for prod in self.data.productos],
        }
        path = filedialog.asksaveasfilename(title="Guardar biblioteca", defaultextension=".json", filetypes=[("JSON", "*.json")], initialfile="biblioteca_costos.json")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
            messagebox.showinfo("Biblioteca", "Biblioteca guardada correctamente.")
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo guardar la biblioteca: {exc}")

    def open_library(self) -> None:
        path = filedialog.askopenfilename(title="Abrir biblioteca", filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            catalogo = [Insumo(**ins) for ins in data.get("catalogo", [])]
            productos = []
            for prod in data.get("productos", []):
                prod_copy = prod.copy()
                ingredientes = [IngredienteDeProducto(**ing) for ing in prod_copy.pop("ingredientes", [])]
                producto = Producto(**prod_copy)
                producto.ingredientes = ingredientes
                productos.append(producto)
            self.data.catalogo = catalogo
            self.data.productos = productos
            self.current_index = 0 if self.data.productos else None
            self.current_insumo = None
            self.new_insumo()
            self._refresh_all()
            messagebox.showinfo("Biblioteca", "Biblioteca cargada correctamente.")
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo abrir la biblioteca: {exc}")

    def _producto_to_dict(self, producto: Producto) -> dict:
        data = asdict(producto)
        data["ingredientes"] = [asdict(ing) for ing in producto.ingredientes]
        return data

    # -------------------------
    # Helpers
    # -------------------------

    def _find_insumo(self, nombre: str) -> Optional[Insumo]:
        for insumo in self.data.catalogo:
            if insumo.nombre == nombre:
                return insumo
        return None

    def _sync_product_from_ui(self) -> None:
        if self.current_index is None or self.current_index >= len(self.data.productos):
            return
        producto = self.data.productos[self.current_index]
        if not self._updating_ui:
            producto.nombre = self.product_name_var.get().strip() or "Producto sin nombre"
        try:
            producto.unidades_por_tanda = parse_int(self.product_vars["unidades_por_tanda"].get(), default=1)
        except ValueError:
            producto.unidades_por_tanda = 1
        for field in [
            "kwh",
            "tarifa_kwh",
            "m3_gas",
            "tarifa_m3_gas",
            "horas",
            "tarifa_hora",
            "cargas_sociales_pct",
            "empaque_unitario",
            "otros_por_tanda",
            "merma_pct",
            "margen_pct",
            "iva_pct",
            "otros_impuestos_pct",
            "redondeo",
        ]:
            try:
                setattr(producto, field, parse_float(self.product_vars[field].get()))
            except ValueError:
                setattr(producto, field, getattr(producto, field))

    def _on_product_field_change(self) -> None:
        if self._updating_ui:
            return
        self._sync_product_from_ui()
        self._refresh_product_list()
        self._update_results()

    def _update_results(self) -> None:
        if self.current_index is None or self.current_index >= len(self.data.productos):
            return
        producto = self.data.productos[self.current_index]
        costo_ing = producto.costo_ingredientes(self.data.catalogo)
        costo_ener = producto.costo_energia()
        costo_mo = producto.costo_mano_obra()
        costo_tanda = producto.costo_tanda(self.data.catalogo)
        unidades_utiles = producto.unidades_utiles()
        costo_u = producto.costo_por_unidad_base(self.data.catalogo)
        precio_sin = producto.precio_sin_impuestos(self.data.catalogo)
        precio_iva = producto.precio_con_iva(self.data.catalogo)
        precio_final = producto.precio_final(self.data.catalogo)

        self.costo_ing_var.set(format_currency(costo_ing))
        self.costo_ener_var.set(format_currency(costo_ener))
        self.costo_mo_var.set(format_currency(costo_mo))
        self.costo_tanda_var.set(format_currency(costo_tanda))
        self.unidades_utiles_var.set(format_number(unidades_utiles))
        self.costo_u_var.set(format_currency(costo_u))
        self.precio_u_sin_var.set(format_currency(precio_sin))
        self.precio_u_iva_var.set(format_currency(precio_iva))
        self.precio_u_final_var.set(format_currency(precio_final))
        self.quick_cost_var.set(f"Costo por unidad: {format_currency(costo_u)}")
        self.quick_price_var.set(f"Precio final: {format_currency(precio_final)}")

    # -------------------------
    # Mainloop
    # -------------------------


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
