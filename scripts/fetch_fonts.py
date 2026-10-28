"""Fetch and prepare renderer fonts. Runs at image build."""
from pathlib import Path
from urllib.request import urlretrieve

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

OUT = Path("assets/fonts")
MIRRORS = (
    "https://raw.githubusercontent.com/google/fonts/main/",
    "https://cdn.jsdelivr.net/gh/google/fonts@main/",
)

STATIC = {
    "MrsSaintDelafield-Regular.ttf": "ofl/mrssaintdelafield/MrsSaintDelafield-Regular.ttf",
    "ArchivoBlack-Regular.ttf": "ofl/archivoblack/ArchivoBlack-Regular.ttf",
}
VARIABLE = {
    "RobotoCondensed[wght].ttf": {
        "source": "ofl/robotocondensed/RobotoCondensed%5Bwght%5D.ttf",
        "instances": {
            "RobotoCondensed-Regular.ttf": {"wght": 400},
            "RobotoCondensed-Bold.ttf": {"wght": 700},
        },
    },
}


def fetch(rel: str, dest: Path) -> None:
    err = None
    for mirror in MIRRORS:
        try:
            urlretrieve(mirror + rel, dest)
            print(f"  fetched {rel}")
            return
        except Exception as exc:
            err = exc
    raise RuntimeError(f"could not fetch {rel}: {err}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = OUT / "_tmp"
    tmp.mkdir(exist_ok=True)

    for target, rel in STATIC.items():
        if not (OUT / target).exists():
            fetch(rel, OUT / target)

    for src_name, cfg in VARIABLE.items():
        src = tmp / src_name
        if not src.exists():
            fetch(cfg["source"], src)
        for target, axes in cfg["instances"].items():
            dest = OUT / target
            if dest.exists():
                continue
            font = TTFont(src)
            instantiateVariableFont(font, axes, inplace=True)
            font.save(dest)
            print(f"  built {target} {axes}")

    print("ready:", sorted(p.name for p in OUT.glob("*.ttf")))


if __name__ == "__main__":
    main()
