'use strict'
/* global $ */

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

// Detect if webgl is available on the browser
function hasWebGL () {
  try {
    var canvas = document.createElement('canvas')
    return !!(window.WebGLRenderingContext && (canvas.getContext('webgl') || canvas.getContext('experimental-webgl')))
  } catch (x) {
    return false
  }
}

var getReadableName = function (name) {
  return name.replace(/-/g, ' ').replace(/_/g, ', ')
}

function initDisplayMap (geoJSONUrl, geoJSONOptions) {
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
      scene: 'https://cdn.rawgit.com/tangrams/refill-style/857e1439ae947057bdcfaea7b5eb958628dc7c26/refill-style.yaml',
      attribution: '<a href="https://mapzen.com/tangram">Tangram</a> | &copy; OSM contributors | <a href="https://mapzen.com/">Mapzen</a>'
    })
  } else {
    layer = L.tileLayer('https://stamen-tiles.a.ssl.fastly.net/toner-lite/{z}/{x}/{y}.png', {
      attribution: 'Map tiles by <a href="http://stamen.com">Stamen Design</a>, under <a href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a>. Data by <a href="http://openstreetmap.org">OpenStreetMap</a>, under <a href="http://www.openstreetmap.org/copyright">ODbL</a>.',
    })
  }
  layer.addTo(displayMap)

  $.ajax({
    type: 'GET',
    url: geoJSONUrl,
    dataType: 'json',
    success: function (data) {
      L.geoJson(data, geoJSONOptions).addTo(displayMap)
    },
    error: function (request, status, error) {
      // do nothing
    }
  })

  return displayMap
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
initListnav()

// Logs an event to Analytics when a file is downloaded
$('body').on('click', 'a.metro-format', function () {
  var $this = $(this)
  var name = $this.data('name')
  var format = $this.data('format')
  ga('send', 'event', name, 'click', format)
})

// Highlights a place on the map when the name is clicked
$(document).ready(function () {
  $('body').on('click', 'h5.place_name', openMapPopup)
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
