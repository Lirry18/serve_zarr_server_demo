#!/usr/bin/env python3
import icechunk
import icechunk.xarray as ixr
import xarray as xr

# ─── CONFIG ────────────────────────────────────────────────────────────
# This must be EXACTLY your GCS bucket name, no ellipsis or abbreviation:
GCP_BUCKET = "scratch_hindcasts_2021-01-02-2021-12-20_n65_daily_aqc2ou"

# The prefix (folder) under which Icechunk will live:
ICE_PREFIX = "icechunk/fragrant-sunset/"

# The *exact* Zarr folder (in that bucket) you want to ingest:
SRC_ZARR = "hindcast_aifs_fragrant-sunset-420.zarr"
# ────────────────────────────────────────────────────────────────────────

def main():
    # 1) Build the Icechunk storage handle (just points at gs://<bucket>/<prefix>/)
    storage = icechunk.gcs_storage(
        bucket=GCP_BUCKET,
        prefix=ICE_PREFIX,
        from_env=True          # picks up GOOGLE_APPLICATION_CREDENTIALS
    )

    # 2) Open it if it exists, or create it if it doesn’t
    repo = icechunk.Repository.open_or_create(storage)
    print("→ Icechunk repo ready at gs://%s/%s" % (GCP_BUCKET, ICE_PREFIX))

    # 3) Start a write session on 'main'
    session = repo.writable_session("main")
    store   = session.store   # this is now a Zarr‐compatible store

    # 4) Load *only* the fragrant-sunset Zarr via xarray
    src_url = f"gs://{GCP_BUCKET}/{SRC_ZARR}"
    print("→ Loading source Zarr:", src_url)
    ds = xr.open_zarr(src_url, consolidated=True)
    ds_rechunk = ds.chunk({"init": 1, "point": -1})

    for var in ds_rechunk.data_vars:
        ds_rechunk[var].encoding["chunks"] = ds_rechunk[var].data.chunksize

    # 5) Write it into Icechunk (root of the repo)
    print("→ Writing data into Icechunk store…")
    ixr.to_icechunk(ds_rechunk, session)

    # 6) Commit all changes atomically
    snap_id = session.commit("Import fragrant-sunset hindcast Zarr")
    print("✅ Committed snapshot ID:", snap_id)

if __name__ == "__main__":
    main()
