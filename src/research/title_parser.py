import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from config.settings import KNOWLEDGE_DIR

class TitleParser:
    def __init__(self):
        self.knowledge = self._load_knowledge()
        self.known_brands = self.knowledge.get("known_brands", [
            "Italika", "Vento", "Bajaj", "Yamaha", "Honda", "Suzuki", "Dinamo", "MB", "TVS", "Kawasaki", "KTM"
        ])
        self.suspension_kb = self.knowledge.get("suspension_knowledge", {})
        self.sprockets_kb = self.knowledge.get("sprockets_knowledge", {})
        self.fenders_kb = self.knowledge.get("fenders_knowledge", {})

    def _load_knowledge(self) -> Dict[str, Any]:
        kb_path = KNOWLEDGE_DIR / "motorcycles.json"
        if kb_path.exists():
            try:
                with open(kb_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def extract_motorcycle_brands(self, title: str) -> List[str]:
        """Detects mentioned motorcycle brands (e.g. Italika, Vento, Bajaj)."""
        found = []
        for brand in self.known_brands:
            pattern = rf"\b{re.escape(brand)}\b"
            if re.search(pattern, title, re.IGNORECASE):
                found.append(brand)
        return found

    def extract_displacement(self, title: str) -> Optional[int]:
        """Extracts engine cc from title (e.g., 70CC, 150CC, 200CC)."""
        match = re.search(r"\b(\d{2,3})\s*CC\b", title, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        # Inferred from model numbers (e.g. FT150 -> 150, AT110 -> 110)
        match_model = re.search(r"\b[A-Z]{1,4}(\d{3})\b", title, re.IGNORECASE)
        if match_model:
            cc_candidate = int(match_model.group(1))
            if 50 <= cc_candidate <= 450:
                return cc_candidate
        return None

    def extract_sprocket_specs(self, title: str) -> Dict[str, Any]:
        """Extracts chain pitch, teeth count, chain length, and link count."""
        pattern = r"\b(?P<pitch>420|428|520|525|530)-(?P<sprocket>\d{2,3})T\s*/\s*(?P<pinion>\d{1,2})T\b"
        match = re.search(pattern, title, re.IGNORECASE)
        specs: Dict[str, Any] = {
            "material_del_sprocket": "Acero",
            "material_del_pinon": "Acero",
            "unidad_largo_cadena": "mm",
            "estilo_conduccion": "Calle",
        }

        if match:
            pitch = match.group("pitch")
            sprocket_teeth = int(match.group("sprocket"))
            pinion_teeth = int(match.group("pinion"))
            specs["paso_cadena"] = pitch
            specs["cantidad_dientes_sprocket"] = sprocket_teeth
            specs["cantidad_dientes_pinon"] = pinion_teeth

            # Check exact ratio in knowledge base
            ratio_key = f"{pitch}-{sprocket_teeth}T/{pinion_teeth}T"
            kb_entry = self.sprockets_kb.get(ratio_key)
            if kb_entry:
                specs["cantidad_eslabones_cadena"] = kb_entry.get("links", 116)
                specs["largo_cadena"] = str(kb_entry.get("chain_length_mm", 1473))
            else:
                # Approximate calculation
                links = 108 if pitch == "420" else (128 if sprocket_teeth >= 45 else 116)
                pitch_mm = 12.7 if pitch in ["420", "428"] else 15.875
                specs["cantidad_eslabones_cadena"] = links
                specs["largo_cadena"] = str(int(round(links * pitch_mm)))
        else:
            specs["cantidad_dientes_sprocket"] = 38
            specs["cantidad_dientes_pinon"] = 15
            specs["cantidad_eslabones_cadena"] = 116
            specs["largo_cadena"] = "1473"
            specs["paso_cadena"] = "428"

        return specs

    def extract_suspension_specs(self, title: str) -> Dict[str, Any]:
        """Extracts exact suspension bar specs (position, color, dimensions per motorcycle model)."""
        specs: Dict[str, Any] = {
            "unidad_diametro": "mm",
            "unidad_largo": "mm",
        }

        # Position
        if re.search(r"\b(DER\.\s*/\s*IZQ\.|PAR)\b", title, re.IGNORECASE):
            specs["posicion"] = "PAR"
        elif re.search(r"\b(IZQ\.UIERDO|IZQ\.|IZQUIERDO)\b", title, re.IGNORECASE):
            specs["posicion"] = "IZQUIERDO"
        elif re.search(r"\b(DER\.ECHO|DER\.|DERECHO)\b", title, re.IGNORECASE):
            specs["posicion"] = "DERECHO"
        else:
            specs["posicion"] = "PAR"

        # Color
        for col in ["NEGRO", "GRIS", "CROMO", "PLATA", "DORADO", "AZUL", "ROJO"]:
            if re.search(rf"\b{col}\b", title, re.IGNORECASE):
                specs["color"] = col.capitalize()
                break
        if "color" not in specs:
            specs["color"] = "Negro"

        # Explicit dimensions in title: e.g. 37*50.3*13 or 31*730
        dim_match = re.search(r"\b(\d{2}(?:\.\d+)?)\s*(?:mm|\*|x)\s*(\d{2,3}(?:\.\d+)?)\b", title, re.IGNORECASE)
        if dim_match:
            specs["diametro"] = float(dim_match.group(1))
            specs["largo"] = float(dim_match.group(2))
            return specs

        # Lookup in knowledge base per model name in title
        title_upper = title.upper()
        matched_kb = None

        # Sorted by length of key to match most specific model first
        sorted_keys = sorted(self.suspension_kb.keys(), key=len, reverse=True)
        for model_key in sorted_keys:
            if re.search(rf"\b{re.escape(model_key)}\b", title_upper):
                matched_kb = self.suspension_kb[model_key]
                break

        if matched_kb:
            specs["diametro"] = float(matched_kb.get("diametro", 31.0))
            specs["largo"] = float(matched_kb.get("largo", 720.0))
        else:
            # Fallback by displacement / type heuristic
            if "70" in title_upper or "90" in title_upper or "110" in title_upper:
                specs["diametro"] = 26.0
                specs["largo"] = 645.0
            elif "200" in title_upper or "250" in title_upper:
                specs["diametro"] = 33.0
                specs["largo"] = 750.0
            else:
                specs["diametro"] = 31.0
                specs["largo"] = 720.0

        return specs

    def extract_fender_specs(self, title: str) -> Dict[str, Any]:
        """Extracts complete fender/salpicadera specs (position, color, dimensions, thickness, holes)."""
        pos = "Delantera"
        if re.search(r"\b(TRASERA|TRAS\.)\b", title, re.IGNORECASE):
            pos = "Trasera"
        elif re.search(r"\b(DELANTERA|DEL\.)\b", title, re.IGNORECASE):
            pos = "Delantera"

        color = "Negro"
        for col in ["NEGRO", "GRIS", "ROJO", "AZUL", "BLANCO", "VERDE", "AMARILLO", "CAFÉ", "CELESTE"]:
            if re.search(rf"\b{col}\b", title, re.IGNORECASE):
                color = col.capitalize()
                break

        # Dimensions & mounting hole defaults based on position
        if pos == "Trasera":
            altura = 18.0
            agujeros = 2
            espesor = 3.5
        else:
            altura = 15.0
            agujeros = 4
            espesor = 3.0

        return {
            "posicion": pos,
            "color": color,
            "acabado": "Satinado",
            "material": "Plástico ABS",
            "incluye_herrajes": "No",
            "altura": altura,
            "unidad_altura": "cm",
            "cantidad_agujeros": agujeros,
            "espesor": espesor,
            "unidad_espesor": "mm",
        }

    def extract_compatible_models(self, title: str) -> List[str]:
        """Extracts clean list of model strings (e.g. FT150, 150SZ, DM150, FZ 2.0)."""
        clean_text = title
        remove_terms = [
            r"KIT ENGRANES ACERO #1045",
            r"KIT ENGRANES ACERO",
            r"KIT SPROCKET",
            r"CARBURADOR SCOOTER",
            r"CARBURADOR COMPLETO",
            r"CARBURADOR",
            r"AMORTIGUADOR\s*/\s*BARRA DE SUSPENSION",
            r"BARRA DE SUSPENSION",
            r"TUBO FUERZA DE SUSPENSION DELANTERA",
            r"TAPAS PARA POLVO DE BARRA DE SUSPENCION",
            r"CUBRE-POLVO DE BARRA SUSPENSION",
            r"SALPICADER\.A TRASERA INFERIOR",
            r"SALPICADER\.A TRASERA",
            r"SALPICADER\.A DELANTERA",
            r"SALPICADERA TRASERA",
            r"SALPICADERA DELANTERA",
            r"CUBIERTA FRONTAL",
            r"SALPICADER\.A",
            r"SALPICADERA",
            r"V-ORIGINAL",
            r"MOTOKING",
            r"TOPTEK",
            r"MASUDA",
            r"LINEA REFACCIONES",
            r"DER\.\s*/\s*IZQ\.",
            r"IZQ\.UIERDO",
            r"DER\.ECHO",
            r"NEGRO",
            r"GRIS",
            r"CROMO",
            r"PIEZAS",
            r"PAR",
            r"\d{3}-\d{2}T\s*/\s*\d{2}T",
            r"\d{2,3}CC",
        ]
        for term in remove_terms:
            clean_text = re.sub(term, " ", clean_text, flags=re.IGNORECASE)

        for b in self.known_brands:
            clean_text = re.sub(rf"\b{re.escape(b)}\b", " ", clean_text, flags=re.IGNORECASE)

        raw_parts = re.split(r"[/,]", clean_text)
        models = []
        for p in raw_parts:
            p_clean = re.sub(r"[^\w\s\.-]", "", p).strip()
            if len(p_clean) >= 2 and not p_clean.isdigit():
                models.append(p_clean)

        return models

    def parse(self, title: str, category_name: str, sku: str = "") -> Dict[str, Any]:
        """Main parsing method returning all deterministically extracted features."""
        brands = self.extract_motorcycle_brands(title)
        models = self.extract_compatible_models(title)
        displacement = self.extract_displacement(title)

        parsed: Dict[str, Any] = {
            "marca": "Genérico",
            "moto_brands": brands,
            "models": models,
            "displacement_cc": displacement,
        }

        cat_lower = category_name.lower()
        if "sprocket" in cat_lower or "engrane" in cat_lower:
            parsed.update(self.extract_sprocket_specs(title))
        elif "barra" in cat_lower or "suspension" in cat_lower:
            parsed.update(self.extract_suspension_specs(title))
        elif "salpicadera" in cat_lower or "plastico" in cat_lower:
            parsed.update(self.extract_fender_specs(title))

        return parsed