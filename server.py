"""
Start:
    uvicorn server:app --reload --port 8000
"""

import os
import xarray as xr
import xpublish as xp
from fastapi import Depends, HTTPException
from xpublish_edr.plugin import CfEdrPlugin

import importlib.metadata as im
print("xpublish     :", im.version("xpublish"))
print("xpublish-edr :", im.version("xpublish-edr"))


# CONFIG (MOVE TO ENV)

ZARR_PATH2 = "gs://base-era5_low_res/data.zarr"
ZARR_PATH = "gs://hindcasts_2021-01-02-2021-12-20_n65_daily_aqc2ou/hindcast_aifs_fragrant-sunset-420.zarr/"

# LOAD DATA

ds = xr.open_zarr(
    ZARR_PATH2,
)


# XPUBLISH APP

rest = xp.Rest(
    datasets      = {"model": ds},
    plugins={"cf_edr": CfEdrPlugin()},
)

app = rest.app 


from pandas import Timestamp, Timedelta
from fastapi import HTTPException

@app.get("/mean14")
def mean14(west: float, south: float, east: float, north: float):
    if west >= east or south >= north:
        raise HTTPException(status_code=400, detail="ongeldige bbox")

    subset = ds["geopotential"].sel(
        time="2019-12-31",
        longitude=slice(west, east),
        latitude=slice(south, north),
        pressure_level=500
    )

    print(subset)
    return {"hPa": float(subset.mean())}