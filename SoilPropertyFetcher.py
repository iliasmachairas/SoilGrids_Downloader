import os
import struct
import tempfile
import time

from osgeo import gdal, osr

gdal.SetConfigOption("GDAL_HTTP_TIMEOUT", "30")

# SoilGrids rasters are served in Interrupted Goode Homolosine, not WGS84.
# This is ISRIC's documented proj4 string for that CRS.
_IGH_PROJ4 = "+proj=igh +lat_0=0 +lon_0=0 +x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs"

# d_factor per SoilGrids property (mapped units -> target units), matching
# the values ISRIC's REST API reports in its response metadata.
_D_FACTORS = {
    'nitrogen': 100,
}
_DEFAULT_D_FACTOR = 10

_transform = None
_dataset_cache = {}


def _get_transform():
    global _transform
    if _transform is None:
        src_srs = osr.SpatialReference()
        src_srs.ImportFromEPSG(4326)
        dst_srs = osr.SpatialReference()
        dst_srs.ImportFromProj4(_IGH_PROJ4)
        _transform = osr.CoordinateTransformation(src_srs, dst_srs)
    return _transform


def _raster_url(property_name, depth, value):
    return (
        f"/vsicurl/https://files.isric.org/soilgrids/latest/data/"
        f"{property_name}/{property_name}_{depth}_{value}.vrt"
    )


def _get_dataset(property_name, depth, value):
    key = (property_name, depth, value)
    ds = _dataset_cache.get(key)
    if ds is None:
        ds = gdal.Open(_raster_url(property_name, depth, value))
        if ds is None:
            raise Exception(f"Could not open SoilGrids raster for '{property_name}'")
        _dataset_cache[key] = ds
    return ds


def download_property_raster(property_name, bbox, output_path, depth="5-15cm", value="mean"):
    """Clip a SoilGrids property to `bbox` (xmin, ymin, xmax, ymax in EPSG:4326)
    and save it as a standard EPSG:4326 GeoTIFF at `output_path`.

    Clipping happens in two steps: first a windowed read straight out of the
    remote Homolosine COG (cheap - only the bytes covering the bbox travel
    over the network), then a local reprojection to EPSG:4326 so the result
    opens with the CRS most tools expect.
    """
    xmin, ymin, xmax, ymax = bbox
    url = _raster_url(property_name, depth, value)

    clip_fd, clip_path = tempfile.mkstemp(suffix=".tif")
    os.close(clip_fd)
    try:
        clipped = gdal.Translate(
            clip_path, url,
            projWin=[xmin, ymax, xmax, ymin],
            projWinSRS="EPSG:4326",
        )
        if clipped is None:
            raise Exception(f"Failed to clip raster for '{property_name}'")
        clipped = None  # flush to disk

        warped = gdal.Warp(output_path, clip_path, dstSRS="EPSG:4326")
        if warped is None:
            raise Exception(f"Failed to reproject raster for '{property_name}'")
        warped = None
    finally:
        if os.path.exists(clip_path):
            os.remove(clip_path)


class SoilPropertyFetcher:
    def __init__(self, lat, lon):
        self.lat = lat
        self.lon = lon

    def fetch_properties(self, properties, depth="5-15cm", value="mean", retries=3, backoff_factor=2):
        """Sample SoilGrids properties at (self.lat, self.lon) directly from
        ISRIC's cloud-optimized rasters via GDAL's /vsicurl/, instead of the
        rate-limited REST API. Only the pixel(s) touched are downloaded.
        """
        results = {}
        transform = _get_transform()
        x, y, _ = transform.TransformPoint(self.lat, self.lon)

        for property_name in properties:
            for attempt in range(retries):
                try:
                    ds = _get_dataset(property_name, depth, value)
                    gt = ds.GetGeoTransform()
                    px = int((x - gt[0]) / gt[1])
                    py = int((y - gt[3]) / gt[5])

                    if px < 0 or py < 0 or px >= ds.RasterXSize or py >= ds.RasterYSize:
                        results[property_name] = None
                        break

                    band = ds.GetRasterBand(1)
                    nodata = band.GetNoDataValue()
                    raw = band.ReadRaster(px, py, 1, 1, buf_type=gdal.GDT_Int16)
                    (raw_value,) = struct.unpack("h", raw)

                    if nodata is not None and raw_value == nodata:
                        results[property_name] = None
                    else:
                        d_factor = _D_FACTORS.get(property_name, _DEFAULT_D_FACTOR)
                        results[property_name] = raw_value / d_factor
                    break

                except Exception as e:
                    if attempt == retries - 1:
                        raise Exception(f"Error fetching '{property_name}': {e}")
                    time.sleep(backoff_factor ** attempt)

        return results
