'use strict'
/* global ga, L */

var map = 'https://s3.amazonaws.com/metro-extracts.mapzen.com/cities.geojson'

var keyTimeout
var timeout = 100
var markers = {}

var setSearchBox = function (text) {
  clearTimeout(keyTimeout)
  $('#search_input').val(text).trigger('keydown').trigger('keyup')
}

var clearSearchBox = function () {
  keyTimeout = setTimeout(function() {
    $('#search_input').val('').trigger('keydown').trigger('keyup')
  }, timeout)
}

var getReadableName = function (name) {
  return name.replace(/-/g, ' ').replace(/_/g, ', ')
}

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

// Detect if webgl is available on the browser
function hasWebGL () {
  var gl

  try {
    gl = document.createElement('canvas').getContext('webgl')
  } catch (x) {
    gl = null
  }

  return (gl) ? true : false
}

// Setup map
function initDisplayMap () {
  var southwest = L.latLng(-41.7713, -197.2265)
  var northeast = L.latLng(68.2693, 206.7187)
  var options = {
    scrollWheelZoom: false,
    // Disables dragging on touch-detected devices
    dragging: (window.self !== window.top && L.Browser.touch) ? false : true,
    tap: (window.self !== window.top && L.Browser.touch) ? false : true,
  }
  var displayMap = L.map('map', options).fitBounds(L.latLngBounds(southwest, northeast))
  var layer

  if (hasWebGL() === true) {
    layer = Tangram.leafletLayer({
      scene: 'https://raw.githubusercontent.com/tangrams/refill-style/gh-pages/refill-style.yaml',
      attribution: '<a href="https://mapzen.com/tangram" target="_blank">Tangram</a> | &copy; OSM contributors | <a href="https://mapzen.com/" target="_blank">Mapzen</a>'
    })
  } else {
    layer = L.tileLayer(' https://stamen-tiles.a.ssl.fastly.net/toner-lite/{z}/{x}/{y}.png', {
      attribution: 'Map tiles by <a href="http://stamen.com">Stamen Design</a>, under <a href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a>. Data by <a href="http://openstreetmap.org">OpenStreetMap</a>, under <a href="http://www.openstreetmap.org/copyright">ODbL</a>.',
    })
  }
  layer.addTo(displayMap)

  $.ajax({
    type: 'GET',
    url: map,
    dataType: 'json',
    success: function (data) {
      L.geoJson(data, {
        onEachFeature: onEachFeature
      }).addTo(displayMap)
    },
    error: function (request, status, error) {
      // do nothing
    }
  })
}

// Setup jquery-listnav
function initListnav () {
  // This is a jQuery plugin
  $('#extracts_list').listnav({
    noMatchText: 'No results found.',
    showCounts: false,
    includeNums: false
  })

  // Style listnav as Bootstrap button group
  var listnav = document.querySelector('.ln-letters')
  var listnavLinks = document.querySelectorAll('.ln-letters a')
  listnav.classList.add('btn-group', 'btn-group-justified')
  for (var i = 0; i < listnavLinks.length; i++) {
    listnavLinks[i].classList.add('btn', 'btn-default')
  }
}

// Enable all the interactive functionality
initDisplayMap()
initListnav()

// Logs an event to Analytics when a file is downloaded
$('body').on('click', 'a.metro-format', function () {
  var $this = $(this)
  var name = $this.data('name')
  var format = $this.data('format')
  ga('send', 'event', name, 'click', format)
})

// Highlights a place on the map when the name is clicked
$('body').on('click', 'h5.place_name', function (e) {
  var id = e.target.parentNode.id
  markers[id].openPopup()
})

// Enable search input box
$('#search_input')
  .fastLiveFilter('#extracts_list')
  .on('keyup', function(){
    if ($('#search_input').val() === '') {
      $('#extracts_list-nav').slideDown(100)
      $('#extracts_list-nav a.all').click()
    } else {
      $('#extracts_list-nav').slideUp(100)
    }
  })
