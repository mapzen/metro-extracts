var Metro = function (){
  var displayMap,
    metro;

  var MetroApp = {
    init : function(data) {
      metro = data;
      this.initDisplayMap();
    },
    hasWebGL: function() {
      try {
        var canvas = document.createElement('canvas')
        return !!(window.WebGLRenderingContext && (canvas.getContext('webgl') || canvas.getContext('experimental-webgl')))
      } catch (x) {
        return false
      }
    },
    initDisplayMap: function() {
      var southwest = L.latLng(metro.bbox.bottom, metro.bbox.right),
        northeast = L.latLng(metro.bbox.top, metro.bbox.left),
        options = {
          scrollWheelZoom: false,
          // Disables dragging on touch-detected devices
          dragging: (window.self !== window.top && L.Browser.touch) ? false : true,
          tap: (window.self !== window.top && L.Browser.touch) ? false : true,
        };
      displayMap = L.map('map', options).fitBounds(L.latLngBounds(southwest, northeast));

      if (this.hasWebGL() === true) {
        var layer = Tangram.leafletLayer({
          scene: '../static/scene.yaml',
          attribution: '<a href="https://mapzen.com/tangram">Tangram</a> | &copy; OSM contributors | <a href="https://mapzen.com/">Mapzen</a>'
        });
      } else {
        var layer = L.tileLayer('https://stamen-tiles.a.ssl.fastly.net/toner-lite/{z}/{x}/{y}.png', {
          attribution: 'Map tiles by <a href="http://stamen.com">Stamen Design</a>, under <a href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a>. Data by <a href="http://openstreetmap.org">OpenStreetMap</a>, under <a href="http://www.openstreetmap.org/copyright">ODbL</a>.',
        });
      }
      layer.addTo(displayMap);

      var rect = new L.Rectangle(new L.LatLngBounds([southwest, northeast]), { className : "blue" });
      displayMap.addLayer(rect);
    },
    addEnclosed: function() {
      var id = request.split("&")[0],
        name = decodeURIComponent(request.split("&")[1]);

      var div = d3.select("#encompassed");
      div.style("display","block")
        .selectAll(".name").text(name);
      div.select(".link").attr("href","/wof/"+id+".geojson");
    }
  };
  return MetroApp;
}