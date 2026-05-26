from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
GENERATED_DIR = DATA_DIR / "generated"
OUTPUTS_DIR = ROOT_DIR / "outputs"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

