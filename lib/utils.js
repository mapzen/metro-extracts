'use strict'

exports.getReadableFileSize = function (bytes) {
  bytes = parseInt(bytes, 10)
  if (bytes === 0) return 'n/a'

  let formats = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  let i = Math.floor(Math.log(bytes) / Math.log(1024))

  // For KB/bytes, cleaner to not display decimal
  let precision = (i <= 1) ? 0 : 1
  return (bytes / Math.pow(1024, i)).toFixed(precision) + ' ' + formats[i]
}

exports.getReadableName = function (key) {
  let name = key.substring(0, key.indexOf('.'))
  return name.replace(/-/g, ' ').replace(/_/g, ', ')
}

exports.getNormalizedId = function (key) {
  let name = key.substring(0, key.indexOf('.'))
  return name.toLowerCase().replace(/,?\s+/g, '-').replace(/_/g, '-')
}

// Formats processing.
// The order matters! (for presentational purposes)

const originalFormats = [
  'osm.pbf',
  'osm.bz2',
  'osm2pgsql-shapefiles.zip',
  'osm2pgsql-geojson.zip',
  'imposm-shapefiles.zip',
  'imposm-geojson.zip',
  'water.coastline.zip',
  'land.coastline.zip'
]
const readableFormats = [
  'OSM PBF',
  'OSM XML',
  'OSM2PGSQL SHP',
  'OSM2PGSQL GEOJSON',
  'IMPOSM SHP',
  'IMPOSM GEOJSON',
  'WATER COASTLINE SHP',
  'LAND COASTLINE SHP'
]

exports.getFormat = function (key) {
  let format = key.substring(key.indexOf('.') + 1)
  return readableFormats[originalFormats.indexOf(format)] || 'UNKNOWN'
}

exports.sortFilesByFormat = function (files) {
  return files.sort(function (a, b) {
    return (readableFormats.indexOf(a.format) < readableFormats.indexOf(b.format)) ? -1 : 1
  })
}
