from dataclasses import dataclass

from app.domain.enums import ProductCategory


@dataclass(frozen=True, slots=True)
class CatalogProduct:
    category: ProductCategory
    manufacturer: str
    canonical_model: str
    variant: str
    attributes: dict[str, object]
    aliases: tuple[tuple[str, frozenset[str], frozenset[str]], ...]


def initial_catalog() -> list[CatalogProduct]:
    return [
        CatalogProduct(ProductCategory.GPU, "NVIDIA", "RTX 3060", "12GB", {"vram_gb": 12}, (("rtx 3060", frozenset({"12gb"}), frozenset({"ti", "8gb"})),)),
        CatalogProduct(ProductCategory.GPU, "AMD", "RX 6700 XT", "12GB", {"vram_gb": 12}, (("rx 6700 xt", frozenset({"12gb"}), frozenset()),)),
        CatalogProduct(ProductCategory.GPU, "NVIDIA", "RTX 4060 Ti", "16GB", {"vram_gb": 16}, (("rtx 4060 ti", frozenset({"ti", "16gb"}), frozenset({"8gb"})),)),
        CatalogProduct(ProductCategory.GPU, "NVIDIA", "RTX 3070", "8GB", {"vram_gb": 8}, (("rtx 3070", frozenset({"8gb"}), frozenset({"ti"})),)),
        CatalogProduct(ProductCategory.CPU, "AMD", "Ryzen 5 5600", "", {"socket": "AM4"}, (("ryzen 5 5600", frozenset({"5600"}), frozenset({"5600g", "5600x"})),)),
        CatalogProduct(ProductCategory.CPU, "AMD", "Ryzen 7 5700X", "", {"socket": "AM4"}, (("ryzen 7 5700x", frozenset({"5700x"}), frozenset()),)),
        CatalogProduct(ProductCategory.CPU, "AMD", "Ryzen 7 5800X", "", {"socket": "AM4"}, (("ryzen 7 5800x", frozenset({"5800x"}), frozenset({"5800x3d"})),)),
        CatalogProduct(ProductCategory.CPU, "Intel", "Core i5-12400F", "", {"socket": "LGA1700"}, (("i5 12400f", frozenset({"12400f"}), frozenset()), ("i5-12400f", frozenset({"12400f"}), frozenset()))),
        CatalogProduct(ProductCategory.MAINBOARD, "Generic", "B550", "ATX", {"socket": "AM4", "form_factor": "ATX"}, (("b550", frozenset({"atx"}), frozenset({"matx", "itx", "mini"})),)),
        CatalogProduct(ProductCategory.MAINBOARD, "Generic", "B550", "Mini-ITX", {"socket": "AM4", "form_factor": "MINI_ITX"}, (("b550", frozenset({"itx"}), frozenset({"matx", "atx"})), ("b550i", frozenset(), frozenset()))),
        CatalogProduct(ProductCategory.RAM, "Generic", "DDR4 Kit", "32GB", {"generation": "DDR4", "capacity_gb": 32, "modules": 2}, (("ddr4", frozenset({"32gb"}), frozenset({"16gb", "64gb"})),)),
        CatalogProduct(ProductCategory.RAM, "Generic", "DDR5 Kit", "32GB 6000", {"generation": "DDR5", "capacity_gb": 32, "speed_mhz": 6000}, (("ddr5", frozenset({"32gb", "6000mhz"}), frozenset({"16gb", "64gb"})),)),
        CatalogProduct(ProductCategory.SSD, "Generic", "NVMe SSD", "1TB PCIe 4.0", {"capacity_tb": 1, "interface": "PCIE_4"}, (("nvme", frozenset({"1tb", "pcie", "4"}), frozenset({"sata"})),)),
    ]
