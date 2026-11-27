# Fil: Script/gui_helpers.py — Återanvändbara Tk-hjälpfunktioner
#
# Gör ttk.Treeview interaktiv enligt AGENTS.md §10:
#   * Sortera kolumner genom klick på kolumnhuvud (växlande stigande/
#     fallande, nummer förstås numeriskt)
#   * Flytta kolumner genom att DRA ett kolumnhuvud till en annan plats
#     (via displaycolumns — ordningen gäller tills appen stängs)

from __future__ import annotations

from typing import Sequence


def make_treeview_interactive(tree, data_columns: Sequence[str]):
    """Aktiverar kolumnsortering (klick) och kolumnflyttning (drag).

    `data_columns` är kolumnnamnen i startordning (utan '#0'). Returnerar
    tree så anropet kan kedjas.
    """
    columns = list(data_columns)
    if not columns:
        return tree
    display = list(columns)
    sort_descending = {column: False for column in columns}

    def _sort_key(value: str):
        try:
            return (0, float(str(value).replace(" ", "")), "")
        except (TypeError, ValueError):
            return (1, 0.0, str(value))

    def sort_column(column: str) -> None:
        reverse = sort_descending.get(column, False)
        items = [(tree.set(item_id, column), item_id)
                 for item_id in tree.get_children("")]
        items.sort(key=lambda pair: _sort_key(pair[0]), reverse=reverse)
        for index, (_value, item_id) in enumerate(items):
            tree.move(item_id, "", index)
        sort_descending[column] = not reverse

    def _on_press(event) -> None:
        try:
            if tree.identify("region", event.x, event.y) == "heading":
                tree._drag_source = tree.identify_column(event.x)
        except Exception:
            tree._drag_source = None

    def _on_release(event) -> None:
        source = getattr(tree, "_drag_source", None)
        tree._drag_source = None
        if not source:
            return
        try:
            target = tree.identify_column(event.x)
        except Exception:
            return
        if not target or source == target:
            return
        names = {f"#{index + 1}": column
                 for index, column in enumerate(display)}
        if source not in names or target not in names:
            return
        source_col, target_col = names[source], names[target]
        display.remove(source_col)
        display.insert(display.index(target_col), source_col)
        tree.configure(displaycolumns=display)

    for column in columns:
        tree.heading(column, command=lambda c=column: sort_column(c))
    tree.bind("<ButtonPress-1>", _on_press)
    tree.bind("<ButtonRelease-1>", _on_release)
    return tree


__all__ = ["make_treeview_interactive"]
