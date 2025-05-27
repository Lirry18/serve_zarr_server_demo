import json
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
import xesmf as xe
# from bwdl.enums import GaussianGridResolution
from latlon_regridder import Regridder
import pandas as pd

# TODO think about a reverse way for the benchmarking
class GaussianRegridder(Regridder):
    """Class to regrid datasets to a Gaussian grid."""

    # def __init__(self, grid_res: GaussianGridResolution):
    #     self.grid_res = grid_res
    #     self.grid_info = self.load_json_dict()

    def load_json_dict(self) -> dict:
        """Load the JSON file containing gaussian grid information."""
        path = (
            PROJECT_DIR / f"reduced_gaussian_config/{self.grid_res.value}.json"
        )
        with open(path) as json_file:
            grid_info = json.load(json_file)
        return grid_info

    def create_target_grid(self, grid_info, ds):
        """Create a target grid based on the provided grid information from the json and the initial dataset."""
        # Extract latitudes and number of longitudes per latitude row
        lat_max, lat_min = ds.latitude.max().item(), ds.latitude.min().item()
        lon_max, lon_min = ds.longitude.max().item(), ds.longitude.min().item()
        target_lats = np.clip(
            np.array(
                [
                    grid_info[str(i)]["latitude"]
                    for i in range(1, len(grid_info) + 1)
                ]
            ),
            lat_min,
            lat_max,
        )

        target_lons_per_lat = [
            grid_info[str(i)]["reduced_point"]
            for i in range(1, len(grid_info) + 1)
        ]

        # Determine the max number of longitudes to create a padded 2D array
        max_n_lon = max(target_lons_per_lat)
        n_lat = len(target_lats)

        # Initialize arrays with NaN to handle reduced grid (irregular shape)
        lat_2d = np.full((n_lat, max_n_lon), np.nan, dtype=np.float32)
        lon_2d = np.full((n_lat, max_n_lon), np.nan, dtype=np.float32)

        for i, (lat, n_lon) in enumerate(
            zip(target_lats, target_lons_per_lat)
        ):
            lons = np.linspace(lon_min, lon_max, n_lon, endpoint=False)
            lat_2d[i, :n_lon] = lat
            lon_2d[i, :n_lon] = lons

        # Create the curvilinear grid
        target_grid = xr.Dataset(
            {
                "latitude": (["y", "x"], lat_2d),
                "longitude": (["y", "x"], lon_2d),
            }
        )
        return target_grid

    def add_cyclic_longitude(self, ds):
        """Add a cyclic longitude coordinate to the dataset in order to remap every point to the target grid."""
        # Check if the dataset already has a cyclic longitude coordinate
        if ds.longitude.max() != 360 and ds.longitude.min() >= 0:
            # get the nearest longitude to 0
            lon0 = ds.sel(longitude=0, method="nearest")
            # create a new dataset with the longitude at 360
            lon360 = lon0.assign_coords(longitude=360)
            ds = xr.concat([ds, lon360], dim="longitude")
        return ds

    def regrid(self, ds):
        """Regrid the dataset to the target grid."""
        # add longitude = 360 to ds so that the remapping doesn't loose information
        ds = self.add_cyclic_longitude(ds)
        # creae the target gaussian grid
        self.target_grid = self.create_target_grid(self.grid_info, ds)
        # create the regridder
        regridder = self.create_regridder(self.target_grid, ds)
        # optimize those chunks size
        ds = ds.chunk({"latitude": 50, "longitude": 50})
        ds_rg = regridder(
            ds,
            keep_attrs=True,
            output_chunks={"latitude": 50, "longitude": 50},
        ).astype("float32")
        # format curvilinear grid into 1D grid
        formatted_ds = self.format_ds(ds_rg, self.target_grid)
        return formatted_ds

    def create_regridder(self, target_grid, ds):
        """Create a regridder using xESMF."""
        # collect source grid
        # first variable 
        var = list(ds.data_vars.keys())[0]
        ds = ds[var]
        # get the lat and lon of the first variabl
        ds_static = ds.isel(time=0).chunk({"latitude": 50, "longitude": 50})

        # compute the current resolution
        current_res = ds_static.latitude.diff("latitude").values[0]
        weights_file = (
            f"regrid_weights_{current_res:.2f}_to_{self.grid_res.value}.nc"
        )
        weights_path = FlexPath(PROJECT_DIR / weights_file)

        if storage.exists(weights_path):
            print(f"Loading existing regridder weights from {weights_file}")
            # Load existing weights
            regridder = xe.Regridder(
                ds_static,
                target_grid,
                method="bilinear",
                weights=str(weights_path),
                reuse_weights=True,
            )
        else:
            print("Creating new regridder and computing weights...")
            regridder = xe.Regridder(
                ds_static,
                target_grid,
                method="bilinear",
                reuse_weights=False,
            )
            regridder.to_netcdf(str(weights_path))
            print(f"Saved regridder weights to {weights_path}")

        print("Regridder ready.")
        return regridder

    def plot_map(self, ds):
        """Plot the regridded dataset on a map."""
        # Extract latitude, longitude, and values
        var = list(ds.data_vars.keys())[0]
        ds = ds[var]
        lats = ds.latitude.values
        lons = ds.longitude.values
        values = ds.isel(time=0).isel(pressure_level=0).values

        fig, ax = plt.subplots(
            figsize=(10, 5), subplot_kw={"projection": ccrs.PlateCarree()}
        )
        # add scatter
        sc = ax.scatter(
            lons,
            lats,
            c=values,
            cmap="viridis",
            s=10,
            transform=ccrs.PlateCarree(),
        )

        # Add coastlines and borders
        ax.coastlines()
        ax.add_feature(cfeature.BORDERS, linestyle=":")
        ax.set_title("2m Temperature")

        # Add gridlines
        cbar = plt.colorbar(
            sc, ax=ax, orientation="vertical", shrink=0.7, pad=0.05
        )
        cbar.set_label("2 metre temperature [K]")

        plt.tight_layout()
        plt.show()

    def format_ds(self, ds, target_grid):
        """Format the dataset to match a 1D grid."""
        # Get curvilinear grid
        target_lats_2d = target_grid.latitude.values
        target_lons_2d = target_grid.longitude.values
        # assign coords
        ds = ds.assign_coords(
            {
                "latitude": (("y", "x"), target_lats_2d),
                "longitude": (("y", "x"), target_lons_2d),
            }
        )

        # Create a mask for valid (non-NaN) points
        valid_mask = ~np.isnan(target_lats_2d) & ~np.isnan(target_lons_2d)
        # make it xarray with dim y and x
        valid_mask = xr.DataArray(
            valid_mask, dims=("y", "x"), coords={"y": ds.y, "x": ds.x}
        )

        ds_out = {}

        for var in ds.data_vars:
            arr = ds[var]

            # Make sure y and x are the first dimensions
            dims = arr.dims
            spatial_dims = ("y", "x")
            non_spatial_dims = tuple(
                dim for dim in dims if dim not in spatial_dims
            )

            arr = arr.transpose(*spatial_dims, *non_spatial_dims)

            # Stack spatial dimensions into a single dimension (lazy operation)
            flat_data = arr.stack(point=("y", "x"))

            # Filter only valid points (non-NaN from curvilinear grid)
            filtered_data = flat_data.where(
                valid_mask.stack(point=("y", "x")), drop=True
            )
            # Reset multiindex to vars
            da = filtered_data.reset_index("point")

            # Crée un nouvel index 'point' plat
            new_point_index = xr.DataArray(
                np.arange(da.sizes["point"]), dims="point", name="point"
            )

            # Remplace l'index
            da = da.assign_coords(point=new_point_index).set_index(
                point="point"
            )
            # remove x and y as coords
            da = da.reset_coords(["x", "y"], drop=True)
            ds_out[var] = da
            # if var == 'temperature':ed_data
            #     self.plot_map(filtered_data)

        return xr.Dataset(ds_out)


