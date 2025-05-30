"""
Start:
    uvicorn server:app --reload --port 8000
"""

import xarray as xr
import xpublish as xp
from fastapi import Depends, HTTPException, Query
from xpublish_edr.plugin import CfEdrPlugin
from xpublish_wms.plugin import CfWmsPlugin
from enum import Enum
from typing import Literal
from pandas import Timestamp, Timedelta
from fastapi import HTTPException
import numpy as np
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal
from auth import get_current_user, login
import os
from dotenv import load_dotenv


# ENV

load_dotenv(".env")

# LOAD DATA

ds = xr.open_zarr(
    os.getenv("ZARR_PATH"),chunks={"init": 1}
)

origins = [
    "http://localhost:8001",   
    "http://127.0.0.1:8001",
]

# XPUBLISH APP

rest = xp.Rest(
    datasets      = {"model": ds},
    plugins={
             "cf_edr": CfEdrPlugin(),
             "wms" : CfWmsPlugin()},
)

app = rest.app 

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,        # or ["*"] during development
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS", "POST"],        # keep it tight
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


def subset_bbox(da, west, south, east, north):
    # Make mask to handle west south east noth to lat long
    mask = (
        (da.longitude >= west) & (da.longitude <= east) &
        (da.latitude  >= south) & (da.latitude  <= north)
    ).compute()
    return da.where(mask, drop=True)

def da_to_geojson(da: xr.DataArray, value_key: str = "value") -> dict:
    """
    Convert a 1-D point cloud DataArray to a GeoJSON FeatureCollection.
    Assumes coords latitude(point), longitude(point).
    """
    lat  = da["latitude"].values
    lon  = da["longitude"].values
    vals = da.values

    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(lon[i]), float(lat[i])]},
            "properties": {value_key: float(vals[i])},
        }
        for i in range(len(vals))
    ]

    return {"type": "FeatureCollection", "features": features}


@app.post("/login", response_model=TokenResponse, tags=["auth"])
def login_endpoint(creds: LoginRequest):
    try:
        token = login(creds.email, creds.password)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"access_token": token, "token_type": "bearer"}


@app.get("/mean14", summary="14-daags hPa gemiddelde binnen bbox", description="Retourneert het gemiddelde van geopotential op `pressure_level` in het opgegeven gebied.")
def mean14(west: float, south: float, east: float, north: float, 
           init: str = Query(..., description="Init-tijd (ISO-8601)"),
           member: int = 0, 
           lead: int = Query(0, ge=0, le=10, description="number of days after init time"),
           pressure_level: int = Query(500, enum=[500], description="pressure Level in hPa"),
           ):
    if west >= east or south >= north:
        raise HTTPException(status_code=400, detail="ongeldige bbox")
    
    lead_td = np.timedelta64(lead, 'D')
    print(lead_td)

    da = ds["geopotential"].sel(
        init="2021-01-02T00:00:00.000000000",
        lead = lead_td,
        member = 0,
        pressure_level= pressure_level
    )
    subset = subset_bbox(da, west, south, east, north)

    print(subset)
    return {"hPa": float(subset.mean())}


@app.get(
    "/geojson",
    summary="Download slice as GeoJSON",
    tags=["export"],
    response_class=JSONResponse,
)
def geojson(
    init  : str,
    lead  : int  = Query(0, ge=0, le=10),
    member: int  = 0,
    plevel: int  = Query(500, enum=[1000, 850, 500, 250]),
    west  : float|None = None,
    south : float|None = None,
    east  : float|None = None,
    north : float|None = None,
    user  = Depends(get_current_user),
):
    lead_td = np.timedelta64(lead, "D")

    da = (
        ds["geopotential"]
        .sel(init="2021-01-02T00:00:00.000000000",
             lead=lead_td,
             member=member,
             pressure_level=plevel)
    )

    # bbox-filter
    if None not in (west, south, east, north):
        da = subset_bbox(da, west, south, east, north)
        if da.point.size == 0:
            raise HTTPException(404, "Geen punten in bbox")

    # GeoJSON serialise
    gj = da_to_geojson(da, value_key="geopotential")

    headers = {"Content-Disposition": "attachment; filename=slice.geojson"}
    return JSONResponse(content=gj, media_type="application/geo+json", headers=headers)


