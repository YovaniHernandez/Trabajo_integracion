import re
from typing import Dict, Any, Optional
from google import genai
import anthropic
from config.settings import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
)

EJEMPLOS_ESTILO = """
Casco: CASCO MOTOCROSS IRON RACING – LÍNEA APOLO ¡Diseño agresivo, seguridad garantizada y estilo único! Prepárate para dominar cualquier terreno con la línea de cascos Apolo de Iron Racing, ideales para motocross, enduro o uso urbano. Su estructura robusta y diseño aerodinámico brindan una protección superior sin sacrificar comodidad ni estilo.

** Características destacadas:
-Certificación DOT (cumple con estándares internacionales de seguridad)
-Fabricado en policarbonato de alta resistencia
-Interior acolchado, desmontable y lavable
-Ventilación frontal, superior y trasera para máxima frescura
-Visor alargado tipo cross con diseño deportivo
-Sistema de cierre con hebilla micrométrica
-Tallas: CH, M, G, EG (según disponibilidad)
-Disponible en colores vibrantes y llamativos

Modelos con combinaciones en: Azul Neón, Amarillo Neón, Violeta, y Rojo.
Ideal para motociclistas que buscan impactar visualmente mientras se mantienen protegidos en cada ruta.

---

Caja para motos: Caja Porta-Equipaje IRON RACING – 55 Litros
Lleva todo lo que necesitas con seguridad y estilo con las cajas porta-equipaje Iron Racing, diseñadas especialmente para motociclistas exigentes. Fabricadas en plástico resistente y con diseño cuadrado, estas cajas ofrecen gran capacidad, durabilidad y un toque moderno para tu moto.

Características generales:
-Material: Plástico rígido de alta resistencia
-Dimensiones: 44 × 34.5 × 37.5 cm
-Capacidad: 55 litros
-Diseño cuadrado con refuerzos en esquinas
-Sistema de cierre metálico con llave para mayor seguridad

Colores disponibles:
*Arena – Modelo CAJ-7104-0037
*Verde Oscuro Militar – Modelo CAJ-7104-0038
*Azul Oscuro – Modelo CAJ-7104-0039

Ideales para viajes largos, mensajería o uso diario. ¡Complementa tu motocicleta con el estilo y funcionalidad de Iron Racing!

---

Guantes: Guantes Motociclismo Táctil Touch Iron Racing Phoenix Azul
Iron Racing, marca líder en accesorios para motocicletas, ofrece productos con altos estándares de calidad, aprobados en laboratorios internacionales para asegurar su efectividad.

Estos guantes no solo son atractivos, sino que también brindan seguridad en tus viajes cortos y largos en tu máquina veloz.

Características:
- Diseño táctil para uso de dispositivos móviles
- Material resistente y duradero
- Protección en nudillos y palma
- Ajuste cómodo y seguro
- Ideal para motociclismo y actividades al aire libre

¡Prepárate para disfrutar de la experiencia Iron Racing!
""".strip()

