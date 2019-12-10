import re

DEFAULT_PRIORITIES = ["geojson", "shapefile", "csv"]


def get_relevant_distribution(dcat_entry, priority=None):
    """
    Given a DCAT entry, find the most relevant distribution
    for the intake catalog. Returns a tuple of
    (intake_driver_name, distribution). In general,
    we choose the more specific formats over the less specific
    formats. By default, they are ranked in the following order:

        GeoJSON
        Shapefile
        CSV

    You can provide a "priority" list to customize the priority.

    If none of these are found, None.
    If there are no distributions, it returns None.
    """
    distributions = dcat_entry.get("distribution")
    if not distributions or not len(distributions):
        return None

    priority = priority or DEFAULT_PRIORITIES
    for p in priority:
        if p.lower() == "geojson":
            for d in distributions:
                if test_geojson(d):
                    return "geojson", geojson_driver_args(d)
        elif p.lower() == "shapefile":
            for d in distributions:
                if test_shapefile(d):
                    return "shapefile", shapefile_driver_args(d)
        elif p.lower() == "csv":
            for d in distributions:
                if test_csv(d):
                    return "csv", csv_driver_args(d)
        else:
            raise ValueError(f"Unexpected driver {p}")

    return None


def test_geojson(distribution):
    """
    Test if a DCAT:distribution is GeoJSON.
    """
    return (
        distribution.get("mediaType") == "application/vnd.geo+json"
        or distribution.get("format", "").lower() == "geojson"
    )


def test_csv(distribution):
    """
    Test if a DCAT:distribution is CSV.
    """
    return (
        distribution.get("mediaType") == "text/csv"
        or distribution.get("format", "").lower() == "csv"
    )


def test_shapefile(distribution):
    """
    Test if a DCAT:distribution is a Shapefile.
    """
    # TODO: can there be a more robust test here?
    url = distribution.get("downloadURL") or distribution.get("accessURL") or ""
    title = distribution.get("title", "").lower()
    format = distribution.get("format", "").lower()
    return (
        title == "shapefile"
        or format == "shapefile"
        or re.search("format=shapefile", url, re.I) is not None
    )


def geojson_driver_args(distribution):
    """
    Construct driver args for a GeoJSON distribution.
    """
    url = distribution.get("downloadURL") or distribution.get("accessURL")
    if not url:
        raise KeyError(f"A download URL was not found for {str(distribution)}")
    return {"urlpath": url}


def csv_driver_args(distribution):
    """
    Construct driver args for a GeoJSON distribution.
    """
    url = distribution.get("downloadURL") or distribution.get("accessURL")
    if not url:
        raise KeyError(f"A download URL was not found for {str(distribution)}")
    return {"urlpath": url, "csv_kwargs": {"blocksize": None, "sample": False}}


def shapefile_driver_args(distribution):
    """
    Construct driver args for a GeoJSON distribution.
    """
    url = distribution.get("downloadURL") or distribution.get("accessURL")
    if not url:
        raise KeyError(f"A download URL was not found for {str(distribution)}")
    args = {"urlpath": url}
    return args
