var Extract = function (){
  var bbox,
    sceneURL;

  var ExtractApp = {
    init : function(initBBox, scene) {
      bbox = initBBox;
      sceneURL = scene;
      this.initDisplayMap();
      return this;
    },
    initDisplayMap: function() {
      var southwest = L.latLng(bbox.s, bbox.w),
        northeast = L.latLng(bbox.n, bbox.e),
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

      var rect = new L.Rectangle(new L.LatLngBounds([southwest, northeast]), { className : "blue" });
      displayMap.addLayer(rect);
    },
    showOutline : function(geojson_url) {
      d3.json(geojson_url, function(data){
        if (data && data.geometry.type == "Feature") {
          outline = L.geoJson(data.geometry, { className : "outline" }).addTo(displayMap);
          displayMap.addLayer(outline);
        } else {
          d3.select("#encompassed").style("display","none");
        }
      });
    }
  };
  return ExtractApp;
}