import pandas as pd
import json
import re

# Importamos la librería creada
from diccionario_utils import Diccionario

class TokenizadorQuechua:
    def __init__(self, instancia_diccionario):
        """Inicializa la clase recibiendo una instancia de Diccionario"""
        self.diccionario = instancia_diccionario

    def explicar_aglutinacion(self, palabra_original):
        """
        Devuelve la descomposición morfológica con explicación.
        """
        # Limpiamos puntuación básica respetando el apóstrofo quechua
        palabra_limpia = re.sub(r'[^\w\s\']', '', palabra_original.lower())
        if not palabra_limpia:
            return [], ""

        # Validamos si la palabra completa ya es una raíz conocida en tu diccionario
        if self.diccionario.buscar_por_quechua(palabra_limpia):
            return [palabra_limpia], ""

        # Si no es exacta, hacemos la búsqueda aglutinante (recortando desde el final)
        for i in range(len(palabra_limpia), 1, -1):
            posible_raiz = palabra_limpia[:i]

            # Si la porción inicial existe en el diccionario, es la raíz
            if self.diccionario.buscar_por_quechua(posible_raiz):
                sufijo = palabra_limpia[i:]
                if sufijo:
                    explicacion = f"La palabra '{palabra_original}' se descompone en 2 morfemas: {posible_raiz} (raíz) + {sufijo} (sufijo)"
                    return [posible_raiz, sufijo], explicacion

        # Si no se encuentra ninguna raíz en el diccionario, se asume como palabra nueva/desconocida
        return [palabra_limpia], ""

    def procesar_corpus_quechua(self, ruta_corpus):
        """
        Aplica tokenización a todas las frases quechuas del CSV y genera la estructura JSON.
        """

        #df = pd.read_csv(ruta_corpus, encoding='utf-8')
        # Variables de acumulación para las métricas del proyecto
        frases_procesadas = []
        total_tokens_generados = 0
        palabras_multiples_tokens = 0

        # Iteración sobre cada registro (oración) del corpus
        for idx, row in df.iterrows():
            frase_original = str(row['quechua_texto']).strip()
            # Filtro de control de calidad: omite filas nulas o vacías
            if pd.isna(row['quechua_texto']) or not frase_original:
                continue
            # Tokenización básica por espacios en blanco
            palabras_originales = frase_original.split()
            tokens_frase = []
            explicaciones_frase = []
            # Procesamiento morfológico de cada palabra individual
            for palabra in palabras_originales:
                # Usamos el método de esta misma clase
                tokens_palabra, explicacion = self.explicar_aglutinacion(palabra)
                tokens_frase.extend(tokens_palabra)
                # Si la palabra generó más de 1 token, cuenta como aglutinada
                if len(tokens_palabra) > 1:
                    palabras_multiples_tokens += 1
                    if explicacion:
                        explicaciones_frase.append(explicacion)

            # Determinar la explicación final de la frase
            if explicaciones_frase:
                explicacion_final = " | ".join(explicaciones_frase)
            else:
                explicacion_final = "No se detectó aglutinación en esta frase."

            frases_procesadas.append({
                "id": idx + 1,
                "frase_original": frase_original,
                "tokens": tokens_frase,
                "palabras_originales": palabras_originales,
                "longitud_tokens": len(tokens_frase),
                "longitud_palabras": len(palabras_originales),
                "explicacion_aglutinacion": explicacion_final
            })

            total_tokens_generados += len(tokens_frase)

        # Estructurar el diccionario de salida exacto
        salida_json = {
            "total_frases": len(frases_procesadas),
            "frases": frases_procesadas,
            #"ejemplos": frases_procesadas[:3], # Muestra solo 3 ejemplos
            "estadisticas_tokenizacion": {
                "total_tokens_generados": total_tokens_generados,
                "promedio_tokens_por_frase": round(total_tokens_generados / len(frases_procesadas), 1) if frases_procesadas else 0,
                "palabras_con_multiples_tokens": palabras_multiples_tokens
            }
        }

        return salida_json
