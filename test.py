import xarray as xr, os
path = "gs://base-era5_low_res/data.zarr"

ds = xr.open_zarr(path, consolidated=True)
print(ds.data_vars.keys())
