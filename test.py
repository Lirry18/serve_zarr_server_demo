import fsspec, xarray as xr

bucket = "hindcasts_2021-01-02-2021-12-20_n65_daily_aqc2ou"
# fs = fsspec.filesystem("gcs", token="gcloud")          # expliciet ADC

zarr_path = f"gs://{bucket}/hindcast_aifs_fragrant-sunset-420.zarr/"
ds = xr.open_zarr(
    zarr_path,
    chunks="auto",
    consolidated=True,
)
print(ds)