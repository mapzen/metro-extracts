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

exports.getReadableName = function (key, separator) {
  let name = key.substring(0, key.indexOf(separator))
  name = name.replace(/-/g, ' ').replace(/_/g, ', ')
  name = capitalize(name)
  return name
}

function capitalize (string) {
  var words = string.split(' ')
  words = words.map(function (word) {
    return word.charAt(0).toUpperCase() + word.slice(1)
  })
  return words.join(' ')
}

exports.getNormalizedId = function (key, separator) {
  let name = key.substring(0, key.indexOf(separator))
  return name.toLowerCase().replace(/,?\s+/g, '-').replace(/_/g, '-')
}

// Formats processing.
// The order matters! (for presentational purposes)
// Note: the first 8 are used by Metro Extracts
// The last one (geojson) is used by Borders
const originalFormats = [
  'osm.pbf',
  'osm.bz2',
  'osm2pgsql-shapefiles.zip',
  'osm2pgsql-geojson.zip',
  'imposm-shapefiles.zip',
  'imposm-geojson.zip',
  'water.coastline.zip',
  'land.coastline.zip',
  'geojson.tgz'
]
const readableFormats = [
  'OSM PBF',
  'OSM XML',
  'OSM2PGSQL SHP',
  'OSM2PGSQL GEOJSON',
  'IMPOSM SHP',
  'IMPOSM GEOJSON',
  'WATER COASTLINE SHP',
  'LAND COASTLINE SHP',
  'GEOJSON'
]

exports.getFormat = function (key, separator) {
  // Filenames do not have consistent separators.
  let format = key.substring(key.indexOf(separator) + 1)
  return readableFormats[originalFormats.indexOf(format)] || 'UNKNOWN'
}

exports.sortFilesByFormat = function (files) {
  return files.sort(function (a, b) {
    return (readableFormats.indexOf(a.format) < readableFormats.indexOf(b.format)) ? -1 : 1
  })
}
