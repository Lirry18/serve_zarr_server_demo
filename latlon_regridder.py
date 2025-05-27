from abc import ABC
from abc import abstractmethod
from typing import Any
import numpy as np
import xarray as xr
import xesmf as xe


class Regridder(ABC):
    """Regridder base class for regridding datasets."""

    def __init__(self, grid_res: Any):
        self.grid_res = grid_res

    @abstractmethod
    def regrid(self, ds):
        """Regrid the dataset `ds` to the target grid resolution."""
        pass


class LatLonRegridder(Regridder):
    """Class to regrid datasets lat-lon grid to a lat-lon grid : change resolution."""

    def __init__(self, grid_res: float):
        self.grid_res = grid_res

    def regrid(self, ds):
        """Regrid the dataset to the target resolution."""
        lat_diff = np.diff(ds.latitude)
        current_resolution = lat_diff[0]
        target_resolution = self.grid_res
        if target_resolution is not None:
            if not np.isclose(target_resolution, current_resolution):
                print(
                    f"Regridding required. Current resolution: {current_resolution}°, "
                    f"Target: {target_resolution}°"
                )
                target_grid = xr.Dataset(
                    {
                        "latitude": (
                            ["latitude"],
                            np.arange(
                                -90 + target_resolution / 2,
                                90,
                                target_resolution,
                            ),
                        ),
                        "longitude": (
                            ["longitude"],
                            np.arange(0, 360, target_resolution),
                        ),
                    }
                )
                print("Creating regridder with bilinear interpolation")
                regridder = xe.Regridder(ds, target_grid, method="bilinear")

                print("Applying regridding")
                ds = regridder(ds, keep_attrs=True)
                print(
                    f"New grid dimensions: lat={len(ds.latitude)}, "
                    f"lon={len(ds.longitude)}"
                )
            else:
                print(
                    "No regridding needed - current resolution matches target"
                )
        return ds