SYSTEM_PROMPT = f"""Eres redactor profesional de fichas técnicas y descripciones de producto para publicaciones de MercadoLibre especializado en motorefacciones, kits de arrastre, carburadores, suspensiones y accesorios para motocicletas.

Debes escribir descripciones con el MISMO estilo comercial, persuasivo y estructurado de estos ejemplos:

{EJEMPLOS_ESTILO}

REGLAS DE ESTILO A SEGUIR SIEMPRE:
1. Título llamativo en mayúsculas al inicio (nombre del producto + especificación clave o modelos compatibles).
2. Un párrafo de introducción tipo "gancho de venta" (resalta rendimiento, durabilidad y compatibilidad exacta).
3. Sección "Características destacadas:" o "Especificaciones técnicas:" con viñetas (guiones), datos técnicos concretos: materiales (ej. Acero #1045, Plástico ABS), medidas, compatibilidades, tipo de conexión, etc.
4. Sección de "Compatibilidad garantizada:" listando los modelos y marcas de motocicletas compatibles.
5. Recomendaciones de instalación o uso si aplica.
6. Cierre motivador y de confianza comercial (ej. "¡Máximo rendimiento y durabilidad garantizada en cada ruta!").
7. Longitud óptima entre 800 y 1500 caracteres, sin inventar certificaciones que no apliquen.
8. Escribe en español, tono comercial mexicano.
9. Devuelve ÚNICAMENTE el texto final de la descripción, sin encabezados markdown (#), listo para copiar y pegar en MercadoLibre.
10. MUY IMPORTANTE: Tu texto debe EMPEZAR directamente con el título en mayúsculas. No agregues frases como "Aquí está la descripción:", "Con gusto...", etc.
11. MARCA DEL PRODUCTO: La marca de la refacción es SIEMPRE "Genérico". No menciones marcas como "Toptek", "Motoking", "Masuda", "Iron Racing" como fabricante de la pieza en la descripción ni en las viñetas.
"""


def limpiar_descripcion(texto: str) -> str:
    """Elimina preámbulos de IA y asegura que empiece por la línea de título."""
    lineas = texto.strip().split("\n")
    for i, linea in enumerate(lineas):
        candidata = linea.strip()
        letras = [c for c in candidata if c.isalpha()]
        if not letras:
            continue
        proporcion_mayusculas = sum(1 for c in letras if c.isupper()) / len(letras)
        if proporcion_mayusculas > 0.75 and len(candidata) >= 12:
            return "\n".join(lineas[i:]).strip()
    return texto.strip()


