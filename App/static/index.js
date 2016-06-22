d3.select("#map").style("height", window.innerHeight + 'px');

function hasWebGL () {
  try {
    var canvas = document.createElement('canvas')
    return !!(window.WebGLRenderingContext && (canvas.getContext('webgl') || canvas.getContext('experimental-webgl')))
  } catch (x) {
    return false
  }
}
function initDisplayMap (geoJSONUrl, geoJSONOptions) {
  var southwest = L.latLng(0, -125)
  var northeast = L.latLng(0, 125)
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
      scene: './scene.yaml',
      attribution: '<a href="https://mapzen.com/tangram">Tangram</a> | &copy; OSM contributors | <a href="https://mapzen.com/">Mapzen</a>'
    })
  } else {
    layer = L.tileLayer('https://stamen-tiles.a.ssl.fastly.net/toner-lite/{z}/{x}/{y}.png', {
      attribution: 'Map tiles by <a href="http://stamen.com">Stamen Design</a>, under <a href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a>. Data by <a href="http://openstreetmap.org">OpenStreetMap</a>, under <a href="http://www.openstreetmap.org/copyright">ODbL</a>.',
    })
  }
  layer.addTo(displayMap);

  d3.json(geoJSONUrl, function(data){
    L.geoJson(data, geoJSONOptions).addTo(displayMap);
  });

  return displayMap
}
var mapurl = 'https://s3.amazonaws.com/metro-extracts.mapzen.com/cities.geojson';

var onEachFeature = function (feature, layer) {
  if (feature.properties && feature.properties.name) {
    var text = feature.properties.name;
    layer.on('click', function (e) {
      var str = text.split("_")[0].replace(/-/g," ");
      document.getElementById("search_input").value = str.capitalize();
      filterList(str);
    })
  }
}

// Setup map
var geoJSONOptions = {
  onEachFeature: onEachFeature
}
var displayMap = initDisplayMap(mapurl, geoJSONOptions)

var nestedCities;

d3.json('/cities.json',function(data) {
  var cityArray = [];
  for (region in data.regions){
    for (city in data.regions[region].cities) {
      var cityCountry = city.split("_");
      cityArray.push({
        city: cityCountry[0],
        country: cityCountry[1],
        bbox: data.regions[region].cities[city].bbox
      });
    }
  }
  nestedCities = d3.nest()
    .key(function(d){ return d.country; })
    .entries(cityArray)
    .sort(function(a,b){ return (a.key < b.key) ? -1 : (a.key > b.key) ? 1 : 0; });

  //drawList(nestedCities);
});

function drawList(data) {
  var countries = d3.select("#extracts").selectAll(".country").data(data);
  var enterCountries = countries.enter().append("div").attr("class","country");
  countries.exit().remove();
  enterCountries.append("div").attr("class","country-name")
    .on("click",function(d){
      doSearch(d.key);
    });
  countries.select(".country-name").text(function(d){ return d.key; });
  var cities = countries.selectAll(".city").data(function(d){ return d.values; });
  cities.enter().append("a").attr("class","city");
  cities.text(function(d){ return d.city.replace(/-/g," "); })
    .attr("href",function(d){ 
      return "./city.html#city="+d.city+"&country="+d.country+"&bbox="+[d.bbox.left, d.bbox.bottom,d.bbox.right, d.bbox.top]; 
    });
  cities.exit().remove();
}

d3.select("#search_submit").on("click",function(){
  doSearch(document.getElementById("search_input").value);
});

var wait = false,
  waitQuery;

function suggestSearch(query) {
  if (!wait) {
    wait = true;
    doSuggestion(query);
    setTimeout(function(){ wait = false; }, 500);
  } else {
    waitQuery = query;
  }
}

function doSuggestion(query) {
  d3.json("https://search.mapzen.com/v1/autocomplete?text="+query+"&sources=wof&api_key=search-owZDPeC", function(error, json) {
      var suggestion = d3.select(".autocomplete")
        .selectAll(".suggestion").data(json.features);
      suggestion.enter().append("div").attr("class","suggestion");
      suggestion.exit().remove();
      suggestion.text(function(d){ return d.properties.label; })
        .on("click",function(d){
          document.getElementById("search_input").value = d.properties.label;
          doSearch(d.properties.label);
          filterList(d.properties.label);
        });
  });
}

function doSearch(query) {
  d3.selectAll(".suggestion").remove();
  
  d3.json("https://search.mapzen.com/v1/search?text="+query+"&sources=wof&api_key=search-owZDPeC", function(error, json) {
      var bbox = json.features[0].bbox;
      displayMap.fitBounds([[bbox[1],bbox[0]],[bbox[3], bbox[2]]])
      if (json.features[0].properties.layer == "locality") displayMap.zoomOut(2);
      if (d3.selectAll(".city")[0].length == 0){
        requestExtract(json.features[0]);
      } else {
        clearRequest();
      }
  });
}

Number.prototype.toRad = function() {
   return this * Math.PI / 180;
}
Number.prototype.toDeg = function() {
   return this * 180 / Math.PI;
}

