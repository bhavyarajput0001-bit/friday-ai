import os, json
from pathlib import Path

HOME = Path.home()

ORGANIZED_FOLDERS = {
    "Downloads": HOME / "Downloads",
    "Coding": HOME / "Downloads" / "Coding",
    "Documents": HOME / "Documents",
}

CATEGORY_MAP = {
    ".jpg": "Images", ".jpeg": "Images", ".png": "Images", ".webp": "Images",
    ".avif": "Images", ".gif": "Images", ".svg": "Images", ".bmp": "Images",
    ".mp4": "Videos", ".mov": "Videos", ".mkv": "Videos", ".avi": "Videos",
    ".mp3": "Audio", ".wav": "Audio", ".m4a": "Audio",
    ".pdf": "PDFs",
    ".py": "Code", ".js": "Code", ".ts": "Code", ".cpp": "Code", ".c": "Code",
    ".html": "Code", ".css": "Code", ".sql": "Code", ".json": "Code",
    ".zip": "Archives", ".rar": "Archives", ".dmg": "Archives",
    ".txt": "Text", ".md": "Text",
}

def scan_folder(path, max_depth=2, max_files=500):
    results = {"folders": [], "files": [], "by_category": {}}
    path = Path(path)
    if not path.exists():
        return results
    try:
        items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        for item in items:
            if item.name.startswith("."):
                continue
            if len(results["files"]) >= max_files:
                break
            if item.is_dir():
                if max_depth > 0:
                    sub = scan_folder(item, max_depth - 1, max_files - len(results["files"]))
                    for cat, count in sub["by_category"].items():
                        results["by_category"][cat] = results["by_category"].get(cat, 0) + count
                    results["folders"].append({
                        "name": item.name,
                        "path": str(item.relative_to(HOME)),
                        "sub_folders": sub["folders"][:10],
                        "file_count": len(sub["files"]),
                        "total_items": len(sub["files"]) + len(sub["folders"]),
                    })
            elif item.is_file():
                ext = item.suffix.lower()
                cat = CATEGORY_MAP.get(ext, "Other")
                results["by_category"][cat] = results["by_category"].get(cat, 0) + 1
                results["files"].append({
                    "name": item.name,
                    "path": str(item.relative_to(HOME)),
                    "ext": ext,
                    "size": item.stat().st_size,
                    "category": cat,
                })
    except PermissionError:
        pass
    return results

def get_structure():
    data = {}
    for label, folder_path in ORGANIZED_FOLDERS.items():
        info = scan_folder(folder_path, max_depth=2)
        categories = dict(sorted(info["by_category"].items(), key=lambda x: -x[1]))
        data[label] = {
            "path": str(folder_path.relative_to(HOME)),
            "folders": info["folders"][:15],
            "categories": categories,
            "total_files": sum(info["by_category"].values()),
            "total_folders": len(info["folders"]),
        }
    return data

def get_file_counts():
    counts = {}
    for label, folder_path in ORGANIZED_FOLDERS.items():
        info = scan_folder(folder_path, max_depth=2)
        counts[label.lower()] = {"count": sum(info["by_category"].values()), "label": "Files"}
    coding_path = HOME / "Downloads" / "Coding"
    if coding_path.exists():
        try:
            proj_count = len([d for d in coding_path.iterdir() if d.is_dir() and not d.name.startswith(".")])
        except OSError:
            proj_count = 0
        counts["coding_projects"] = {"count": proj_count, "label": "Projects"}
    return counts
