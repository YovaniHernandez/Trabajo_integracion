import json
from typing import Dict, Any, Optional, Type
from google import genai
from google.genai import types
from pydantic import BaseModel
from config.settings import GEMINI_API_KEY, GEMINI_MODEL
from schemas.models import get_schema_by_name, BaseProductAttributes

class GeminiEnricher:
    def __init__(self, api_key: str = GEMINI_API_KEY, model_name: str = GEMINI_MODEL):
        self.api_key = api_key
        self.model_name = model_name
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

    def enrich_product(
        self,
        sku: str,
        title: str,
        category_name: str,
        schema_name: str,
        parsed_clues: Dict[str, Any],
        search_snippets: list,
        category_defaults: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Uses Gemini to extract and complete structured technical attributes for any category."""
        schema_cls = get_schema_by_name(schema_name) or BaseProductAttributes

        if not self.client:
            print("[GeminiEnricher] Warning: No GEMINI_API_KEY available. Using deterministic fallback.")
            return self._build_deterministic_fallback(sku, title, category_name, parsed_clues, category_defaults, schema_cls)

        prompt = f"""Eres un ingeniero mecánico automotriz especialista en refacciones y motocicletas del mercado mexicano y latinoamericano.

Tu tarea es catalogar un producto para Mercado Libre en la categoría: "{category_name}".
Debes inferir y estructurar con precisión todos los atributos técnicos requeridos siguiendo estrictamente el esquema de datos y las reglas del negocio.

DATOS DEL PRODUCTO:
- SKU: {sku}
- Título original: {title}
- Categoría / Hoja: {category_name}
- Pistas técnicas extraídas: {json.dumps(parsed_clues, ensure_ascii=False)}
- Valores base configurados: {json.dumps(category_defaults, ensure_ascii=False)}

SNIPPETS DE INVESTIGACIÓN WEB:
{json.dumps(search_snippets, ensure_ascii=False, indent=2) if search_snippets else "No se requirieron búsquedas adicionales."}

REGLAS DE CATALOGACIÓN ESTRICTAS:
1. Marca: SIEMPRE debe ser "Genérico" para todos los productos (regla obligatoria de Mercado Libre para evitar infracciones de marca).
2. Campo 'modelo' y 'modelos_compatibles': Debes incluir OBLIGATORIAMENTE TODOS los modelos de motos compatibles señalados en el título original del input, separados por " / ". NO resumas ni omitas ningún modelo indicado en el título.
3. Para Carburadores:
   - En el campo 'modelo', coloca TODOS los modelos de motocicletas compatibles señalados en el título (ej. "FT150 / 150SZ / 150Z / 170Z / DM150 / CYCLONE / LITHIUM / ROCKETMAN / STORM / V-RACER"). NUNCA coloques códigos de carburador como PZ19, PZ26, PZ27 o PZ30 en 'modelo'.
   - El código estándar de carburador va exclusivamente en 'tipo_carburador' (ej. PZ19, PZ26, PZ27, PZ30, CVK).
   - Si el título del carburador no tiene nombres de motos sino cilindradas generales (ej. 70CC / 90CC), coloca las cilindradas o aplicaciones en 'modelo' (ej. "70cc / 90cc").
   - Cantidad de bocas: "1"
   - Cantidad de cilindros: "1"
   - Origen: "China"
4. Para Kits de sprockets:
   - Material del sprocket: SIEMPRE "Acero" (NO usar "Acero #1045").
   - Material del piñón: SIEMPRE "Acero".
   - Dientes de corona y piñón (ej. 38T / 15T).
   - Cantidad de eslabones de cadena (ej. 108, 116, 120, 128, 132).
   - Largo de la cadena: Cadena numérica calculada en milímetros (ej. "1370", "1473", "1524", "1625", "1746").
   - Unidad de Largo de la cadena: "mm"
5. Para Barras de suspensión:
   - Diámetro nominal del tubo en mm según el modelo de moto real (ej. 26.0 para AT110/Strada, 31.0 para FT125/FT150/125Z/150Z, 33.0 para FT200/RT200, 37.0 para DM200/250Z/Storm250, 41.0 para FZ16/FZ 2.0, 30.0 para scooters Axus/Ruda).
   - Largo total en mm según el modelo real (ej. 610.0 Strada70, 645.0 AT110, 710.0 FT125, 730.0 FT150, 830.0 DM200, 765.0 FZ16, 420.0 scooters Axus/Ruda).
   - Posición: PAR, DERECHO o IZQUIERDO.
6. Para Salpicaderas:
   - Altura: 15.0 para Delantera, 18.0 para Trasera (en cm).
   - Unidad de Altura: "cm".
   - Cantidad de agujeros de montaje: 4 para Delantera, 2 para Trasera.
   - Espesor: 3.0 o 3.5 (en mm).
   - Unidad de Espesor: "mm".
   - Material: "Plástico ABS".
   - Acabado: "Satinado".
   - Incluye herrajes de montaje: "No".
7. Devuelve los datos exactamente conformes al schema JSON solicitado.
"""

        # Candidate models fallback list in case of quota or availability limits
        candidate_models = ["gemini-3.5-flash-lite", "gemini-3.5-flash", self.model_name]
        candidate_models = list(dict.fromkeys(candidate_models))

        for model_to_try in candidate_models:
            try:
                response = self.client.models.generate_content(
                    model=model_to_try,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=schema_cls,
                        temperature=0.1,
                    ),
                )
                raw_json = response.text.strip()
                data = json.loads(raw_json)
                # Enforce business rules
                data["marca"] = "Genérico"
                if "material_del_sprocket" in data:
                    data["material_del_sprocket"] = "Acero"
                if "material_del_pinon" in data:
                    data["material_del_pinon"] = "Acero"
                return data
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "503" in err_msg or "NOT_FOUND" in err_msg:
                    print(f"[GeminiEnricher] Warning on {model_to_try}: {err_msg[:90]}... Trying next model in pool.")
                    continue
                else:
                    print(f"[GeminiEnricher] Non-recoverable error on {model_to_try}: {e}")
                    break

        print("[GeminiEnricher] All LLM models exhausted. Using deterministic fallback logic.")
        return self._build_deterministic_fallback(sku, title, category_name, parsed_clues, category_defaults, schema_cls)

    def _build_deterministic_fallback(
        self,
        sku: str,
        title: str,
        category_name: str,
        parsed_clues: Dict[str, Any],
        category_defaults: Dict[str, Any],
        schema_cls: Type[BaseModel],
    ) -> Dict[str, Any]:
        """Builds a valid attribute dictionary using deterministic rules and defaults when API is unavailable."""
        models_list = parsed_clues.get("models", [])
        models_str = " / ".join(models_list) if models_list else "Universal"

        fallback_data: Dict[str, Any] = {
            "marca": "Genérico",
            "numero_de_parte": sku,
            "numero_de_pedimento": "N/A",
            "origen": category_defaults.get("Origen", "China"),
            "modelos_compatibles": models_list,
        }

        # Specific category fallbacks
        if "Carburador" in schema_cls.__name__:
            fallback_data.update({
                "modelo": models_str,
                "cantidad_de_bocas": category_defaults.get("Cantidad de bocas", "1"),
                "cantidad_de_cilindros": category_defaults.get("Cantidad de cilindros", "1"),
                "cilindrada_cc": parsed_clues.get("displacement_cc"),
            })
        elif "Sprocket" in schema_cls.__name__:
            fallback_data.update({
                "material_del_sprocket": "Acero",
                "material_del_pinon": "Acero",
                "cantidad_dientes_sprocket": parsed_clues.get("cantidad_dientes_sprocket", 38),
                "cantidad_dientes_pinon": parsed_clues.get("cantidad_dientes_pinon", 15),
                "largo_cadena": str(parsed_clues.get("largo_cadena", "1473")),
                "unidad_largo_cadena": "mm",
                "cantidad_eslabones_cadena": parsed_clues.get("cantidad_eslabones_cadena", 116),
                "paso_cadena": parsed_clues.get("paso_cadena", "428"),
                "estilo_conduccion": category_defaults.get("Estilo de conducción en moto", "Calle"),
            })
        elif "Barras" in schema_cls.__name__:
            fallback_data.update({
                "diametro": parsed_clues.get("diametro", 31.0),
                "unidad_diametro": "mm",
                "largo": parsed_clues.get("largo", 720.0),
                "unidad_largo": "mm",
                "posicion": parsed_clues.get("posicion", "PAR"),
                "color": parsed_clues.get("color", "Negro"),
            })
        elif "Salpicadera" in schema_cls.__name__:
            fallback_data.update({
                "modelo": models_str,
                "color": parsed_clues.get("color", "Negro"),
                "acabado": parsed_clues.get("acabado", "Satinado"),
                "posicion": parsed_clues.get("posicion", "Delantera"),
                "altura": parsed_clues.get("altura", 15.0),
                "unidad_altura": "cm",
                "incluye_herrajes": "No",
                "cantidad_agujeros": parsed_clues.get("cantidad_agujeros", 4),
                "material": parsed_clues.get("material", "Plástico ABS"),
                "espesor": parsed_clues.get("espesor", 3.0),
                "unidad_espesor": "mm",
            })

        return fallback_data