class GaussianToLatLonRegridder(Regridder):
    """Class to regrid datasets from a Gaussian grid to a regular LatLon grid."""

    def __init__(self, grid_res: float):
        """
        Parameters:
        - grid_res: Desired resolution in degrees (e.g., 1.5 for 1.5° x 1.5° grid)
        """
        self.grid_res = grid_res

    def create_target_grid(self, ds):
        """Create a regular lat-lon target grid based on resolution."""
        lat_min, lat_max = ds.latitude.min().compute(), ds.latitude.max().compute()
        lon_min, lon_max = ds.longitude.min().compute(), ds.longitude.max().compute()

        latitudes = np.arange(lat_min, lat_max + self.grid_res, self.grid_res)
        longitudes = np.arange(lon_min, lon_max + self.grid_res, self.grid_res)

        return xr.Dataset(
            {
                "latitude": (["latitude"], latitudes),
                "longitude": (["longitude"], longitudes),
            }
        )

    def regrid(self, ds):
        """Regrid from Gaussian to regular lat-lon grid using xESMF with chunked weight generation."""

        # 1. Build the target grid (2D lat/lon mesh)
        target_grid = self.create_target_grid(ds)

        spatial_dims = list(target_grid.dims.keys())
        shape = tuple(target_grid.dims[dim] for dim in spatial_dims)

        # 2. Add a dummy mask variable so xESMF can chunk it
        #    (coords alone don't count as a data variable)
        target_grid["mask"] = xr.DataArray(
            np.ones(shape, dtype=bool),
            dims=spatial_dims
        )

        # 3. Chunk the target grid along both spatial dims
        #    here: 50×50 tiles (tweak as needed for your RAM)
        chunk_dict = {dim: 50 for dim in spatial_dims}
        tgt_chunked = target_grid.chunk(chunk_dict)

        # 4. Take a representative static slice to define the source grid
        ds_static = ds.isel(lead=0)

        # 5. Create the Regridder with parallel=True
        regridder = xe.Regridder(
            ds_static,
            tgt_chunked,
            method="bilinear",
            reuse_weights=False,
            parallel=True
        )

        # 6. Apply it to the full dataset (stays lazy & chunked)
        ds_rg = regridder(ds, keep_attrs=True)
        return ds_rg

