import json
from pathlib import Path
from typing import Dict, Any, Optional

from config.settings import RESEARCH_DIR, GEMINI_API_KEY
from config.categories.registry import registry
from src.excel.reader import ProductRow
from src.research.title_parser import TitleParser
from src.research.search_engine import SearchEngine
from src.research.gemini_enricher import GeminiEnricher
from src.generators.description_generator import DescriptionGenerator

class ProductProcessor:
    def __init__(self, api_key: str = GEMINI_API_KEY):
        self.parser = TitleParser()
        self.search_engine = SearchEngine()
        self.gemini_enricher = GeminiEnricher(api_key=api_key)
        self.desc_generator = DescriptionGenerator(api_key=api_key)

    def process_row(
        self,
        row: ProductRow,
        llm_provider: str = "gemini",
        save_evidence: bool = True,
    ) -> Dict[str, Any]:
        """
        Processes a single ProductRow:
        1. Parse title with deterministic regex/NLP
        2. Search DuckDuckGo if additional specs are needed
        3. Enrich structured attributes with Gemini
        4. Generate commercial Mercado Libre description
        5. Map attributes to sheet-specific columns
        6. Persist research evidence JSON
        """
        category_cfg = registry.get_by_sheet(row.sheet_name)
        if not category_cfg:
            category_cfg = registry.get_base_config()

        schema_name = category_cfg.get("schema_name", "BaseProductAttributes")
        defaults = category_cfg.get("defaults", {})
        col_mapping = category_cfg.get("column_mapping", {})

        # Step 1: Parse Title with Regex / NLP
        parsed_clues = self.parser.parse(row.title, row.sheet_name, row.sku)

        # Step 2: Search Web if necessary
        search_template = category_cfg.get("search_query_template", "{title}")
        search_query = search_template.format(title=row.title)
        search_snippets = self.search_engine.search(search_query, max_results=3)

        # Step 3: Enrich technical attributes with Gemini
        tech_attributes = self.gemini_enricher.enrich_product(
            sku=row.sku,
            title=row.title,
            category_name=row.sheet_name,
            schema_name=schema_name,
            parsed_clues=parsed_clues,
            search_snippets=search_snippets,
            category_defaults=defaults,
        )

        # Step 4: Generate commercial description
        description = self.desc_generator.generate(
            sku=row.sku,
            title=row.title,
            category_name=row.sheet_name,
            technical_attributes=tech_attributes,
            provider=llm_provider,
        )

        # Step 5: Map enriched attributes to Excel column updates
        excel_updates: Dict[str, Any] = {}
        for attr_key, col_header in col_mapping.items():
            if attr_key == "descripcion_comercial":
                excel_updates[col_header] = description
                continue

            # Prioritize tech_attributes -> parsed_clues -> defaults
            val = None
            if attr_key in tech_attributes and tech_attributes[attr_key] is not None:
                val = tech_attributes[attr_key]
            elif attr_key in parsed_clues and parsed_clues[attr_key] is not None:
                val = parsed_clues[attr_key]
            elif col_header in defaults:
                val = defaults[col_header]

            if isinstance(val, list):
                val = " / ".join(str(x) for x in val)

            excel_updates[col_header] = val

        # Mandatory Business Rules & Guarantees across all products:
        
        # Rule 1: Marca is ALWAYS "Genérico"
        excel_updates["Marca"] = "Genérico"

        # Rule 2: Número de parte is row.sku
        if "Número de parte" in excel_updates or "Número de parte" in col_mapping.values():
            excel_updates["Número de parte"] = row.sku

        # Rule 3: Apply any missing category defaults
        for def_k, def_v in defaults.items():
            if def_k not in excel_updates or excel_updates[def_k] is None or excel_updates[def_k] == "":
                excel_updates[def_k] = def_v

        # Category-Specific Complete Guarantees:
        cat_lower = row.sheet_name.lower()
        
        # Salpicaderas: Guaranteed Altura, Espesor, Agujeros, Material, Acabado
        if "salpicadera" in cat_lower or "plastico" in cat_lower:
            pos = parsed_clues.get("posicion", "Delantera")
            if "trasera" in row.title.lower() or "tras." in row.title.lower():
                pos = "Trasera"
            
            if not excel_updates.get("Altura") or excel_updates.get("Altura") == "":
                excel_updates["Altura"] = 18 if pos == "Trasera" else 15
            excel_updates["Unidad de Altura"] = "cm"

            if not excel_updates.get("Espesor") or excel_updates.get("Espesor") == "":
                excel_updates["Espesor"] = 3.5 if pos == "Trasera" else 3
            excel_updates["Unidad de Espesor"] = "mm"

            if not excel_updates.get("Cantidad de agujeros de montaje") or excel_updates.get("Cantidad de agujeros de montaje") == "":
                excel_updates["Cantidad de agujeros de montaje"] = 2 if pos == "Trasera" else 4

            if not excel_updates.get("Material") or excel_updates.get("Material") == "":
                excel_updates["Material"] = "Plástico ABS"
            if not excel_updates.get("Acabado") or excel_updates.get("Acabado") == "":
                excel_updates["Acabado"] = "Satinado"
            if not excel_updates.get("Incluye herrajes de montaje") or excel_updates.get("Incluye herrajes de montaje") == "":
                excel_updates["Incluye herrajes de montaje"] = "No"

        # Kits de sprockets: Guaranteed Material = Acero, Largo de cadena in mm
        elif "sprocket" in cat_lower or "engrane" in cat_lower:
            excel_updates["Material del sprocket"] = "Acero"
            excel_updates["Material del piñón"] = "Acero"
            if not excel_updates.get("Largo de la cadena") or excel_updates.get("Largo de la cadena") == "":
                excel_updates["Largo de la cadena"] = str(parsed_clues.get("largo_cadena", "1473"))
            excel_updates["Unidad de Largo de la cadena"] = "mm"

        # Barras de suspensión: Guaranteed Diámetro, Largo, Unidades
        elif "barra" in cat_lower or "suspension" in cat_lower:
            if not excel_updates.get("Diámetro") or excel_updates.get("Diámetro") == "":
                excel_updates["Diámetro"] = parsed_clues.get("diametro", 31.0)
            excel_updates["Unidad de Diámetro"] = "mm"

            if not excel_updates.get("Largo") or excel_updates.get("Largo") == "":
                excel_updates["Largo"] = parsed_clues.get("largo", 720.0)
            excel_updates["Unidad de Largo"] = "mm"

        # Step 6: Save Evidence JSON
        if save_evidence:
            cat_research_dir = RESEARCH_DIR / row.sheet_name.replace(" ", "_").lower()
            cat_research_dir.mkdir(parents=True, exist_ok=True)
            safe_sku = "".join(c for c in row.sku if c.isalnum() or c in ("-", "_")) or "item"
            evidence_file = cat_research_dir / f"{safe_sku}.json"

            evidence = {
                "sku": row.sku,
                "title": row.title,
                "sheet": row.sheet_name,
                "parsed_clues": parsed_clues,
                "search_query": search_query,
                "search_snippets": search_snippets,
                "technical_attributes": tech_attributes,
                "description": description,
                "excel_updates": excel_updates,
            }
            with open(evidence_file, "w", encoding="utf-8") as f:
                json.dump(evidence, f, ensure_ascii=False, indent=2)

        return excel_updates
