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
    precio_final_manual: float = 0.0

    def costo_ingredientes(self, catalogo: List[Insumo]) -> float:
        lookup = {insumo.nombre: insumo for insumo in catalogo}
        total = 0.0
        for ingrediente in self.ingredientes:
            insumo = lookup.get(ingrediente.insumo_nombre)
            if insumo:
                total += ingrediente.costo_total(insumo)
        return total

    def costo_tanda(self, catalogo: List[Insumo]) -> float:
        return self.costo_ingredientes(catalogo)

    def unidades_por_tanda_validas(self) -> float:
        return max(self.unidades_por_tanda, 1e-9)

    def costo_por_unidad(self, catalogo: List[Insumo]) -> float:
        return self.costo_tanda(catalogo) / self.unidades_por_tanda_validas()

    def precio_final(self, catalogo: List[Insumo]) -> float:
        calculado = self.precio_final_manual
        if calculado <= 0:
            return self.costo_por_unidad(catalogo)
        return calculado


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
        self.geometry("1440x860")
        self.minsize(1280, 760)
        self.configure(background="#f3f4f8")

        self.style = ttk.Style(self)
        self._setup_style()

        self.data = Biblioteca()
        self.current_index: Optional[int] = None
        self.current_insumo: Optional[str] = None
        self._updating_ui = False

        self.product_search_var = tk.StringVar()
        self.catalog_search_var = tk.StringVar()

        self.product_name_var = tk.StringVar()
        self.quick_cost_var = tk.StringVar(value="$ 0,00")
        self.quick_price_var = tk.StringVar(value="$ 0,00")

        # Campos del producto
        self.product_vars = {
            "unidades_por_tanda": tk.StringVar(value="1"),
            "precio_final_manual": tk.StringVar(value="0"),
        }

        # Resultados calculados
        self.costo_ing_var = tk.StringVar(value="$ 0,00")
        self.costo_tanda_var = tk.StringVar(value="$ 0,00")
        self.unidades_tanda_var = tk.StringVar(value="0")
        self.costo_u_var = tk.StringVar(value="$ 0,00")
        self.precio_u_final_var = tk.StringVar(value="$ 0,00")
        self.margen_unitario_var = tk.StringVar(value="$ 0,00")
        self.margen_pct_var = tk.StringVar(value="0,00 %")

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

    def _setup_style(self) -> None:
        base_bg = "#f3f4f8"
        card_bg = "#ffffff"
        accent = "#0d47a1"
        success = "#1b5e20"

        self.style.theme_use("clam")
        self.style.configure("TFrame", background=base_bg)
        self.style.configure("TLabel", background=base_bg)
        self.style.configure("TNotebook", background=base_bg)
        self.style.configure("Header.TFrame", background=accent)
        self.style.configure("HeaderTitle.TLabel", background=accent, foreground="#ffffff", font=("Helvetica", 18, "bold"))
        self.style.configure("HeaderSubtitle.TLabel", background=accent, foreground="#d9e6ff", font=("Helvetica", 11))

        self.style.configure("Card.TFrame", background=card_bg, relief="flat", borderwidth=0)
        self.style.configure("CardTitle.TLabel", background=card_bg, foreground=accent, font=("Helvetica", 14, "bold"))
        self.style.configure("SectionLabel.TLabel", background=card_bg, foreground="#4d5666", font=("Helvetica", 11, "bold"))
        self.style.configure("SummaryCard.TFrame", background=card_bg, relief="ridge", borderwidth=1)
        self.style.configure("SummaryValue.TLabel", background=card_bg, foreground=accent, font=("Helvetica", 16, "bold"))
        self.style.configure("SummaryValueGreen.TLabel", background=card_bg, foreground=success, font=("Helvetica", 16, "bold"))
        self.style.configure("ValueLabel.TLabel", background=card_bg, foreground="#1a2333", font=("Helvetica", 11, "bold"))
        self.style.configure("Caption.TLabel", background=card_bg, foreground="#6b7280", font=("Helvetica", 10))
        self.style.configure("FormLabel.TLabel", background=card_bg, foreground="#2f3b52", font=("Helvetica", 10, "bold"))

        self.style.configure("Accent.TButton", font=("Helvetica", 10, "bold"), padding=8, relief="flat", background=accent, foreground="#ffffff")
        self.style.map("Accent.TButton", background=[("active", "#1359c5"), ("disabled", "#8ca9d6")], foreground=[("disabled", "#f0f4ff")])
        self.style.configure("Secondary.TButton", font=("Helvetica", 10), padding=8, relief="flat", background="#e4e9f4", foreground="#1a2333")
        self.style.map("Secondary.TButton", background=[("active", "#d2daec")])

        self.style.configure("Treeview", background=card_bg, foreground="#1f2937", fieldbackground=card_bg, bordercolor="#d9dde5", rowheight=28)
        self.style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"), background="#eef2fb", foreground="#0d47a1")
        self.style.map("Treeview", background=[("selected", "#dbe6ff")], foreground=[("selected", "#0d47a1")])
        self.style.map("Treeview.Heading", background=[("active", "#dbe6ff")])

        self.style.configure("Card.TLabelframe", background=card_bg)
        self.style.configure("Card.TLabelframe.Label", background=card_bg, foreground=accent, font=("Helvetica", 12, "bold"))

        self.option_add("*TCombobox*Listbox.font", ("Helvetica", 10))

    def _build_ui(self) -> None:
        header = ttk.Frame(self, style="Header.TFrame", padding=(24, 18))
        header.pack(fill="x")
        ttk.Label(header, text="Costos de Productos", style="HeaderTitle.TLabel").pack(side="left")
        ttk.Label(header, text="Gestioná ingredientes y precios finales en un solo lugar", style="HeaderSubtitle.TLabel").pack(side="left", padx=(12, 0))

        content = ttk.Frame(self, padding=20)
        content.pack(fill="both", expand=True)

        paned = ttk.PanedWindow(content, orient="horizontal")
        paned.pack(fill="both", expand=True)

        left_frame = ttk.Frame(paned, style="Card.TFrame", padding=16)
        center_frame = ttk.Frame(paned, style="Card.TFrame", padding=16)
        right_frame = ttk.Frame(paned, style="Card.TFrame", padding=16)

        paned.add(left_frame, weight=1)
        paned.add(center_frame, weight=2)
        paned.add(right_frame, weight=1)

        self._build_products_panel(left_frame)
        self._build_product_detail_panel(center_frame)
        self._build_catalog_panel(right_frame)

    def _build_products_panel(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="📦 Productos", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 12))

        search_frame = ttk.Frame(parent, style="Card.TFrame")
        search_frame.pack(fill="x", pady=(0, 12))
        ttk.Label(search_frame, text="Buscar", style="Caption.TLabel").pack(side="left", padx=(0, 6))
        entry = ttk.Entry(search_frame, textvariable=self.product_search_var)
        entry.pack(side="left", fill="x", expand=True)

        table_container = ttk.Frame(parent, style="Card.TFrame")
        table_container.pack(fill="both", expand=True)

        columns = ("nombre", "costo", "precio")
        self.product_tree = ttk.Treeview(table_container, columns=columns, show="headings", height=18)
        self.product_tree.heading("nombre", text="Nombre")
        self.product_tree.heading("costo", text="Costo / unidad")
        self.product_tree.heading("precio", text="Precio final")
        self.product_tree.column("nombre", width=240)
        self.product_tree.column("costo", width=140, anchor="e")
        self.product_tree.column("precio", width=140, anchor="e")
        scroll = ttk.Scrollbar(table_container, orient="vertical", command=self.product_tree.yview)
        self.product_tree.configure(yscrollcommand=scroll.set)
        self.product_tree.pack(fill="both", expand=True, side="left")
        scroll.pack(fill="y", side="right")

        self.product_tree.tag_configure("odd", background="#f7f9ff")

        btn_frame = ttk.Frame(parent, style="Card.TFrame")
        btn_frame.pack(fill="x", pady=(16, 0))
        ttk.Button(btn_frame, text="Nuevo producto", style="Accent.TButton", command=self.new_product).pack(fill="x", pady=4)
        ttk.Button(btn_frame, text="Duplicar seleccionado", style="Secondary.TButton", command=self.duplicate_product).pack(fill="x", pady=4)
        ttk.Button(btn_frame, text="Eliminar", style="Secondary.TButton", command=self.delete_product).pack(fill="x", pady=4)

        ttk.Separator(btn_frame, orient="horizontal").pack(fill="x", pady=12)
        ttk.Button(btn_frame, text="Guardar biblioteca…", style="Secondary.TButton", command=self.save_library).pack(fill="x", pady=4)
        ttk.Button(btn_frame, text="Abrir biblioteca…", style="Secondary.TButton", command=self.open_library).pack(fill="x", pady=4)

    def _build_product_detail_panel(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="🧾 Detalle del producto", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 12))

        summary = ttk.Frame(parent, style="Card.TFrame")
        summary.pack(fill="x", pady=(0, 16))

        cost_card = ttk.Frame(summary, style="SummaryCard.TFrame", padding=14)
        cost_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        ttk.Label(cost_card, text="Costo por unidad", style="Caption.TLabel").pack(anchor="w")
        ttk.Label(cost_card, textvariable=self.quick_cost_var, style="SummaryValue.TLabel").pack(anchor="w", pady=(6, 0))

        price_card = ttk.Frame(summary, style="SummaryCard.TFrame", padding=14)
        price_card.grid(row=0, column=1, sticky="nsew", padx=(0, 12))
        ttk.Label(price_card, text="Precio final", style="Caption.TLabel").pack(anchor="w")
        ttk.Label(price_card, textvariable=self.quick_price_var, style="SummaryValueGreen.TLabel").pack(anchor="w", pady=(6, 0))

        margin_card = ttk.Frame(summary, style="SummaryCard.TFrame", padding=14)
        margin_card.grid(row=0, column=2, sticky="nsew")
        ttk.Label(margin_card, text="Margen unitario", style="Caption.TLabel").pack(anchor="w")
        ttk.Label(margin_card, textvariable=self.margen_unitario_var, style="SummaryValue.TLabel").pack(anchor="w", pady=(6, 0))
        ttk.Label(margin_card, textvariable=self.margen_pct_var, style="Caption.TLabel").pack(anchor="w", pady=(4, 0))

        summary.columnconfigure(0, weight=1)
        summary.columnconfigure(1, weight=1)
        summary.columnconfigure(2, weight=1)

        general = ttk.Frame(parent, style="Card.TFrame")
        general.pack(fill="x", pady=(0, 12))
        ttk.Label(general, text="Datos generales", style="SectionLabel.TLabel").grid(row=0, column=0, columnspan=8, sticky="w", pady=(0, 8))
        self._create_labeled_entry(general, "Nombre", self.product_name_var, 1, 0, columnspan=3)
        self._create_labeled_entry(general, "Unidades por tanda", self.product_vars["unidades_por_tanda"], 1, 3)
        self._create_labeled_entry(general, "Precio final manual", self.product_vars["precio_final_manual"], 2, 0, columnspan=1)
        ttk.Label(general, text="Si dejás 0 se usará automáticamente el costo por unidad.", style="Caption.TLabel").grid(row=3, column=0, columnspan=8, sticky="w", pady=(4, 0))

        ing_frame = ttk.Labelframe(parent, text="Ingredientes del producto", style="Card.TLabelframe", padding=12)
        ing_frame.pack(fill="both", expand=True, pady=(0, 12))

        edit_frame = ttk.Frame(ing_frame, style="Card.TFrame")
        edit_frame.pack(fill="x", pady=(0, 12))
        ttk.Label(edit_frame, text="Insumo", style="Caption.TLabel").grid(row=0, column=0, sticky="w", padx=2, pady=2)
        self.insumo_combo = ttk.Combobox(edit_frame, textvariable=self.insumo_sel_var, state="readonly")
        self.insumo_combo.grid(row=0, column=1, sticky="ew", padx=2, pady=2)
        edit_frame.columnconfigure(1, weight=1)

        ttk.Label(edit_frame, text="Cantidad usada", style="Caption.TLabel").grid(row=0, column=2, sticky="w", padx=6, pady=2)
        ttk.Entry(edit_frame, textvariable=self.cant_sel_var, width=12).grid(row=0, column=3, sticky="w", padx=2, pady=2)

        ttk.Label(edit_frame, text="Costo unitario personalizado", style="Caption.TLabel").grid(row=0, column=4, sticky="w", padx=6, pady=2)
        ttk.Entry(edit_frame, textvariable=self.override_sel_var, width=12).grid(row=0, column=5, sticky="w", padx=2, pady=2)

        ttk.Button(edit_frame, text="Agregar o actualizar", style="Accent.TButton", command=self.add_or_update_ing).grid(row=0, column=6, padx=8)
        ttk.Button(edit_frame, text="Eliminar", style="Secondary.TButton", command=self.remove_selected_ing).grid(row=0, column=7, padx=4)

        ing_columns = ("insumo", "cantidad", "costo_unit", "costo_total")
        self.ing_tree = ttk.Treeview(ing_frame, columns=ing_columns, show="headings", height=12)
        self.ing_tree.heading("insumo", text="Insumo")
        self.ing_tree.heading("cantidad", text="Cantidad usada")
        self.ing_tree.heading("costo_unit", text="Costo unidad")
        self.ing_tree.heading("costo_total", text="Costo total")
        self.ing_tree.column("insumo", width=220)
        self.ing_tree.column("cantidad", width=130, anchor="e")
        self.ing_tree.column("costo_unit", width=130, anchor="e")
        self.ing_tree.column("costo_total", width=130, anchor="e")
        ing_scroll = ttk.Scrollbar(ing_frame, orient="vertical", command=self.ing_tree.yview)
        self.ing_tree.configure(yscrollcommand=ing_scroll.set)
        self.ing_tree.pack(side="left", fill="both", expand=True)
        ing_scroll.pack(side="left", fill="y", padx=(6, 0))

        self.ing_tree.tag_configure("odd", background="#f7f9ff")

        resultados = ttk.Labelframe(parent, text="Resumen de costos", style="Card.TLabelframe", padding=12)
        resultados.pack(fill="x")

        self._create_result_row(resultados, "Costo de ingredientes (tanda)", self.costo_ing_var, 0)
        self._create_result_row(resultados, "Total de la tanda", self.costo_tanda_var, 1)
        self._create_result_row(resultados, "Unidades por tanda", self.unidades_tanda_var, 2, is_currency=False)
        self._create_result_row(resultados, "Costo por unidad", self.costo_u_var, 3)
        self._create_result_row(resultados, "Precio final", self.precio_u_final_var, 4)
        self._create_result_row(resultados, "Margen unitario", self.margen_unitario_var, 5)

    def _build_catalog_panel(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="🧺 Catálogo de insumos", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 12))

        search_frame = ttk.Frame(parent, style="Card.TFrame")
        search_frame.pack(fill="x", pady=(0, 12))
        ttk.Label(search_frame, text="Buscar", style="Caption.TLabel").pack(side="left", padx=(0, 6))
        entry = ttk.Entry(search_frame, textvariable=self.catalog_search_var)
        entry.pack(side="left", fill="x", expand=True)

        table_container = ttk.Frame(parent, style="Card.TFrame")
        table_container.pack(fill="both", expand=True)

        columns = ("nombre", "unidad", "costo_compra", "factor", "costo_uso")
        self.catalog_tree = ttk.Treeview(table_container, columns=columns, show="headings", height=16)
        self.catalog_tree.heading("nombre", text="Nombre")
        self.catalog_tree.heading("unidad", text="Unidad compra")
        self.catalog_tree.heading("costo_compra", text="Costo unidad compra")
        self.catalog_tree.heading("factor", text="Factor uso")
        self.catalog_tree.heading("costo_uso", text="Costo unidad uso")
        self.catalog_tree.column("nombre", width=180)
        self.catalog_tree.column("unidad", width=110)
        self.catalog_tree.column("costo_compra", width=140, anchor="e")
        self.catalog_tree.column("factor", width=110, anchor="e")
        self.catalog_tree.column("costo_uso", width=140, anchor="e")
        scroll = ttk.Scrollbar(table_container, orient="vertical", command=self.catalog_tree.yview)
        self.catalog_tree.configure(yscrollcommand=scroll.set)
        self.catalog_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.catalog_tree.tag_configure("odd", background="#f7f9ff")

        form = ttk.Labelframe(parent, text="Detalle de insumo", style="Card.TLabelframe", padding=12)
        form.pack(fill="x", pady=12)
        self._create_labeled_entry(form, "Nombre", self.insumo_vars["nombre"], 0, 0, columnspan=2)
        self._create_labeled_entry(form, "Unidad de compra", self.insumo_vars["unidad_compra"], 1, 0, columnspan=2)
        self._create_labeled_entry(form, "Costo por unidad de compra", self.insumo_vars["costo_por_unidad_compra"], 2, 0, columnspan=2)
        self._create_labeled_entry(form, "Factor de uso", self.insumo_vars["factor_uso"], 3, 0, columnspan=2)

        btn_frame = ttk.Frame(parent, style="Card.TFrame")
        btn_frame.pack(fill="x")
        ttk.Button(btn_frame, text="Nuevo insumo", style="Secondary.TButton", command=self.new_insumo).pack(fill="x", pady=4)
        ttk.Button(btn_frame, text="Guardar / actualizar", style="Accent.TButton", command=self.save_insumo).pack(fill="x", pady=4)
        ttk.Button(btn_frame, text="Eliminar", style="Secondary.TButton", command=self.delete_insumo).pack(fill="x", pady=4)

    def _create_labeled_entry(self, parent: ttk.Widget, label: str, variable: tk.StringVar, row: int, column: int, columnspan: int = 1) -> None:
        lbl = ttk.Label(parent, text=label, style="FormLabel.TLabel")
        lbl.grid(row=row, column=column * 2, sticky="w", padx=4, pady=4)
        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row, column=column * 2 + 1, sticky="ew", padx=4, pady=4, columnspan=columnspan)
        parent.grid_columnconfigure(column * 2 + 1, weight=1)

    def _create_result_row(self, parent: ttk.Frame, label: str, variable: tk.StringVar, row: int, *, is_currency: bool = True) -> None:
        ttk.Label(parent, text=label, style="Caption.TLabel").grid(row=row, column=0, sticky="w", padx=6, pady=4)
        value_style = "ValueLabel.TLabel" if is_currency else "Caption.TLabel"
        ttk.Label(parent, textvariable=variable, style=value_style).grid(row=row, column=1, sticky="e", padx=6, pady=4)
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

        visual_index = 0
        for idx, producto in enumerate(self.data.productos):
            if search and search not in producto.nombre.lower():
                continue
            costo = producto.costo_por_unidad(self.data.catalogo)
            precio = producto.precio_final(self.data.catalogo)
            tags = ("odd",) if visual_index % 2 else ()
            self.product_tree.insert("", "end", iid=str(idx), values=(producto.nombre, format_currency(costo), format_currency(precio)), tags=tags)
            visual_index += 1

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
                self.product_vars["unidades_por_tanda"].set("1")
                self.product_vars["precio_final_manual"].set("0")
                self.quick_cost_var.set("$ 0,00")
                self.quick_price_var.set("$ 0,00")
                self.costo_ing_var.set("$ 0,00")
                self.costo_tanda_var.set("$ 0,00")
                self.unidades_tanda_var.set("0")
                self.costo_u_var.set("$ 0,00")
                self.precio_u_final_var.set("$ 0,00")
                self.margen_unitario_var.set("$ 0,00")
                self.margen_pct_var.set("0,00 %")
                return

            producto = self.data.productos[self.current_index]
            self.product_name_var.set(producto.nombre)
            for field, var in self.product_vars.items():
                value = getattr(producto, field)
                if isinstance(value, float):
                    var.set(format_number(value))
                else:
                    var.set(str(value))

            visual_index = 0
            for ingrediente in producto.ingredientes:
                insumo = self._find_insumo(ingrediente.insumo_nombre)
                cantidad = format_number(ingrediente.cantidad_uso)
                if insumo:
                    costo_unit = ingrediente.override_costo_uso if ingrediente.override_costo_uso is not None and ingrediente.override_costo_uso >= 0 else insumo.costo_por_unidad_uso()
                    costo_total = ingrediente.costo_total(insumo)
                    tags = ("odd",) if visual_index % 2 else ()
                    self.ing_tree.insert("", "end", iid=ingrediente.insumo_nombre, values=(ingrediente.insumo_nombre, cantidad, format_currency(costo_unit), format_currency(costo_total)), tags=tags)
                else:
                    tags = ("odd",) if visual_index % 2 else ()
                    self.ing_tree.insert("", "end", iid=ingrediente.insumo_nombre, values=(ingrediente.insumo_nombre + " (faltante)", cantidad, "-", "-"), tags=tags)
                visual_index += 1

            self._update_results()
        finally:
            self._updating_ui = False

    def _refresh_catalog(self) -> None:
        search = self.catalog_search_var.get().strip().lower()
        for item in self.catalog_tree.get_children():
            self.catalog_tree.delete(item)
        visual_index = 0
        for insumo in self.data.catalogo:
            if search and search not in insumo.nombre.lower():
                continue
            tags = ("odd",) if visual_index % 2 else ()
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
                tags=tags,
            )
            visual_index += 1
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
                messagebox.showerror("Ingredientes", "Ingresá un valor numérico válido para el costo personalizado.")
                return
            if override < 0:
                messagebox.showerror("Ingredientes", "El costo personalizado debe ser mayor o igual a cero.")
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
                allowed = {"nombre", "unidades_por_tanda", "precio_final_manual"}
                filtered = {k: v for k, v in prod_copy.items() if k in allowed}
                producto = Producto(**filtered)
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
        try:
            producto.precio_final_manual = parse_float(self.product_vars["precio_final_manual"].get())
        except ValueError:
            pass

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
        costo_tanda = producto.costo_tanda(self.data.catalogo)
        precio_final = producto.precio_final(self.data.catalogo)
        unidades = producto.unidades_por_tanda_validas()
        costo_u = producto.costo_por_unidad(self.data.catalogo)
        margen = precio_final - costo_u
        margen_pct = (margen / costo_u * 100) if costo_u else 0.0

        self.costo_ing_var.set(format_currency(costo_ing))
        self.costo_tanda_var.set(format_currency(costo_tanda))
        self.unidades_tanda_var.set(str(producto.unidades_por_tanda))
        self.costo_u_var.set(format_currency(costo_u))
        self.precio_u_final_var.set(format_currency(precio_final))
        self.margen_unitario_var.set(format_currency(margen))
        self.margen_pct_var.set(f"{format_number(margen_pct)} %")
        self.quick_cost_var.set(format_currency(costo_u))
        self.quick_price_var.set(format_currency(precio_final))

    # -------------------------
    # Mainloop
    # -------------------------


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
