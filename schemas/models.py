from typing import List, Optional, Dict, Any, Type
from pydantic import BaseModel, Field

class BaseProductAttributes(BaseModel):
    """Atributos base comunes a todas las motorefacciones."""
    marca: str = Field(default="Genérico", description="Marca comercial del producto (siempre 'Genérico' para evitar infracciones de marca en Mercado Libre).")
    numero_de_parte: str = Field(description="SKU o código de parte del producto.")
    numero_de_pedimento: str = Field(default="N/A", description="Número de pedimento aduanal, siempre N/A.")
    origen: str = Field(default="China", description="País de origen del producto.")
    modelos_compatibles: List[str] = Field(default_factory=list, description="Lista exhaustiva de TODOS los modelos de motos compatibles señalados en el título/input de entrada sin omitir ninguno.")
    resumen_tecnico: Optional[str] = Field(default=None, description="Resumen conciso de especificaciones técnicas.")


class CarburadorAttributes(BaseProductAttributes):
    """Atributos específicos para la categoría Carburadores."""
    marca: str = Field(default="Genérico", description="Marca comercial: 'Genérico'.")
    modelo: str = Field(
        description=(
            "TODOS los modelos de motocicletas compatibles señalados en el título/input de entrada, "
            "separados por ' / ' (ej: 'FT150 / 150SZ / 150Z / 170Z / DM150 / CYCLONE / LITHIUM / ROCKETMAN / STORM / V-RACER'). "
            "REGLA OBLIGATORIA: Debes incluir exhaustivamente TODOS y cada uno de los modelos de motocicletas compatibles indicados en el título original sin omitir ninguno ni resumir. "
            "NUNCA colocar aquí el código o tipo de carburador (como PZ19, PZ26, PZ27, PZ30, CVK); ese código va exclusivamente en 'tipo_carburador'. "
            "Si el título no incluye nombres de modelos específicos sino rangos de cilindrada (ej: 'ITALIKA / DINAMO 70CC / 90CC'), indica las cilindradas o aplicaciones (ej: '70cc / 90cc')."
        )
    )
    cantidad_de_bocas: str = Field(default="1", description="Cantidad de bocas del carburador, típicamente '1'.")
    cantidad_de_cilindros: str = Field(default="1", description="Cantidad de cilindros para los que está diseñado ('1' para monocilíndricas).")
    tipo_carburador: Optional[str] = Field(default=None, description="Código estándar (ej: PZ19, PZ26, PZ27, PZ30, CVK).")
    cilindrada_cc: Optional[int] = Field(default=None, description="Cilindrada en cc del motor compatible (70, 90, 110, 125, 150, 200, 250).")


class SprocketAttributes(BaseProductAttributes):
    """Atributos específicos para la categoría Kits de sprockets (Kits de arrastre)."""
    marca: str = Field(default="Genérico", description="Marca comercial: 'Genérico'.")
    material_del_sprocket: str = Field(default="Acero", description="Material del sprocket/corona: 'Acero'.")
    material_del_pinon: str = Field(default="Acero", description="Material del piñón delantero: 'Acero'.")
    cantidad_dientes_sprocket: int = Field(description="Número de dientes de la corona trasera (ej. 38, 40, 41, 42, 45, 54).")
    cantidad_dientes_pinon: int = Field(description="Número de dientes del piñón delantero (ej. 14, 15, 16, 17).")
    largo_cadena: str = Field(default="1473", description="Largo total de la cadena en milímetros calculado según el número de eslabones y paso (ej. 1370, 1473, 1524, 1625, 1746).")
    unidad_largo_cadena: str = Field(default="mm", description="Unidad de medida del largo de cadena: 'mm'.")
    cantidad_eslabones_cadena: int = Field(default=116, description="Cantidad total de eslabones de la cadena (ej. 108, 116, 120, 122, 128, 132).")
    paso_cadena: Optional[str] = Field(default="428", description="Paso estándar de la cadena (420, 428, 520).")
    estilo_conduccion: str = Field(default="Calle", description="Estilo de conducción (Calle, Deportivo, Adventure/Custom).")


