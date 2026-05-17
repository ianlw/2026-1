import json
import unicodedata
from pathlib import Path
from typing import List, Dict

def _normalize(text: str) -> str:
    if not text:
        return ""
    text = text.lower().strip().rstrip(".")
    text = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    return text

class Diccionario:
    def __init__(self, path_qe: str, path_eq: str):
        self.qe = json.loads(Path(path_qe).read_text(encoding="utf-8"))
        self.eq = json.loads(Path(path_eq).read_text(encoding="utf-8"))

        # Índices por lema (normalizados)
        self.idx_qe = {}
        self.idx_eq = {}
        for e in self.qe:
            lema = _normalize(e.get("lema", ""))
            self.idx_qe.setdefault(lema, []).append(e)
        for e in self.eq:
            lema = _normalize(e.get("lema", ""))
            self.idx_eq.setdefault(lema, []).append(e)

    # =============================
    #  Búsqueda exacta
    # =============================
    def buscar_por_quechua(self, lema: str) -> List[Dict]:
        return self.idx_qe.get(_normalize(lema), [])

    def buscar_por_espanol(self, lema: str) -> List[Dict]:
        return self.idx_eq.get(_normalize(lema), [])

    # =============================
    #  Búsqueda flexible
    # =============================
    def buscar_flexible(self, palabra: str, seccion: str = "qe") -> List[Dict]:
        """
        Busca en lema, definición, sinónimos y ejemplos (subcadenas).
        - seccion="qe" busca en Quechua→Español
        - seccion="eq" busca en Español→Quechua
        """
        data = self.qe if seccion == "qe" else self.eq
        p = _normalize(palabra)
        resultados = []
        for e in data:
            texto_busqueda = " ".join([
                e.get("lema", ""),
                e.get("definicion", ""),
                " ".join(e.get("sinonimos", [])),
                " ".join(e.get("ejemplos", []))
            ])
            if p in _normalize(texto_busqueda):
                resultados.append(e)
        return resultados

    # =============================
    #  Funciones adicionales
    # =============================
    def obtener_variantes_dialectales(self, lema: str) -> List[str]:
        variantes = []
        for e in self.buscar_por_quechua(lema):
            variantes.extend(list(e.get("variantes_dialectales", {}).values()))
        return list(dict.fromkeys(variantes))

    def buscar_por_categoria_gramatical(self, categoria: str) -> List[Dict]:
        cat = categoria.strip().lower()
        resultados = []
        for e in (self.qe + self.eq):
            cat_gram = e.get("categoria_gramatical", [])
            # Si es lista, verificar si la categoría está en la lista
            if isinstance(cat_gram, list):
                if any(c.lower() == cat for c in cat_gram):
                    resultados.append(e)
            # Si es string (compatibilidad con datos antiguos)
            elif isinstance(cat_gram, str) and cat_gram.lower() == cat:
                resultados.append(e)
        return resultados

    def buscar_por_campo_semantico(self, campo: str) -> List[Dict]:
        c = campo.strip()
        return [
            e for e in (self.qe + self.eq)
            if e.get("campo_semantico", "") == c
        ]

    def contar_entradas(self) -> Dict:
        return {
            "quechua_espanol": len(self.qe),
            "espanol_quechua": len(self.eq)
        }

    def listar_lemas(self) -> Dict:
        return {
            "quechua_espanol": [e["lema"] for e in self.qe],
            "espanol_quechua": [e["lema"] for e in self.eq]
        }

    def listar_categorias_gramaticales(self) -> List[str]:
        cats = set()
        for e in (self.qe + self.eq):
            cat_gram = e.get("categoria_gramatical")
            if cat_gram:
                # Si es lista, agregar cada elemento
                if isinstance(cat_gram, list):
                    cats.update(cat_gram)
                # Si es string (por compatibilidad), agregarlo directamente
                else:
                    cats.add(cat_gram)
        return sorted(cats)

    def listar_campos_semanticos(self) -> List[str]:
        campos = {e.get("campo_semantico") for e in (self.qe + self.eq) if e.get("campo_semantico")}
        return sorted(campos)
