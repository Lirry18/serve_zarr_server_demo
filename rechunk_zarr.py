import xarray as xr
import gcsfs

def main(src_zarr, dest_zarr):   

    # Open source Zarr via GCS
    ds = xr.open_zarr(src_zarr, consolidated=True)

    # Rechunk
    ds_rechunk = ds.chunk({"init": 1, "point": -1})

    for var in ds_rechunk.data_vars:
        ds_rechunk[var].encoding["chunks"] = ds_rechunk[var].data.chunksize

    # Write to destination Zarr in GCS
    ds_rechunk.to_zarr(store=dest_zarr, mode='w', consolidated=True)
    print(f"Rechunked Zarr written to {dest_zarr}")

if __name__ == "__main__":
    main("gs://scratch_hindcasts_2021-01-02-2021-12-20_n65_daily_aqc2ou/hindcast_aifs_fragrant-sunset-420.zarr", 
         "gs://scratch_hindcasts_2021-01-02-2021-12-20_n65_daily_aqc2ou/hindcast_aifs_fragrant-sunset-420-rechunked.zarr",)
