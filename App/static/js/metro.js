var Metro = function (){
  var displayMap,
    metro,
    sceneURL;

  var MetroApp = {
    init : function(data, URL) {
      metro = data;
      sceneURL = URL;
      this.initDisplayMap();
      return this;
    },
    initDisplayMap : function() {
      var southwest = L.latLng(metro.bbox.bottom, metro.bbox.right),
        northeast = L.latLng(metro.bbox.top, metro.bbox.left),
        options = {
          dragging: (window.self !== window.top && L.Browser.touch) ? false : true,
          tap: (window.self !== window.top && L.Browser.touch) ? false : true,
          scrollWheelZoom: false,
          scene: sceneURL,
          attribution: '<a href="https://mapzen.com/tangram">Tangram</a> | <a href="http://www.openstreetmap.org/copyright">&copy; OSM contributors</a> | <a href="https://mapzen.com/">Mapzen</a>',
          fallbackTile: L.tileLayer('https://stamen-tiles.a.ssl.fastly.net/toner-lite/{z}/{x}/{y}.png', {
            attribution: 'Map tiles by <a href="http://stamen.com">Stamen Design</a>'})
        };
      displayMap = L.Mapzen.map('map', options).fitBounds(L.latLngBounds(southwest, northeast));

      var rect = new L.Rectangle(new L.LatLngBounds([southwest, northeast]));
      displayMap.addLayer(rect);
    },
    showOutline : function(geojson_url) {
      d3.json(geojson_url, function(data){
        outline = L.geoJson(data.geometry, { className : "outline" }).addTo(displayMap);
        displayMap.addLayer(outline);
      });
    }
  };
  return MetroApp;
}