function calculateOffset(theta, d, lat1, lng1) {
  var lat1 = lat1.toRad(), 
    lng1 = lng1.toRad(),
    R = 6371;

  var lat2 = Math.asin( Math.sin(lat1)*Math.cos(d/R) 
        + Math.cos(lat1)*Math.sin(d/R)*Math.cos(theta) ),
    lng2 = lng1 + Math.atan2(Math.sin(theta)*Math.sin(d/R)*Math.cos(lat1), 
          Math.cos(d/R)-Math.sin(lat1)*Math.sin(lat2));

  return [lat2.toDeg(), lng2.toDeg()];
}

function calculateNewBox(bbox) {
  var distance = Math.sqrt(Math.pow(bbox[3]-bbox[1],2) + Math.pow(bbox[2]-bbox[0], 2))*25;
  var northEast = calculateOffset(-Math.PI*3/4, distance, bbox[1], bbox[0]),
  southWest = calculateOffset(Math.PI/4, distance, bbox[3], bbox[2]);
  return [northEast, southWest];
}

var rect, 
  dots = [],
  outline,
  requestBoundingBox;
var myIcon = L.divIcon({className: 'drag-icon'});
//var wof = "http://whosonfirst.mapzen.com/spelunker/id/";
var wof = "/wof/";

function requestExtract(metro) {
  var geoID = metro.properties.id;
  requestBoundingBox = calculateNewBox(metro.bbox);

  drawRequestBox();

  d3.json(wof+geoID+".geojson",function(data){
    var outline = L.geoJson(data.geometry, { className : "outline" }).addTo(displayMap);
    displayMap.addLayer(outline);
  });

  d3.select("#make-request").style("display","block")
    .selectAll(".name").text(metro.properties.name);
  d3.select("#request").style("display","none");
  d3.select("#make-request").select("a")
    .on("click",function(){
      d3.select(this).attr("href","https://github.com/mapzen/data-pages/issues/new?title="+metro.properties.name+"&body=Bounding Box: "+requestBoundingBox);
    });
}
function drawRequestBox() {
  clearMap();
  rect = new L.Rectangle(new L.LatLngBounds(requestBoundingBox), { className : "blue" });
  displayMap.addLayer(rect);

  var cSW = new L.marker(requestBoundingBox[0], { icon : myIcon, draggable: true });
  dots.push(cSW);
  var cNE = new L.marker(requestBoundingBox[1], { icon : myIcon, draggable: true });
  dots.push(cNE);

  cSW.on("drag",function(e){
    requestBoundingBox[0] = [e.target.getLatLng().lat, e.target.getLatLng().lng];
    displayMap.removeLayer(rect);
    rect = new L.Rectangle(new L.LatLngBounds(requestBoundingBox), { className : "blue" });
    displayMap.addLayer(rect);
  });
  cNE.on("drag",function(e){
    requestBoundingBox[1] = [e.target.getLatLng().lat, e.target.getLatLng().lng];
    displayMap.removeLayer(rect);
    rect = new L.Rectangle(new L.LatLngBounds(requestBoundingBox), { className : "blue" });
    displayMap.addLayer(rect);
  });

  dots.forEach(function(l){
    displayMap.addLayer(l);
  });
}
function clearMap() {
  if (rect) displayMap.removeLayer(rect);
  if (outline) displayMap.removeLayer(outline);
  dots.forEach(function(l){
    displayMap.removeLayer(l);
  });
  dots = [];
}
function clearRequest() {
  clearMap();
  d3.select("#request").style("display","block");
  d3.select("#make-request").style("display","none");
}

var keyIndex = -1;

String.prototype.capitalize = function() {
  var words = this.split(" "),
    capitalized = words.map(function(w){ return w.charAt(0).toUpperCase() + w.slice(1); });
  return capitalized.join(" ");
}

d3.select("#search_input").on("keyup",function(d, i, e){
  var inputDiv = document.getElementById("search_input");
  var val = inputDiv.value;

  if (!val.length) {
    drawList(nestedCities);
    d3.selectAll(".suggestion").remove();
    clearRequest();
    return;
  }

  var currentList = d3.selectAll(".suggestion");
  if (event.keyCode == 40) {
    keyIndex = Math.min(keyIndex+1, currentList[0].length-1);
    currentList.each(function(d, i){ //arrow down
      if (i == keyIndex)
        inputDiv.value = d.properties.label;
    }).classed("selected",function(d,i){ return i == keyIndex; });
    
  } else if (event.keyCode == 38) { //arrow up
    keyIndex = Math.max(keyIndex-1, 0);
    currentList.each(function(d, i){
      if (i == keyIndex)
        inputDiv.value = d.properties.label;
    }).classed("selected",function(d,i){ return i == keyIndex; });
    
  } else if (event.keyCode == 13) {
    keyIndex = -1;
    filterList(val);
    d3.selectAll(".suggestion").remove();
    doSearch(val);
  } else if (event.keyCode < 48 || event.keyCode > 90) {
    return; //restrict autocomplete to 0-9,a-z character input
  } else {
    keyIndex = -1;
    suggestSearch(val);
    filterList(val);
  }
});

function filterList(str) {
  var newData = [];
  nestedCities.forEach(function(d){
    var country = jQuery.extend({}, d);
    if (country.key.replace(/-/g," ").indexOf(str) != -1) {
      newData.push(country);
    } else {
      country.values = country.values.filter(function(e){ 
        return e.city.replace(/-/g," ").indexOf(str) != -1; 
      });
      if (country.values.length) newData.push(country);
    }
  });
  drawList(newData);
}