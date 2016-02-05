'use strict'
/* global ga, L, $ */

var mapurl = 'https://s3.amazonaws.com/metro-extracts.mapzen.com/cities.geojson'

var getNormalizedId = function (name) {
  return name.toLowerCase().replace(/,?\s+/g, '-').replace(/_/g, '-')
}

var onEachFeature = function (feature, layer) {
  if (feature.properties && feature.properties.name) {
    var id = getNormalizedId(feature.properties.name)
    var text = getReadableName(feature.properties.name)
    markers[id] = layer
    layer.bindPopup(text)
    layer.on('click', function (e) {
      setSearchBox(text)
    })
    layer.on('popupclose', function (e) {
      clearSearchBox()
    })
  }
}

// Setup map
var geoJSONOptions = {
  onEachFeature: onEachFeature
}
var displayMap = initDisplayMap(mapurl, geoJSONOptions)

function openMapPopup (e) {
  var id = e.target.parentNode.id
  markers[id].openPopup()
}
