##Choose a file format

When you download from Metro Extracts, you can choose from several spatial data formats that run a spectrum of raw to more processed from left to right. The less-processed formats, such as xml and osm, are intended for developers who are running their own tools on the data. For most map-making workflows, a shapefile or GeoJSON works well because these can be added directly to many software applications.

![Available files for Lisbon, Portugal](./images/lisbon_download_formats.png)

### OSM PBF and OSM XML

OSM is a special community. Likewise, OSM data is really special. So special, it gets its own file format that nobody else uses, .osm. These files can be compressed, either as XML .bx2 or .pbf. Just note that .pbf is smaller than XML (more on .pbf [here](http://wiki.openstreetmap.org/wiki/ProtocolBufBinary)).

If you're very particular about what you need to extract or want to run your on tools on the data, these formats are probably for you. If you want to filter for specific tagged OSM data, like `amenity=police`, you could use some of the same command line tools that generate Metro Extracts, such as [Osmosis](http://wiki.openstreetmap.org/wiki/Osmosis), [osm2pgsql](https://github.com/openstreetmap/osm2pgsql), and [ogr2ogr](http://www.gdal.org/ogr2ogr.html) to generate a GeoJSON with an OSM dataset custom to your needs.

### OSM2PGSQL and IMPOSM

The names and contents of the shapefiles and GeoJSON files are based on the process used to extract the OSM data: `osm2pgsql` or `imposm`. When you download a Metro Extract created with [osm2pgsql](http://wiki.openstreetmap.org/wiki/Osm2pgsql), you get three datasets split by geometry type: lines, points, or polygons. The [imposm](http://imposm.org/) extracts, however, are grouped into individual layers based on the tags used in OSM, such as buildings and roads.

Here is an example of a point dataset from osm2pgsql:

	{
    "type": "Feature",
    "properties": {
        "osm_id": 368395980,
        "access": null,
        "aerialway": null,
        "aeroway": "helipad",
        "amenity": null,
        "area": null,
        "barrier": null,
        "bicycle": null,
        "brand": null,
        "bridge": null,
        "boundary": null,
        "building": null,
        "capital": null,
        "covered": null,
        "culvert": null,
        "cutting": null,
        "disused": null,
        "ele": "33",
        "embankment": null,
        "foot": null,
        "harbour": null,
        "highway": null,
        "historic": null,
        "horse": null,
        "junction": null,
        "landuse": null,
        "layer": null,
        "leisure": null,
        "lock": null,
        "man_made": null,
        "military": null,
        "motorcar": null,
        "name": "Unisys Heliport",
        "natural": null,
        "oneway": null,
        "operator": null,
        "poi": null,
        "population": null,
        "power": null,
        "place": null,
        "railway": null,
        "ref": null,
        "religion": null,
        "route": null,
        "service": null,
        "shop": null,
        "sport": null,
        "surface": null,
        "toll": null,
        "tourism": null,
        "tower:type": null,
        "tunnel": null,
        "water": null,
        "waterway": null,
        "wetland": null,
        "width": null,
        "wood": null,
        "z_order": null
    },
    "geometry": {
        "type": "Point",
        "coordinates": [
            -74.50099,
            40.3709408
        ]
    }
    }

That's a lot of information to explain that this is a helipad. Basically, every OSM tag that could be applied to a point, line, or polygon is stored as a feature property within that point, line, or polygon.

`imposm` exports are a little more granular and grouped into multiple datasets, most of which are important OSM tags that make sense to separate (administrative polygons, waterways, roads, and so on). Some versions of the same dataset that have been simplified; if the filename has the suffix `gen`, it's been generalized.

All extracted shapefiles and GeoJSONs use EPSG:4326 for the projection.

- imposm shapefiles: EPSG:4326
- osm2pgsql shapefiles: EPSG:4326
- GeoJSONs (imposm and osm2pgsql): EPSG:4326

#### Technical details osm2pgsql and imposm files

If you're working with spatial data, you're most likely working with SQL data. `osm2pgsql` and `imposm` are tools for importing .osm data into PostGIS. Mapzen's chef recipe then generates shapefiles using the PostGIS command [pgsql2shp](http://www.bostongis.com/pgsql2shp_shp2pgsql_quickguide.bqg) and GeoJSONs using `ogr2ogr`. `osm2pgsql` and imposm carve up .osm data in different ways that you can configure yourself.
