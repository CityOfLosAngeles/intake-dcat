import copy
import time

import requests
import yaml

from dask.utils import tmpfile
import s3fs

from .catalog import DCATCatalog

# TODO: should we allow the user to pass in a s3fs session here?
fs = s3fs.S3FileSystem()

MAX_DOWNLOAD_ATTEMPTS = 60
RETRY_DELAY = 5


def mirror_data(manifest_file, upload=True, name=None, version=None):
    """
    Given a path the a manifest.yml file, download the relevant data,
    upload it to the specified bucket, and return a new catalog
    pointing at the data.

    Parameters
    ----------
    manifest_file: str
        A path to a manifest file.

    upload: boolean
        Whether to upload the datasets to the indicated bucket. Defaults to
        True, but can be set to false to perform a dry run.

    Returns
    -------
    A dictionary containing data for the new catalog.
    """
    new_catalog = {"metadata": {"name": name, "version": version}, "sources": {}}
    with open(manifest_file) as f:
        manifest = yaml.safe_load(f)
        bucket_uri = manifest["metadata"]["bucket_uri"]
        for catalog_name, catalog_data in manifest["sources"].items():
            catalog = DCATCatalog(catalog_data["args"]["url"], name=catalog_name)
            items = catalog_data["args"]["items"]
            for name, id in items.items():
                entry = yaml.safe_load(catalog[id].yaml())["sources"][id]
                new_entry = _construct_remote_entry(
                    bucket_uri, entry, name, upload=upload
                )
                new_catalog["sources"][name] = new_entry

    return new_catalog


def _upload_remote_data(old_uri, new_uri, dir=None):
    # Some servers, such as ESRI open data, can return 202 Accepted status codes
    # while it is preparing a dataset. In that case, we enter a retry loop.
    attempts = 0
    while attempts < MAX_DOWNLOAD_ATTEMPTS:
        r = requests.get(old_uri)
        if r.status_code == 202:
            attempts += 1
            time.sleep(RETRY_DELAY)
            continue
        elif r.status_code == 200:
            break
        else:
            raise RuntimeError(f"Unexpected response from DCAT server: {r.content}")
    else:
        raise RuntimeError("Unable to download dataset: Maximum retries met.")

    with tmpfile(dir=dir) as filename:
        with open(filename, "wb") as outfile:
            outfile.write(r.content)
        fs.put(filename, new_uri)


def _construct_remote_entry(bucket_uri, entry, name, directory="", upload=True):
    new_entry = copy.deepcopy(entry)
    old_uri = entry["args"]["urlpath"]
    upload_uri = _construct_remote_uri(bucket_uri, entry, name, directory)
    compression = _get_compression_for_entry(entry)
    access_uri = f"{compression}+{upload_uri}" if compression else upload_uri
    new_entry["args"]["urlpath"] = access_uri
    if upload:
        _upload_remote_data(old_uri, upload_uri)
    return new_entry


def _construct_remote_uri(bucket_uri, entry, name, directory=""):
    ext = _get_extension_for_entry(entry)
    key = f"{directory.strip('/')}/{name}{ext}" if directory else f"{name}{ext}"
    return f"{bucket_uri.strip('/')}/{key}"


def _get_extension_for_entry(intake_entry):
    """
    Given an intake catalog entry, return a file extension for it, which can
    be used to construct names when re-uploading the files to s3. It would be
    nice to be able to rely on extensions in the URL, but that is not
    particularly reliable. Instead, we infer an extension from the driver and
    args that are used. The following extensions are returned:

        GeoJSON: ".geojson"
        Zipped Shapefile: ".zip"
        Shapefile: ".shp"
        CSV: ".csv"
    """
    driver = intake_entry.get("driver")
    if driver == "geojson" or driver == "intake_geopandas.geopandas.GeoJSONSource":
        return ".geojson"
    elif (
        driver == "shapefile" or driver == "intake_geopandas.geopandas.ShapefileSource"
    ):
        compression = _get_compression_for_entry(intake_entry)
        if compression == "zip":
            return ".zip"
        elif not compression:
            return ".shp"
        else:
            raise ValueError(f"Unexpected compression scheme for {str(intake_entry)}")
    elif driver == "csv" or driver == "intake.source.csv.CSVSource":
        return ".csv"
    else:
        raise ValueError(f"Unsupported driver {driver}")


def _get_compression_for_entry(intake_entry):
    """
    Given an intake catalog entry, determine a compression scheme, if
    applicable. Fiona uses compound protocols like 'zip+s3://' to construct
    paths for GDAL, and we need to construct that properly.

    Returns a string scheme like "zip", "gzip",  or "tar". If no compression
    scheme is used, returns `None`.
    """
    driver = intake_entry.get("driver")
    if (
        driver == "geojson"
        or driver == "shapefile"
        or driver == "intake_geopandas.geopandas.GeoJSONSource"
        or driver == "intake_geopandas.geopandas.ShapefileSource"
    ):
        args = intake_entry.get("args", {})
        return args.get("geopandas_kwargs", {}).get("compression")
    else:
        return None