class BarrasSuspensionAttributes(BaseProductAttributes):
    """Atributos específicos para la categoría Barras de suspensión (Telescópicas / Amortiguadores delanteros)."""
    marca: str = Field(default="Genérico", description="Marca comercial: 'Genérico'.")
    diametro: float = Field(description="Diámetro nominal exterior del tubo de la barra en mm según el modelo de moto (ej. 26.0, 30.0, 31.0, 33.0, 37.0, 41.0).")
    unidad_diametro: str = Field(default="mm", description="Unidad del diámetro: 'mm'.")
    largo: float = Field(description="Largo total de la barra de suspensión en mm según el modelo de moto (ej. 610.0, 645.0, 710.0, 730.0, 750.0, 830.0).")
    unidad_largo: str = Field(default="mm", description="Unidad del largo: 'mm'.")
    posicion: Optional[str] = Field(default="PAR", description="Posición o presentación: PAR, DERECHO (DER.), IZQUIERDO (IZQ.).")
    color: Optional[str] = Field(default="NEGRO", description="Color o acabado exterior (NEGRO, GRIS, CROMO, PLATA).")


class SalpicaderaAttributes(BaseProductAttributes):
    """Atributos específicos para la categoría Salpicaderas (Guardabarros / Salpicaderos)."""
    marca: str = Field(default="Genérico", description="Marca comercial: 'Genérico'.")
    modelo: str = Field(
        description=(
            "TODOS los modelos de motocicleta compatibles señalados en el título/input de entrada, "
            "separados por ' / ' (ej: 'FZ-S / FZ 2.0', 'Pulsar 200NS', 'AXUS150 / AXUS170', 'LITHIUM / RYDER / THRILLER / THUNDER / WORKMAN / XPLOR'). "
            "REGLA OBLIGATORIA: Debes incluir exhaustivamente TODOS y cada uno de los modelos de motos compatibles indicados en el título original sin omitir ninguno ni resumir la lista."
        )
    )
    color: str = Field(default="Negro", description="Color del producto (Negro, Gris, Rojo, Azul, Blanco, etc.).")
    acabado: str = Field(default="Satinado", description="Acabado superficial: 'Satinado', 'Mate' o 'Natural'.")
    posicion: str = Field(default="Delantera", description="Posición en la moto ('Delantera' o 'Trasera').")
    altura: float = Field(default=15.0, description="Altura de la salpicadera en cm (ej. 15.0 para delantera, 18.0 para trasera).")
    unidad_altura: str = Field(default="cm", description="Unidad de medida de la altura: 'cm'.")
    incluye_herrajes: str = Field(default="No", description="Indica si incluye tornillería/herrajes de montaje: 'No'.")
    cantidad_agujeros: int = Field(default=4, description="Cantidad de orificios de montaje (típicamente 4 para delanteras, 2 o 4 para traseras).")
    material: str = Field(default="Plástico ABS", description="Material de fabricación: 'Plástico ABS' o 'Plástico'.")
    espesor: float = Field(default=3.0, description="Espesor del material en mm (típicamente 3.0 o 3.5 mm).")
    unidad_espesor: str = Field(default="mm", description="Unidad del espesor: 'mm'.")


# Registro central de esquemas
SCHEMA_REGISTRY: Dict[str, Type[BaseProductAttributes]] = {
    "CarburadorAttributes": CarburadorAttributes,
    "SprocketAttributes": SprocketAttributes,
    "BarrasSuspensionAttributes": BarrasSuspensionAttributes,
    "SalpicaderaAttributes": SalpicaderaAttributes,
}

def get_schema_by_name(name: str) -> Optional[Type[BaseProductAttributes]]:
    return SCHEMA_REGISTRY.get(name)
