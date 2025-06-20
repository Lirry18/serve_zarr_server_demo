import time
import xarray as xr
import icechunk

# ─── CONFIG ───────────────────────────────────────────────────────────
# Fill these in with your real bucket & prefix
BUCKET      = "scratch_hindcasts_2021-01-02-2021-12-20_n65_daily_aqc2ou"
ICE_PREFIX  = "icechunk/fragrant-sunset/"  # where you ingested the Zarr
PLAIN_ZARR  = f"gs://{BUCKET}/hindcast_aifs_fragrant-sunset-420-rechunked.zarr"
# ────────────────────────────────────────────────────────────────────────

# prepare Icechunk store
storage = icechunk.gcs_storage(bucket=BUCKET, prefix=ICE_PREFIX, from_env=True)
repo    = icechunk.Repository.open(storage)   # or open_or_create
session = repo.readonly_session(branch="main")
ice_store = session.store

def time_open_and_slice(path_or_store, consolidated, repeats=3):
    times = []
    for _ in range(repeats):
        start = time.perf_counter()
        ds = xr.open_zarr(path_or_store, consolidated=consolidated, decode_timedelta=False)
        ds.isel(init=0).load()    # load the first 1 MB “init” into memory
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        del ds
    return times

def time_open(path_or_store, consolidated, repeats=5):
    """Time xr.open_zarr(...) on either a gs:// URL or an fsspec store."""
    times = []
    for _ in range(repeats):
        start = time.perf_counter()
        ds = xr.open_zarr(path_or_store, consolidated=consolidated, decode_timedelta=False)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        # discard dataset so next open is 'cold'
        del ds
    return times

if __name__ == "__main__":
    N = 3
    print(f"Timing plain Zarr open ({PLAIN_ZARR!r}) {N}× …")
    plain_times = time_open_and_slice(PLAIN_ZARR, consolidated=True, repeats=N)
    print("  times:", [f"{t*1000:.1f} ms" for t in plain_times])
    print("  avg:  ", f"{(sum(plain_times)/N)*1000:.1f} ms")

    print(f"\nTiming Icechunk open ({ICE_PREFIX!r}) {N}× …")
    ice_times = time_open_and_slice(ice_store, consolidated=False, repeats=N)
    print("  times:", [f"{t*1000:.1f} ms" for t in ice_times])
    print("  avg:  ", f"{(sum(ice_times)/N)*1000:.1f} ms")