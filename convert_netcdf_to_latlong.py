import xarray as xr
import xesmf as xe
import numpy as np
from pathlib import Path
from dask.diagnostics import ProgressBar

# 1) Open your source Gaussian‐grid file
src_file = Path("netcdf_from_zarr.nc")
ds = xr.open_dataset(src_file, chunks={})  # no chunks: small file

# Inspect your grid dims & coords
print(ds.dims)      # e.g. ('lat': 64, 'lon': 128)
print(ds.coords)    # should include ds['lat'] and ds['lon']

# 2) Build the source‐grid descriptor for xESMF
# If lat/lon are 1D coords:
if ds['latitude'].ndim == 1 and ds['longitude'].ndim == 1:
    # make a 2D mesh of their values
    LAT2, LON2 = np.meshgrid(ds['latitude'], ds['longitude'], indexing='ij')
    src_grid = xr.Dataset({
        'lat': (('lat','lon'), LAT2),
        'lon': (('lat','lon'), LON2),
    })
else:
    # lat/lon already 2D
    src_grid = xr.Dataset({
        'lat': (ds['lat'].dims, ds['lat'].values),
        'lon': (ds['lon'].dims, ds['lon'].values),
    })

# 3) Define your target regular lat–lon grid
res = 1.0  # degrees; change to 0.5, 2.0, etc.
lat_out = np.arange(  90,  -90 - res,  -res)  # 90→-90
lon_out = np.arange(-180,  180,        res)   # -180→+180

LATo, LONo = np.meshgrid(lat_out, lon_out, indexing='ij')
dst_grid = xr.Dataset({
    'lat': (('lat','lon'), LATo),
    'lon': (('lat','lon'), LONo),
})

# 4) Create (or reuse) the weights
wfile = Path("gaussN32_to_latlon1deg.nc")
if not wfile.exists():
    regridder = xe.Regridder(
        src_grid, dst_grid, method='bilinear',
        filename=str(wfile), reuse_weights=False
    )
else:
    regridder = xe.Regridder(
        src_grid, dst_grid, method='bilinear',
        filename=str(wfile), reuse_weights=True
    )

# 5) Apply it to your variable(s)
# For a single variable:
da = ds['YOUR_VAR_NAME']  # e.g. 't', 'z', etc.
da_ll = regridder(da)

# Restore metadata
da_ll.name = da.name
da_ll.attrs = da.attrs

# 6) Write out to NetCDF with a progress bar
ds_out = da_ll.to_dataset()

with ProgressBar():
    ds_out.to_netcdf("your_gauss_n32_latlon1deg.nc")

print("✅ Done — regridded file is your_gauss_n32_latlon1deg.nc")