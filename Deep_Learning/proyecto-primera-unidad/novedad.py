
# ============================================================
# MÓDULO: novedad.py
# Detección de novedad léxica en corpus quechua
# ============================================================
from collections import Counter
import re
import unicodedata

class Novedad:
    """
    Módulo de detección de novedad léxica.

    Implementa:
    - comparar_con_diccionario(palabras_corpus, diccionario)
    - inferir_categoria(palabra, tokenizador, diccionario)
    - calcular_confianza(termino, frecuencias, alineaciones)
    """

    def __init__(self, tokenizador=None):
        self.tokenizador = tokenizador

    # ------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------
    def limpiar_palabra(self, palabra):
        palabra = str(palabra).lower().strip()
        palabra = re.sub(r"^[¿¡\.,;:\?\!]+|[¿¡\.,;:\?\!]+$", "", palabra)
        palabra = re.sub(r"\s+", " ", palabra)
        return palabra.strip()

    def normalizar(self, texto):
        """Normaliza para comparar contra diccionario."""
        texto = self.limpiar_palabra(texto)
        nfkd = unicodedata.normalize("NFKD", texto)
        return "".join(c for c in nfkd if unicodedata.category(c) != "Mn")

    def _extraer_lema(self, entrada):
        if isinstance(entrada, dict):
            return entrada.get("lema") or entrada.get("entrada") or entrada.get("quechua") or ""
        return ""

    def _indice_diccionario(self, diccionario):
        """Construye índice normalizado lema -> entrada."""
        indice = {}

        if isinstance(diccionario, list):
            for entrada in diccionario:
                lema = self._extraer_lema(entrada)
                if lema:
                    indice.setdefault(self.normalizar(lema), entrada)

        elif isinstance(diccionario, dict):
            # Caso diccionario directo {lema: info}
            for clave, valor in diccionario.items():
                if clave != "quechua_espanol":
                    indice.setdefault(self.normalizar(clave), valor)

            # Caso estructura {"quechua_espanol": ...}
            contenido = diccionario.get("quechua_espanol")
            if isinstance(contenido, list):
                for entrada in contenido:
                    lema = self._extraer_lema(entrada)
                    if lema:
                        indice.setdefault(self.normalizar(lema), entrada)
            elif isinstance(contenido, dict):
                for clave, valor in contenido.items():
                    indice.setdefault(self.normalizar(clave), valor)

        return indice

    def _palabras_desde_corpus(self, corpus_tokenizado):
        palabras = []
        for frase in corpus_tokenizado:
            for palabra in frase.get("palabras_originales", []):
                limpia = self.limpiar_palabra(palabra)
                if limpia:
                    palabras.append(limpia)
        return palabras

    def _tokenizar_palabra(self, palabra, tokenizador=None):
        palabra = self.limpiar_palabra(palabra)
        tok = tokenizador or self.tokenizador
        if not palabra:
            return []

        if tok is not None:
            try:
                if hasattr(tok, "explicar_aglutinacion"):
                    tokens, _ = tok.explicar_aglutinacion(palabra)
                    return [self.limpiar_palabra(t) for t in tokens if self.limpiar_palabra(t)]
                if hasattr(tok, "tokenizar_palabra"):
                    return [self.limpiar_palabra(t) for t in tok.tokenizar_palabra(palabra) if self.limpiar_palabra(t)]
                if callable(tok):
                    return [self.limpiar_palabra(t) for t in tok(palabra) if self.limpiar_palabra(t)]
            except Exception:
                pass

        return [palabra]

    def _extraer_info_entrada(self, entrada):
        """Extrae definición y categoría soportando varios formatos."""
        if isinstance(entrada, str):
            return entrada, ["desconocida"]

        if isinstance(entrada, dict):
            definicion = (
                entrada.get("definicion") or
                entrada.get("significado") or
                entrada.get("traduccion") or
                entrada.get("espanol") or
                "Sin definición disponible"
            )
            categoria = (
                entrada.get("categoria") or
                entrada.get("categorias") or
                entrada.get("pos") or
                entrada.get("tipo") or
                ["desconocida"]
            )
            if isinstance(categoria, str):
                categoria = [categoria]
            return definicion, categoria

        return "Formato no reconocido", ["desconocida"]

    # ------------------------------------------------------------
    # 3.3 Comparación con diccionario
    # ------------------------------------------------------------
    def comparar_con_diccionario(self, palabras_corpus, diccionario):
        """
        Identifica términos registrados y no registrados.
        palabras_corpus puede ser lista o Counter.
        """
        indice = self._indice_diccionario(diccionario)

        if isinstance(palabras_corpus, Counter):
            palabras = list(palabras_corpus.keys())
        else:
            palabras = list(palabras_corpus)

        palabras_unicas = sorted(set(self.limpiar_palabra(p) for p in palabras if self.limpiar_palabra(p)))
        registradas = []
        no_registradas = []

        for palabra in palabras_unicas:
            if self.normalizar(palabra) in indice:
                registradas.append(palabra)
            else:
                no_registradas.append(palabra)

        return {
            "palabras_unicas": palabras_unicas,
            "palabras_registradas": registradas,
            "palabras_no_registradas": no_registradas
        }

    # ------------------------------------------------------------
    # 3.3 Inferencia de categoría
    # ------------------------------------------------------------
    def inferir_categoria(self, palabra, tokenizador, diccionario):
        """
        Propone raíz, significado y categoría a partir del tokenizador y diccionario.
        """
        indice = self._indice_diccionario(diccionario)
        morfemas = self._tokenizar_palabra(palabra, tokenizador)

        raiz = morfemas[0] if morfemas else self.limpiar_palabra(palabra)
        entrada_raiz = indice.get(self.normalizar(raiz))

        # Si la primera raíz no aparece, busca la raíz más larga del diccionario que sea prefijo.
        if entrada_raiz is None:
            palabra_norm = self.normalizar(palabra)
            posibles = [lema for lema in indice.keys() if len(lema) >= 3 and palabra_norm.startswith(lema)]
            if posibles:
                raiz_norm = max(posibles, key=len)
                raiz = raiz_norm
                entrada_raiz = indice.get(raiz_norm)

        if entrada_raiz is not None:
            significado, categoria = self._extraer_info_entrada(entrada_raiz)
        else:
            significado, categoria = "Raíz no encontrada en diccionario", ["desconocida"]

        return {
            "raiz_propuesta": raiz,
            "morfemas_detectados": morfemas,
            "significado_propuesto": significado,
            "categoria_inferida": categoria
        }

    # ------------------------------------------------------------
    # 3.3 Cálculo de confianza
    # ------------------------------------------------------------
    def calcular_confianza(self, termino, frecuencias, alineaciones=None, info_inferida=None, diccionario=None):
        """
        Asigna confianza combinando frecuencia, raíz encontrada, categoría y alineación.
        """
        termino = self.limpiar_palabra(termino)
        frecuencia = frecuencias.get(termino, 0)

        confianza = 0.30

        if frecuencia >= 2:
            confianza += 0.20
        if frecuencia >= 4:
            confianza += 0.10

        if info_inferida is not None:
            if info_inferida.get("significado_propuesto") not in [None, "Raíz no encontrada en diccionario"]:
                confianza += 0.25
            if info_inferida.get("categoria_inferida") not in [None, ["desconocida"]]:
                confianza += 0.10

        if alineaciones is not None and self._aparece_en_alineaciones(termino, alineaciones):
            confianza += 0.05

        return round(min(confianza, 0.95), 2)

    def _aparece_en_alineaciones(self, termino, alineaciones):
        termino = self.limpiar_palabra(termino)
        for item in alineaciones:
            tokens = [self.limpiar_palabra(t) for t in item.get("frase_quechua_tokens", [])]
            if termino in tokens:
                return True
        return False

    def _frases_ejemplo(self, termino, corpus_tokenizado, max_ejemplos=5):
        termino = self.limpiar_palabra(termino)
        ejemplos = []
        for frase in corpus_tokenizado:
            palabras = [self.limpiar_palabra(p) for p in frase.get("palabras_originales", [])]
            if termino in palabras:
                ejemplos.append(frase["id"])
        return ejemplos[:max_ejemplos]

    def generar_terminos_nuevos(self, corpus_tokenizado, diccionario, tokenizador=None, alineaciones=None, min_freq=1):
        """Genera la estructura de terminos_nuevos_corpus.json."""
        palabras = self._palabras_desde_corpus(corpus_tokenizado)
        frecuencias = Counter(palabras)
        comparacion = self.comparar_con_diccionario(frecuencias, diccionario)

        nuevos = []
        for termino in comparacion["palabras_no_registradas"]:
            freq = frecuencias.get(termino, 0)
            if freq < min_freq:
                continue

            info = self.inferir_categoria(termino, tokenizador or self.tokenizador, diccionario)
            confianza = self.calcular_confianza(
                termino,
                frecuencias,
                alineaciones=alineaciones,
                info_inferida=info,
                diccionario=diccionario
            )

            nuevos.append({
                "termino": termino,
                "frecuencia_corpus": freq,
                "raiz_propuesta": info["raiz_propuesta"],
                "morfemas_detectados": info["morfemas_detectados"],
                "significado_propuesto": info["significado_propuesto"],
                "categoria_inferida": info["categoria_inferida"],
                "confianza": confianza,
                "frases_ejemplo": self._frases_ejemplo(termino, corpus_tokenizado),
                "estado_recomendado": (
                    "alta_confianza" if confianza >= 0.70 else
                    "corpus_provisional" if confianza >= 0.50 else
                    "solo_revision"
                )
            })

        nuevos.sort(key=lambda x: (-x["confianza"], -x["frecuencia_corpus"], x["termino"]))

        return {
            "resumen": {
                "total_palabras_distintas_corpus": len(comparacion["palabras_unicas"]),
                "palabras_no_registradas": len(comparacion["palabras_no_registradas"]),
                "palabras_registradas": len(comparacion["palabras_registradas"])
            },
            "nuevos_terminos": nuevos
        }
