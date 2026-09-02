import argparse
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import DATA_DIR, OUTPUT_DIR, PAUSE_BETWEEN_ROWS
from config.categories.registry import registry
from src.excel.reader import ExcelReader
from src.excel.writer import ExcelWriter
from src.processor import ProductProcessor

def main():
    parser = argparse.ArgumentParser(
        description="Pipeline multicategoría para enriquecimiento técnico y catalogación de motorefacciones en Mercado Libre."
    )
    parser.add_argument(
        "archivo",
        nargs="?",
        default="Prueba_Y_2.0.xlsx",
        help="Ruta al archivo Excel con las plantillas de productos (por defecto Prueba_Y_2.0.xlsx).",
    )
    parser.add_argument(
        "--sheet",
        "--hoja",
        default=None,
        help="Nombre de una hoja específica a procesar (ej. 'Carburadores', 'Kits de sprockets', etc.).",
    )
    parser.add_argument(
        "--salida",
        "--output",
        default=None,
        help="Ruta del archivo Excel de salida. Por defecto crea una copia en data/output/.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Límite de productos a procesar por hoja (útil para pruebas rápidas).",
    )
    parser.add_argument(
        "--sku",
        default=None,
        help="Procesar exclusivamente un SKU específico.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Forzar el reprocesamiento de filas que ya tienen descripción o datos llenos.",
    )
    parser.add_argument(
        "--provider",
        default="auto",
        choices=["auto", "gemini", "claude"],
        help="Proveedor de LLM para descripciones (por defecto auto: Claude si hay API key, sino Gemini).",
    )

    args = parser.parse_args()
    input_path = Path(args.archivo)

    if not input_path.exists():
        print(f"Error: El archivo '{input_path}' no existe.")
        sys.exit(1)

    if args.salida:
        output_path = Path(args.salida)
    else:
        output_path = OUTPUT_DIR / f"{input_path.stem}_completado.xlsx"

    print("=" * 70)
    print("MOTOR DE ENRIQUECIMIENTO MULTICATEGORÍA URBANNOVA / TOPTEK")
    print(f"Archivo origen: {input_path}")
    print(f"Archivo destino: {output_path}")
    print("=" * 70)

    reader = ExcelReader(input_path)
    writer = ExcelWriter(input_path, output_path)
    processor = ProductProcessor()

    sheets_to_process = [args.sheet] if args.sheet else reader.sheet_names

    total_procesados = 0
    total_saltados = 0

    for sheet_name in sheets_to_process:
        if sheet_name not in reader.sheet_names:
            print(f"\n[Aviso] La hoja '{sheet_name}' no existe en el libro. Saltando...")
            continue

        print(f"\n>>> Procesando hoja: [{sheet_name}]")
        category_cfg = registry.get_by_sheet(sheet_name)
        if category_cfg:
            print(f"    Schema asociado: {category_cfg.get('schema_name')} | Start Row: {category_cfg.get('start_row', 5)}")
        else:
            print("    [Aviso] Categoría no registrada en config/categories. Usando esquema base.")

        rows = reader.read_sheet(sheet_name, force=args.force)
        if args.sku:
            rows = [r for r in rows if r.sku.lower() == args.sku.lower()]

        if args.limit and args.limit > 0:
            rows = rows[:args.limit]

        print(f"    Total filas detectadas para procesar: {len(rows)}")

        for idx, row in enumerate(rows, 1):
            if row.is_completed and not args.force:
                print(f"  [{idx}/{len(rows)}] Fila {row.row_idx} ({row.sku}): Ya completada. Saltando.")
                total_saltados += 1
                continue

            print(f"  [{idx}/{len(rows)}] Fila {row.row_idx} ({row.sku}): '{row.title}'")
            try:
                updates = processor.process_row(row, llm_provider=args.provider, save_evidence=True)
                writer.update_row(sheet_name, row.row_idx, updates, save_now=True)
                total_procesados += 1
                print(f"       -> OK! Atributos: {list(updates.keys())}")
            except Exception as e:
                print(f"       -> ERROR en fila {row.row_idx}: {e}")

            time.sleep(PAUSE_BETWEEN_ROWS)

    print("\n" + "=" * 70)
    print(f"PROCESO TERMINADO CON ÉXITO")
    print(f"Productos procesados y enriquecidos: {total_procesados}")
    print(f"Productos saltados (ya completos): {total_saltados}")
    print(f"Resultado guardado en: {output_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