class DescriptionGenerator:
    def __init__(self, api_key: Optional[str] = None):
        self.anthropic_key = ANTHROPIC_API_KEY
        self.gemini_key = api_key or GEMINI_API_KEY
        self.claude_client = anthropic.Anthropic(api_key=self.anthropic_key) if self.anthropic_key else None
        self.gemini_client = genai.Client(api_key=self.gemini_key) if self.gemini_key else None

    def generate(
        self,
        sku: str,
        title: str,
        category_name: str,
        technical_attributes: Optional[Dict[str, Any]] = None,
        provider: str = "auto",
    ) -> str:
        """Generates commercial MercadoLibre product description."""
        user_prompt = (
            f"Genera la descripción comercial de Mercado Libre para este producto de la categoría '{category_name}'.\n\n"
            f"SKU: {sku}\n"
            f"Título / Nombre del artículo: {title}\n"
            f"Atributos técnicos identificados: {technical_attributes or {}}\n\n"
            f"Redacta la descripción siguiendo el formato y estilo indicado (título en mayúsculas, gancho comercial, especificaciones técnicas detalladas y compatibilidad de modelos)."
        )

        # Decide provider
        use_claude = (provider == "claude" or (provider == "auto" and self.claude_client is not None))

        if use_claude and self.claude_client:
            try:
                response = self.claude_client.messages.create(
                    model=CLAUDE_MODEL,
                    max_tokens=1500,
                    system=SYSTEM_PROMPT,
                    tools=[{"type": "web_search_20250305", "name": "web_search"}],
                    messages=[{"role": "user", "content": user_prompt}],
                )
                partes_texto = [b.text for b in response.content if getattr(b, "type", None) == "text"]
                texto_completo = "\n".join(partes_texto).strip()
                return limpiar_descripcion(texto_completo)
            except Exception as e:
                print(f"[DescriptionGenerator] Claude failed ({e}), falling back to Gemini.")

        # Gemini Generation with Model Fallback
        if self.gemini_client:
            from google.genai import types
            candidate_models = ["gemini-3.5-flash-lite", "gemini-3.5-flash", GEMINI_MODEL]
            candidate_models = list(dict.fromkeys(candidate_models))

            for model_to_try in candidate_models:
                try:
                    response = self.gemini_client.models.generate_content(
                        model=model_to_try,
                        contents=f"{SYSTEM_PROMPT}\n\n---\n\n{user_prompt}",
                        config=types.GenerateContentConfig(
                            temperature=0.7,
                        ),
                    )
                    return limpiar_descripcion(response.text.strip())
                except Exception as e:
                    err_msg = str(e)
                    if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "503" in err_msg or "NOT_FOUND" in err_msg:
                        continue
                    else:
                        print(f"[DescriptionGenerator] Non-recoverable error on {model_to_try}: {e}")
                        break

        # Fallback template
        return self._build_template_fallback(sku, title, category_name, technical_attributes)

    def _build_template_fallback(
        self,
        sku: str,
        title: str,
        category_name: str,
        tech_attrs: Optional[Dict[str, Any]],
    ) -> str:
        """Generates a structured commercial template if no LLM API is available."""
        tech = tech_attrs or {}
        modelos = ", ".join(tech.get("modelos_compatibles", [])) or "Múltiples modelos compatibles"

        desc = f"{title.upper()}\n\n"
        desc += "¡Optimiza el rendimiento, seguridad y durabilidad de tu motocicleta! Esta refacción está fabricada bajo estrictos estándares de calidad con materiales de alta resistencia, garantizando un ajuste perfecto y máxima vida útil en tus traslados diarios y en carretera.\n\n"
        desc += "** Características destacadas:\n"
        desc += f"- Marca: Genérico\n"
        desc += f"- Número de parte / SKU: {sku}\n"
        
        cat_lower = category_name.lower()
        if "sprocket" in cat_lower or "engrane" in cat_lower:
            desc += f"- Material de corona: Acero\n"
            desc += f"- Material de piñón: Acero\n"
            desc += f"- Relación de dientes: {tech.get('cantidad_dientes_sprocket', 38)}T / {tech.get('cantidad_dientes_pinon', 15)}T\n"
            desc += f"- Paso de cadena: {tech.get('paso_cadena', '428')}\n"
            desc += f"- Cantidad de eslabones: {tech.get('cantidad_eslabones_cadena', 116)}\n"
            desc += f"- Largo de la cadena: {tech.get('largo_cadena', '1473')} mm\n"
        elif "barra" in cat_lower or "suspension" in cat_lower:
            desc += f"- Diámetro del tubo: {tech.get('diametro', 31.0)} mm\n"
            desc += f"- Largo total: {tech.get('largo', 720.0)} mm\n"
            desc += f"- Posición: {tech.get('posicion', 'PAR')}\n"
            desc += f"- Acabado: {tech.get('color', 'Negro')}\n"
        elif "salpicadera" in cat_lower or "plastico" in cat_lower:
            desc += f"- Posición: {tech.get('posicion', 'Delantera')}\n"
            desc += f"- Material: Plástico ABS de alta resistencia\n"
            desc += f"- Color: {tech.get('color', 'Negro')}\n"
            desc += f"- Acabado: {tech.get('acabado', 'Satinado')}\n"
            desc += f"- Altura: {tech.get('altura', 15.0)} cm\n"
            desc += f"- Espesor: {tech.get('espesor', 3.0)} mm\n"
            desc += f"- Cantidad de orificios de montaje: {tech.get('cantidad_agujeros', 4)}\n"
        elif "carburador" in cat_lower:
            desc += f"- Cantidad de bocas: {tech.get('cantidad_de_bocas', '1')}\n"
            desc += f"- Cantidad de cilindros: {tech.get('cantidad_de_cilindros', '1')}\n"
            if tech.get("tipo_carburador"):
                desc += f"- Tipo de carburador: {tech.get('tipo_carburador')}\n"

        desc += "\n** Compatibilidad garantizada:\n"
        desc += f"- Modelos: {modelos}\n\n"
        desc += "¡Máximo rendimiento y ajuste garantizado en cada ruta!"
        return desc
