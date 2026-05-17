
# ============================================================
# MÓDULO: terminos.py
# Extracción de n-gramas y traducciones candidatas
# ============================================================
from collections import Counter
import math
import re

class Terminos:
    """
    Módulo de extracción de términos.

    Implementa:
    - extraer_ngramas(corpus_tokenizado, n_min, n_max, min_freq)
    - calcular_pmi(ngrama, corpus)
    - obtener_traduccion_ngrama(ngrama, alineaciones)
    """

    def __init__(self, tokenizador=None):
        self.tokenizador = tokenizador

    # ------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------
    def limpiar_palabra(self, palabra):
        """Limpia signos externos y normaliza a minúsculas."""
        palabra = str(palabra).lower().strip()
        palabra = re.sub(r"^[¿¡\.,;:\?\!]+|[¿¡\.,;:\?\!]+$", "", palabra)
        palabra = re.sub(r"\s+", " ", palabra)
        return palabra.strip()

    def limpiar_tokens(self, tokens):
        """Limpia una lista de tokens eliminando vacíos."""
        return [self.limpiar_palabra(t) for t in tokens if self.limpiar_palabra(t)]

    def _corpus_palabras_originales(self, corpus_tokenizado):
        """
        Convierte las frases tokenizadas en lista de pares:
        [{id, palabras}], usando palabras originales limpias.
        """
        corpus = []
        for frase in sorted(corpus_tokenizado, key=lambda x: x["id"]):
            palabras = self.limpiar_tokens(frase.get("palabras_originales", []))
            if palabras:
                corpus.append({"id": frase["id"], "palabras": palabras})
        return corpus

    def _tokenizar_palabra_quechua(self, palabra):
        """
        Tokeniza una palabra quechua a morfemas usando el tokenizador heredado
        si existe. Si no existe, devuelve la palabra limpia como único token.
        """
        palabra = self.limpiar_palabra(palabra)
        if not palabra:
            return []

        if self.tokenizador is not None:
            try:
                if hasattr(self.tokenizador, "explicar_aglutinacion"):
                    tokens, _ = self.tokenizador.explicar_aglutinacion(palabra)
                    return self.limpiar_tokens(tokens)
                if hasattr(self.tokenizador, "tokenizar_palabra"):
                    return self.limpiar_tokens(self.tokenizador.tokenizar_palabra(palabra))
                if callable(self.tokenizador):
                    return self.limpiar_tokens(self.tokenizador(palabra))
            except Exception:
                pass

        return [palabra]

    def _mapear_palabras_a_tokens(self, palabras_originales):
        """
        Mapea cada palabra original a los índices de los morfemas que genera.

        Ejemplo:
        palabras_originales = ["wasiman", "rirani"]
        tokens = ["wasi", "man", "rira", "ni"]
        mapeo = {0: [0,1], 1: [2,3]}
        """
        tokens = []
        mapeo = {}

        for idx_palabra, palabra in enumerate(palabras_originales):
            morfemas = self._tokenizar_palabra_quechua(palabra)
            inicio = len(tokens)
            tokens.extend(morfemas)
            fin = len(tokens)
            mapeo[idx_palabra] = list(range(inicio, fin))

        return tokens, mapeo

    def _traduccion_valida(self, traduccion, max_tokens=6):
        """Evita traducciones con ruido, signos o frases demasiado largas."""
        traduccion = str(traduccion).strip().lower()
        if not traduccion:
            return False

        tokens = traduccion.split()
        signos = {"¿", "?", ".", ",", ";", ":", "¡", "!"}

        if len(tokens) == 0 or len(tokens) > max_tokens:
            return False
        if any(t in signos for t in tokens):
            return False
        if any(re.fullmatch(r"[¿?.,;:¡!]+", t) for t in tokens):
            return False

        return True

    # ------------------------------------------------------------
    # 3.1 Cálculo de PMI
    # ------------------------------------------------------------
    def calcular_pmi(self, ngrama, corpus):
        """
        Calcula la mutua información puntual (PMI) de un n-grama.

        ngrama: tuple/list de palabras, ej. ("sapa", "kuti")
        corpus: lista de listas de palabras limpias
        """
        ngrama = tuple(self.limpiar_tokens(ngrama))
        total = sum(len(frase) for frase in corpus)
        if total == 0 or len(ngrama) == 0:
            return 0.0

        freq_individual = Counter(p for frase in corpus for p in frase)
        n = len(ngrama)

        freq_ngrama = sum(
            1
            for frase in corpus
            for i in range(len(frase) - n + 1)
            if tuple(frase[i:i+n]) == ngrama
        )

        if freq_ngrama == 0:
            return 0.0

        p_ng = freq_ngrama / total
        p_ind = 1.0
        for palabra in ngrama:
            p_ind *= freq_individual.get(palabra, 0) / total

        if p_ind == 0:
            return 0.0

        return round(math.log2(p_ng / p_ind), 4)

    # ------------------------------------------------------------
    # 3.1 Extracción de n-gramas frecuentes
    # ------------------------------------------------------------
    def extraer_ngramas(self, corpus_tokenizado, n_min=2, n_max=3, min_freq=2):
        """
        Extrae n-gramas frecuentes desde palabras originales, no desde morfemas.
        Devuelve la estructura solicitada para ngramas_quechua_frecuentes.json.
        """
        corpus_con_id = self._corpus_palabras_originales(corpus_tokenizado)
        corpus = [item["palabras"] for item in corpus_con_id]

        resultado = {
            "parametros": {
                "n_minimo": n_min,
                "n_maximo": n_max,
                "frecuencia_minima": min_freq
            },
            "bigramas": [],
            "trigramas": []
        }

        for n in range(n_min, n_max + 1):
            contador = Counter()

            for item in corpus_con_id:
                palabras = item["palabras"]
                for i in range(len(palabras) - n + 1):
                    contador[tuple(palabras[i:i+n])] += 1

            salida = []
            for ngrama, frecuencia in sorted(contador.items(), key=lambda x: (-x[1], x[0])):
                if frecuencia < min_freq:
                    continue

                frases_ejemplo = []
                for item in corpus_con_id:
                    palabras = item["palabras"]
                    for i in range(len(palabras) - n + 1):
                        if tuple(palabras[i:i+n]) == ngrama:
                            frases_ejemplo.append(item["id"])
                            break

                salida.append({
                    "ngrama": " ".join(ngrama),
                    "frecuencia": frecuencia,
                    "pmi": self.calcular_pmi(ngrama, corpus),
                    "frases_ejemplo": frases_ejemplo[:5]
                })

            if n == 2:
                resultado["bigramas"] = salida
            elif n == 3:
                resultado["trigramas"] = salida[:20]

        return resultado

    # ------------------------------------------------------------
    # 3.2 Traducción candidata de n-gramas
    # ------------------------------------------------------------
    def obtener_traduccion_ngrama(self, ngrama, alineaciones, corpus_tokenizado=None):
        """
        Propone traducción candidata para un n-grama usando alineaciones.

        Se usa corpus_tokenizado para ubicar el n-grama a nivel de palabras originales
        y mapear esas palabras a morfemas antes de consultar las alineaciones.
        """
        palabras_ng = self.limpiar_tokens(str(ngrama).split())
        if not palabras_ng:
            return None

        alineacion_por_id = {a["id"]: a for a in alineaciones}
        corpus_por_id = {}
        if corpus_tokenizado is not None:
            corpus_por_id = {f["id"]: f for f in corpus_tokenizado}

        conteo_traducciones = Counter()
        total_apariciones = 0

        for fid, datos_alineacion in alineacion_por_id.items():
            # Si existe corpus original, se ubica el n-grama en palabras originales.
            if fid in corpus_por_id:
                palabras_originales = self.limpiar_tokens(corpus_por_id[fid].get("palabras_originales", []))
            else:
                # Fallback: se usa tokens quechuas si no existe corpus original.
                palabras_originales = self.limpiar_tokens(datos_alineacion.get("frase_quechua_tokens", []))

            # Buscar posiciones donde aparece el n-grama como secuencia contigua.
            posiciones_palabras = []
            n = len(palabras_ng)
            for i in range(len(palabras_originales) - n + 1):
                if palabras_originales[i:i+n] == palabras_ng:
                    posiciones_palabras = list(range(i, i+n))
                    break

            if not posiciones_palabras:
                continue

            total_apariciones += 1

            # Convertimos posiciones de palabras a índices de morfemas.
            _, mapeo = self._mapear_palabras_a_tokens(palabras_originales)
            indices_qu_objetivo = set()
            for pos in posiciones_palabras:
                indices_qu_objetivo.update(mapeo.get(pos, []))

            if not indices_qu_objetivo:
                continue

            # Recuperamos índices españoles alineados con esos morfemas.
            indices_es = set()
            for ali in datos_alineacion.get("alineaciones", []):
                q_idx = ali.get("quechua_idx", [])
                e_idx = ali.get("espanol_idx", [])
                if any(q in indices_qu_objetivo for q in q_idx):
                    indices_es.update(e_idx)

            tokens_es = self.limpiar_tokens(datos_alineacion.get("frase_espanol_tokens", []))
            if indices_es:
                traduccion = " ".join(
                    tokens_es[i]
                    for i in sorted(indices_es)
                    if i < len(tokens_es)
                ).strip()

                if self._traduccion_valida(traduccion):
                    conteo_traducciones[traduccion] += 1

        if not conteo_traducciones:
            return None

        traduccion_principal, frecuencia = conteo_traducciones.most_common(1)[0]
        variantes = [
            {"traduccion": t, "frecuencia": f}
            for t, f in conteo_traducciones.most_common()
            if t != traduccion_principal
        ]

        return {
            "ngrama_quechua": " ".join(palabras_ng),
            "traduccion_candidata": traduccion_principal,
            "confianza": round(frecuencia / sum(conteo_traducciones.values()), 4),
            "frecuencia_alineacion": frecuencia,
            "total_apariciones": total_apariciones,
            "variantes_encontradas": variantes[:5]
        }

    def obtener_traducciones_candidatas(self, ngramas_resultado, alineaciones, corpus_tokenizado=None):
        """Obtiene traducciones candidatas para bigramas y trigramas."""
        lista_ngramas = ngramas_resultado.get("bigramas", []) + ngramas_resultado.get("trigramas", [])
        candidatos = []

        for item in lista_ngramas:
            candidato = self.obtener_traduccion_ngrama(
                item["ngrama"],
                alineaciones,
                corpus_tokenizado=corpus_tokenizado
            )
            if candidato is not None:
                candidatos.append(candidato)

        return {
            "resumen": {
                "total_ngramas_evaluados": len(lista_ngramas),
                "candidatos_con_traduccion_valida": len(candidatos),
                "candidatos_sin_traduccion_o_descartados": len(lista_ngramas) - len(candidatos)
            },
            "candidatos": candidatos
        }
