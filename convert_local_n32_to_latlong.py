import numpy as np
import xarray as xr
import xesmf as xe
from pathlib import Path
from dask.diagnostics import ProgressBar
from gaussian_regridder import GaussianToLatLonRegridder

# ── 1. Open your source Zarr lazily ───────────────────────────────────────
SRC = Path("hindcast_raw_tiny.zarr")
ds  = xr.open_zarr(
    SRC,
    chunks={"lead": 1, "member": 1, "point": 22304},  # keep point intact
    consolidated=True
)

regridder = GaussianToLatLonRegridder(grid_res=2.8)

da_ll = regridder.regrid(ds)




# da = ds["geopotential"]  # dims (lead, member, point), dtype float32, dask-backed

# # ── 2. Build the target lat–lon grid ─────────────────────────────────────
# nlat, nlon = 361, 720
# lat1d     = np.linspace(  90,  -90, nlat)
# lon1d     = np.linspace(-180,  180, nlon, endpoint=False)
# lat_coarse = lat1d[::2]     # length 181
# lon_coarse = lon1d[::2]     # length 360
# LAT2D, LON2D = np.broadcast_arrays(lat_coarse[:,None], lon_coarse[None,:])

# print('destination grid..')
# dst_grid = xr.Dataset({
#     "lat": (("lat","lon"), LAT2D),
#     "lon": (("lat","lon"), LON2D),
# })
# print('destination grid done')

# # ── 3. Build the unstructured source–grid spec ────────────────────────────
# print('source grid..')
# src_grid = xr.Dataset({
#     "lat": (("point",), ds.latitude.values),
#     "lon": (("point",), ds.longitude.values),
# })
# print('source grid done')

# # ── 4. Make or load bilinear weights ─────────────────────────────────────
# print('weights')
# WEI = Path("weights_point2latlon_bilin.nc")
# if not WEI.exists():
#     print('weights werent there')
#     regridder = xe.Regridder(
#         src_grid, dst_grid, method="bilinear",
#         filename=str(WEI), reuse_weights=False
#     )
# else:
#     print('weights were there')
#     regridder = xe.Regridder(
#         src_grid, dst_grid, method="bilinear",
#         filename=str(WEI), reuse_weights=True
#     )
# print('weights done')

# # ── 5. Regrid the entire dask array ───────────────────────────────────────
# # This returns a new DataArray of shape (lead, member, lat, lon),
# # still backed by dask, so it stays lazy:
# da_ll = regridder(da)

# restore name & units
da_ll.name = "geopotential"
da_ll.attrs["units"] = ds["geopotential"].attrs.get("units", "")

# wrap it in a Dataset
print('wrapping in dataset')
ds_ll = da_ll.to_dataset()

# ── 6. Write directly to Zarr, chunk by chunk ────────────────────────────
OUT = Path("hindcast_geop_latlon.zarr")
print('writing to zar..')
ds_ll.to_zarr(
    store=OUT,
    mode="w",
    consolidated=True
)
print("✅ Wrote regridded file to", OUT)
