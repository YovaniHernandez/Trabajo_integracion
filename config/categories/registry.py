import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from config.settings import CATEGORIES_DIR

class CategoryRegistry:
    def __init__(self, categories_dir: Path = CATEGORIES_DIR):
        self.categories_dir = categories_dir
        self._categories: Dict[str, Dict[str, Any]] = {}
        self._sheet_to_category: Dict[str, str] = {}
        self.load_all()

    def load_all(self):
        """Loads all YAML category definitions from the config/categories directory."""
        for file_path in self.categories_dir.glob("*.yaml"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if data and "name" in data:
                        cat_name = data["name"]
                        self._categories[cat_name] = data
                        if "sheet_name" in data:
                            self._sheet_to_category[data["sheet_name"].strip().lower()] = cat_name
                            self._sheet_to_category[data["sheet_name"].strip()] = cat_name
            except Exception as e:
                print(f"[CategoryRegistry] Error loading {file_path}: {e}")

    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        return self._categories.get(name)

    def get_by_sheet(self, sheet_name: str) -> Optional[Dict[str, Any]]:
        sheet_key = sheet_name.strip()
        cat_name = self._sheet_to_category.get(sheet_key) or self._sheet_to_category.get(sheet_key.lower())
        if cat_name:
            return self._categories.get(cat_name)
        return None

    def list_categories(self) -> Dict[str, Dict[str, Any]]:
        return self._categories

registry = CategoryRegistry()
