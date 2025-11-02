#!/usr/bin/env python3
"""
Rasterize a city boundary GeoJSON to a binary mask.

Outputs:
  - <out_prefix>.npy  (H x W, dtype uint8, values {0,1})
  - <out_prefix>.png  or .jpg (grayscale: 0 or 255)
  - <out_prefix>.meta.txt (bounds, CRS, etc.)

Install:
  pip install geopandas shapely pillow numpy pyproj

Usage:
  python rasterize_mask.py --input berlin_boundary.geojson --width 256 --height 256 --out-prefix berlin_mask --format png --project-utm
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
from shapely.prepared import prep
from PIL import Image

def parse_args():
    p = argparse.ArgumentParser(description="Rasterize a GeoJSON polygon boundary into a binary mask.")
    p.add_argument("--input", required=True, help="Path to GeoJSON containing a city boundary polygon.")
    p.add_argument("--out-prefix", default="mask", help="Output prefix (default: mask)")
    p.add_argument("--width", type=int, default=50, help="Output raster width in pixels (default: 50)")
    p.add_argument("--height", type=int, default=50, help="Output raster height in pixels (default: 50)")
    p.add_argument("--format", choices=["png", "jpg", "jpeg"], default="png", help="Output image format (default: png)")
    p.add_argument("--project-utm", action="store_true",
                   help="Reproject to estimated local UTM for uniform meters-per-pixel before rasterizing.")
    p.add_argument("--invert", action="store_true",
                   help="Invert mask values (inside=0, outside=1). Default is inside=1.")
    return p.parse_args()

def load_polygon(geojson_path: str) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(geojson_path)
    if gdf.empty:
        raise ValueError("No geometry found in the GeoJSON.")
    # Dissolve to a single polygon/multipolygon if multiple parts exist
    geom = gdf.unary_union
    out = gpd.GeoDataFrame(geometry=[geom], crs=gdf.crs)
    if out.crs is None:
        # Assume WGS84 if CRS is missing (common for simple GeoJSON)
        out.set_crs("EPSG:4326", inplace=True)
    return out

def maybe_project_to_utm(gdf: gpd.GeoDataFrame, use_utm: bool) -> gpd.GeoDataFrame:
    if not use_utm:
        return gdf
    try:
        utm_crs = gdf.estimate_utm_crs()
        return gdf.to_crs(utm_crs)
    except Exception as e:
        print(f"[warn] Could not project to UTM automatically: {e}\nProceeding in original CRS.", file=sys.stderr)
        return gdf

def grid_sample_points(bounds, width, height):
    minx, miny, maxx, maxy = bounds
    # pixel centers
    xs = np.linspace(minx, maxx, num=width, endpoint=False) + (maxx - minx) / (2 * width)
    ys = np.linspace(miny, maxy, num=height, endpoint=False) + (maxy - miny) / (2 * height)
    # Note: row 0 corresponds to top (max y). We'll flip ys so top row is North.
    ys_top_to_bottom = ys[::-1]
    return xs, ys_top_to_bottom

def rasterize_vectorized(poly, xs, ys):
    """
    Fast path using Shapely 2.x vectorized contains if available.
    Fallback to loop with prepared geometry otherwise.
    """
    # Try Shapely vectorized API
    try:
        from shapely import vectorized  # Shapely>=2.0
        # Build meshgrid of coordinates
        X, Y = np.meshgrid(xs, ys)  # shapes (H, W)
        mask_bool = vectorized.contains(poly, X, Y)  # boolean mask
        return mask_bool.astype(np.uint8)
    except Exception:
        # Fallback: prepared geometry + python loops (fine for small rasters)
        prepared = prep(poly)
        H, W = len(ys), len(xs)
        mask = np.zeros((H, W), dtype=np.uint8)
        for i, y in enumerate(ys):
            for j, x in enumerate(xs):
                if prepared.contains_xy(x, y):
                    mask[i, j] = 1
        return mask

def ensure_polygon(geom):
    if isinstance(geom, (Polygon, MultiPolygon)):
        return geom
    # If it's something else (e.g., GeometryCollection), extract polygonal part
    try:
        polys = [g for g in geom.geoms if isinstance(g, (Polygon, MultiPolygon))]
        if not polys:
            raise ValueError("No polygonal geometry found.")
        return MultiPolygon([p for g in polys for p in (g.geoms if isinstance(g, MultiPolygon) else [g])])
    except AttributeError:
        raise ValueError("Unsupported geometry type for rasterization.")

def save_outputs(mask01: np.ndarray, out_prefix: str, img_format: str, crs_wkt: str, bounds, width, height, src_path: str):
    # 1) NumPy 0/1
    npy_path = f"{out_prefix}.npy"
    np.save(npy_path, mask01.astype(np.uint8))

    # 2) Image: scale to 0/255 and save as PNG/JPEG (grayscale 'L')
    img = (mask01 * 255).astype(np.uint8)
    image = Image.fromarray(img, mode="L")
    img_ext = "jpg" if img_format == "jpeg" else img_format
    img_path = f"{out_prefix}.{img_ext}"
    # For JPEG, set high quality to minimize artifacts (still lossy)
    if img_ext in ("jpg", "jpeg"):
        image.save(img_path, quality=95, subsampling=0, optimize=True)
    else:
        image.save(img_path, optimize=True)

    # 3) Metadata
    meta = {
        "source_geojson": str(Path(src_path).resolve()),
        "output_npy": str(Path(npy_path).resolve()),
        "output_image": str(Path(img_path).resolve()),
        "image_format": img_ext,
        "height": int(height),
        "width": int(width),
        "bounds": {"minx": bounds[0], "miny": bounds[1], "maxx": bounds[2], "maxy": bounds[3]},
        "crs_wkt": crs_wkt,
        "inside_value": 1,
        "outside_value": 0,
        "orientation": "row 0 is North (top), col 0 is West (left)"
    }
    meta_path = f"{out_prefix}.meta.txt"
    with open(meta_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(meta, indent=2))

    print(f"[ok] Saved: {npy_path}")
    print(f"[ok] Saved: {img_path}")
    print(f"[ok] Saved: {meta_path}")

def main():
    args = parse_args()

    gdf = load_polygon(args.input)
    gdf = maybe_project_to_utm(gdf, args.project_utm)

    geom = ensure_polygon(gdf.geometry.iloc[0])

    bounds = geom.bounds  # (minx, miny, maxx, maxy)
    xs, ys = grid_sample_points(bounds, args.width, args.height)

    # Rasterize
    mask01 = rasterize_vectorized(geom, xs, ys)  # uint8 {0,1}

    if args.invert:
        mask01 = 1 - mask01

    # Save
    crs_wkt = gdf.crs.to_wkt() if gdf.crs is not None else "UNKNOWN"
    save_outputs(mask01, args.out_prefix, args.format, crs_wkt, bounds, args.width, args.height, args.input)

if __name__ == "__main__":
    main()


