# Simple demo to show how we can publish ZARR data with XPublish

How to install

1 - Create venv with python 3.11
2- Install pacakges:
    xarray
    xpublish
    fastapi
    xpublish_edr
    xpublish_wms
    pydantic
    numpy
    dotenv
    supabase
    (maybe i forgot some)
    

PS: Get Google CLI Auth working on your laptop, else the data can't be retrieved

How to run

1 - Start server with "uvicorn server:app --reload --port 8000"
2 - Start local server on 8001 "python -m http.server 8001"
3 - visit localhost:8000/docs for swagger documentation and OpenAPI
    visit localhost:8001/viewer/globes.html for side by side map demo




