'use strict'
/* global $ */

var mapurl = 'https://s3.amazonaws.com/osm-polygons.mapzen.com/regions.geojson'
var regions = []

function openMapPopup (e) {
  var city = $(this).parent().data('city')
  markers[city].openPopup()
}

function getRandomColor () {
  var letters = '0123456789ABCDEF'.split('')
  var color = '#'
  for (var i = 0; i < 6; i++ ) {
    color += letters[Math.floor(Math.random() * 16)]
  }
  return color
}

var onEachFeature = function (feature, layer) {
  if (feature.properties && feature.properties.name) {
    var city = getReadableName(feature.properties['name:display'])
    var searchName = getReadableName(feature.properties['name'])
    regions.push({
      name: feature.properties['name'],
      displayName: feature.properties['name:display']
    })
    markers[feature.properties['name:display']] = layer
    layer.setStyle({
      fillColor:getRandomColor()
    })
    layer.bindPopup(city)
    layer.on('click', function(e){
      setSearchBox(city)
    })
    layer.on('popupclose', function(e){
      clearSearchBox()
    })
  }
}

// Setup map
var geoJSONOptions = {
  style: {
    'weight': 5,
    'fillOpacity': 0.7,
    'color': '#fff',
    'opacity': 0.0,
  },
  onEachFeature: onEachFeature
}

var displayMap = initDisplayMap(mapurl, geoJSONOptions)

function setupEasterEgg () {
  var list = document.getElementById('extracts_list')
  if (!list) return
  var source = '<ul style="display: none;" id="null-island-easter-egg"><li data-city="Null Island"><h5 class="place_name">Null Island</h5><div class="btn-group btn-group-justified"><a href="https://github.com/nixta/null-island/blob/master/GeoJSON/null-island.geo.json" class="btn btn-default format metro-format" data-name="Null Island" data-format="GEOJSON">GEOJSON<span class="size" style="display: block; font-size: 10px; color: gray;">6 KB</span></a></div></li></ul>'
  $(source).insertAfter(list)
  var $input = $('#search_input')
  var egg = document.getElementById('null-island-easter-egg')
  $input.on('keyup', function () {
    egg.style.display = 'none'
    var input = $input.val().trim()
    if (input.search(/^nul/i) !== -1 && 'null island'.search(new RegExp(input, 'i')) === 0) {
      egg.style.display = 'block'
    }
  })
}

setupEasterEgg()
