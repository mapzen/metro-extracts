Number.prototype.toRad = function() {
   return this * Math.PI / 180;
}
Number.prototype.toDeg = function() {
   return this * 180 / Math.PI;
}

var Metros = function() {
  var nestedCities,
    geoJSONUrl,
    sceneURL,
    displayMap,
    extractLayers = [],
    xhr,
    keyIndex = 0,
    placeID = null,
    wofPrefix = null;

  var rect, 
    dots = [],
    outline,
    requestBoundingBox;

  var MetrosApp = {
    init : function(nestedData, jsonURL, scene, wofPrefixURL) {
      nestedCities = nestedData;
      geoJSONUrl = jsonURL;
      sceneURL = scene;
      wofPrefix = wofPrefixURL;
      this.initDisplayMap();
      return this;
    },
    hasWebGL : function() {
      try {
        var canvas = document.createElement('canvas')
        return !!(window.WebGLRenderingContext && (canvas.getContext('webgl') || canvas.getContext('experimental-webgl')))
      } catch (x) {
        return false
      }
    },
    initDisplayMap : function() {
      var southwest = L.latLng(0, -125),
        northeast = L.latLng(0, 125),
        options = {
          scrollWheelZoom: false,
          // Disables dragging on touch-detected devices
          dragging: (window.self !== window.top && L.Browser.touch) ? false : true,
          tap: (window.self !== window.top && L.Browser.touch) ? false : true,
        };
      displayMap = L.map('map', options).fitBounds(L.latLngBounds(southwest, northeast));

      if (this.hasWebGL() === true) {
        var layer = Tangram.leafletLayer({
          scene: sceneURL,
          attribution: '<a href="https://mapzen.com/tangram">Tangram</a> | &copy; OSM contributors | <a href="https://mapzen.com/">Mapzen</a>'
        });
      } else {
        var layer = L.tileLayer('https://stamen-tiles.a.ssl.fastly.net/toner-lite/{z}/{x}/{y}.png', {
          attribution: 'Map tiles by <a href="http://stamen.com">Stamen Design</a>, under <a href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a>. Data by <a href="http://openstreetmap.org">OpenStreetMap</a>, under <a href="http://www.openstreetmap.org/copyright">ODbL</a>.',
        });
      }
      layer.addTo(displayMap);

      var onEachFeature = function (feature, layer) {
        extractLayers.push(layer);
        layer.bindPopup("<a href='"+feature.properties.href+"'>"+feature.properties.display_name+"</a>");
      }

      d3.json(geoJSONUrl, function(data){
        L.geoJson(data, { onEachFeature: onEachFeature, className : "red" }).addTo(displayMap);
      });
    },
    filterList : function(str) {
      var newData = [];
      str = str.toLowerCase();
      nestedCities.forEach(function(d){
        if (d.country.toLowerCase().indexOf(str) != -1) {
          newData.push(d);
        } else {
          var c = {
            country : d.country,
            metros : []
          }
          d.metros.forEach(function(e){ 
            if (e.name.toLowerCase().indexOf(str) != -1)
              c.metros.push(e);
          });
          if (c.metros.length) newData.push(c);
        }
      });
      this.drawList(newData);
    },
    drawList : function(data, request_id, display_name, noWOF) {
      d3.select("#request-wrapper").classed("filtered",!data.length);

      var countries = d3.select("#extracts").selectAll(".country").data(data);
      var enterCountries = countries.enter().append("div").attr("class","country");
      countries.exit().remove();
      enterCountries.append("div").attr("class","country-name")
      var m = this;
      countries.select(".country-name")
        .text(function(d){ return d.country; })
        .on("click",function(d){
          m.doSearch(d.country, true);
        });
      var cities = countries.selectAll(".city").data(function(d){ return d.metros; });
      cities.enter().append("a").attr("class","city");
      cities.text(function(d){ return d.name; })
        .attr("href",function(d){ 
          if (noWOF) return d.href;
          else return d.href + (request_id ? escape(request_id)+"/"+escape(display_name) : ""); });
      cities.exit().remove();
    },
    doSuggestion : function(query) {
      if (xhr) xhr.abort();
      var m = this;
      xhr = d3.json("https://search.mapzen.com/v1/autocomplete?text="+query+"&sources=wof&api_key=search-owZDPeC", function(error, json) {
        m.showSuggestions(json);
      });
    },
    showSuggestions : function(data) {
      data.features.unshift({
        label : true,
        text : "To request a new extract:"
      });

      var suggestion = d3.select(".autocomplete")
        .selectAll(".suggestion").data(data.features);
      suggestion.enter().append("div").attr("class","suggestion");
      suggestion.exit().remove();
      var m = this;
      suggestion.html(function(d){
        if (d.label) return d.text;
        else return d.properties.label + "<span class='layer'>(" + d.properties.layer + ")</span>"; 
      }).on("click",function(d){
        if (d.label) return;
        placeID = d.properties.source + ":" + d.properties.layer + ":" + d.properties.id;
        document.getElementById("search_input").value = d.properties.label;
        m.onSubmit(d.properties.label);
      });
    },
    selectSuggestion : function() {
      var currentList = d3.selectAll(".suggestion");
      currentList.each(function(d, i){ 
        if (i == keyIndex) {
          document.getElementById("search_input").value = d.properties.label;
          placeID = d.properties.source + ":" + d.properties.layer + ":" + d.properties.id;
        }
      }).classed("selected",function(d,i){ return i == keyIndex; });
    },
    onSubmit : function(val) {
      keyIndex = 0;
      this.filterList(val);
      d3.selectAll(".suggestion").remove();
      this.doSearch(val);
      placeID = null;
    },
    searchError : function(query) {
      var m = this;
      d3.select("#request-wrapper").attr("class","filtered-error");
      d3.select("#search-error").select(".name").text(query);
    },
    clearSearchBox : function() {
      document.getElementById("search_input").value = "";
      this.drawList(nestedCities);
      d3.selectAll(".suggestion").remove();
      placeID = null;
      this.clearRequest();
    },
    processKeyup : function(event) {
      var inputDiv = document.getElementById("search_input");
      var val = inputDiv.value;

      if (!val.length) {
        this.clearSearchBox();
        return;
      }

      if (event.keyCode == 40) { //arrow down
        keyIndex = Math.min(keyIndex+1, d3.selectAll(".suggestion")[0].length-1);
        this.selectSuggestion();   
      } else if (event.keyCode == 38) { //arrow up
        keyIndex = Math.max(keyIndex-1, 1);
        this.selectSuggestion();
      } else if (event.keyCode == 13) { //enter
        this.onSubmit(val);
      } else if (event.keyCode != 8 && (event.keyCode < 48 || event.keyCode > 90)) {
        return; //restrict autocomplete to 0-9,a-z character input, excluding delete
      } else {
        keyIndex = 0;
        placeID = null;
        this.doSuggestion(val);
        this.filterList(val);
      }
    },
    doSearch : function(query, countrySearch) {
      d3.selectAll(".suggestion").remove();
      var m = this;

      if (placeID) {
        d3.json("https://search.mapzen.com/v1/place?api_key=search-owZDPeC&ids="+placeID, function(error, json){
          m.requestExtract(json.features[0]);
        });
      } else {
        d3.json("https://search.mapzen.com/v1/search?text="+query+"&sources=wof&api_key=search-owZDPeC", function(error, json) {
          if (!json.features.length) {
            d3.json("https://search.mapzen.com/v1/search?text="+query+"&api_key=search-owZDPeC", function(e, j) {
              if (j.features.length)
                m.requestExtract(j.features[0], true);
              else
                m.searchError(query);
            });
          } else if (d3.selectAll(".city")[0].length == 0){
            document.getElementById("search_input").value = json.features[0].properties.label;
            m.requestExtract(json.features[0]);
          } else if (countrySearch){
            m.zoomMap(json.features[0].bbox);
            document.getElementById("search_input").value = query;
            m.filterList(query);
            window.scroll(0,0);
          } else {
            m.zoomMap(json.features[0].bbox);
            m.clearRequest();
          }
        });
      }
    },
    zoomMap : function(bbox) {
      displayMap.fitBounds([[bbox[1],bbox[0]],[bbox[3], bbox[2]]]);
    },
    requestExtract : function(metro, noWOF) {
      var bbox = metro.bbox ? metro.bbox : metro.geometry.coordinates.concat(metro.geometry.coordinates),
        zoomOut = (bbox[0] == bbox[2]) ? 8 : 1;
      this.zoomMap(bbox);
      displayMap.zoomOut(zoomOut);

      var geoID = metro.properties.id;
      d3.select("input[name='wof_id']").attr("value",geoID);
      d3.select("input[name='wof_name']").attr("value",metro.properties.label);

      requestBoundingBox = this.calculateNewBox(bbox);

      this.drawRequestBox();
      d3.select("#map").classed("request-mode",true);

      if (metro.type == "Feature" && !noWOF)
        d3.json(wofPrefix.replace('GEOID', geoID), function(data){
          outline = L.geoJson(data.geometry, { className : "outline" }).addTo(displayMap);
          displayMap.addLayer(outline);
        });

      var p1 = L.latLng(bbox[1],bbox[0]),
        p2 = L.latLng(bbox[3],bbox[2]);
      var encompassed = [{
        country : "Encompassing Metros",
        metros : []
      }];
      extractLayers.forEach(function(l){
        if (l.getBounds().contains(p1) && l.getBounds().contains(p2)) 
          encompassed[0].metros.push({
            name : l.feature.properties.display_name,
            href : l.feature.properties.href,
            country : l.feature.properties.name.split("_")[1],
            bbox : l.feature.bbox
          })
      });

      var requestDiv = d3.select("#request-wrapper");

      requestDiv.select("#make-request")
        .style("display","block")
        .selectAll(".name").text(metro.properties.name);

      if (encompassed[0].metros.length){
        requestDiv.attr("class","filtered-encompassed");
        this.drawList(encompassed, geoID, metro.properties.name, noWOF);
        return;
      }

      var biggestDist = Math.max(requestBoundingBox[1][1] - requestBoundingBox[0][1], requestBoundingBox[1][0] - requestBoundingBox[0][0]);
      if (biggestDist > 5)
        requestDiv.attr("class","filtered-request-greater-5");
      else if (biggestDist > 1)
        requestDiv.attr("class","filtered-request-greater-1");
      else
        requestDiv.attr("class","filtered-default");
    },
    clearMap : function() {
      if (rect) displayMap.removeLayer(rect);
      if (outline) displayMap.removeLayer(outline);
      dots.forEach(function(l){
        displayMap.removeLayer(l);
      });
      dots = [];
    },
    clearRequest : function() {
      this.clearMap();
      d3.select("#map").classed("request-mode",false);
      d3.select("#request-wrapper").attr("class","");
      d3.select("#make-request").style("display","none");
    },
    calculateOffset : function(theta, d, lat1, lng1) {
      var lat1 = lat1.toRad(), 
        lng1 = lng1.toRad(),
        R = 6371;

      var lat2 = Math.asin( Math.sin(lat1)*Math.cos(d/R) 
            + Math.cos(lat1)*Math.sin(d/R)*Math.cos(theta) ),
        lng2 = lng1 + Math.atan2(Math.sin(theta)*Math.sin(d/R)*Math.cos(lat1), 
              Math.cos(d/R)-Math.sin(lat1)*Math.sin(lat2));

      return [lat2.toDeg(), lng2.toDeg()];
    },
    calculateNewBox : function(bbox) {
      var d = Math.sqrt(Math.pow(bbox[3]-bbox[1],2) + Math.pow(bbox[2]-bbox[0], 2))*25,
        distance = (d == 0) ? 25 : d,
        northEast = this.calculateOffset(-Math.PI*3/4, distance, bbox[1], bbox[0]),
        southWest = this.calculateOffset(Math.PI/4, distance, bbox[3], bbox[2]);
      return [northEast, southWest];
    },
    drawRequestBox : function() {
      this.clearMap();
      var m = this;
      rect = new L.Rectangle(new L.LatLngBounds(requestBoundingBox), { className : "blue" });
      displayMap.addLayer(rect);
      
      var myIcon = L.divIcon({className: 'drag-icon'});

      var cSW = new L.marker(requestBoundingBox[0], { icon : myIcon, draggable: true });
      dots.push(cSW);
      var cNE = new L.marker(requestBoundingBox[1], { icon : myIcon, draggable: true });
      dots.push(cNE);

      cSW.on("drag",function(e){
        requestBoundingBox[0] = [e.target.getLatLng().lat, e.target.getLatLng().lng];
        m.redrawBox();
      });
      cNE.on("drag",function(e){
        requestBoundingBox[1] = [e.target.getLatLng().lat, e.target.getLatLng().lng];
        m.redrawBox();
      });

      dots.forEach(function(l){
        displayMap.addLayer(l);
      });
      this.fillRequestForm();
    },
    redrawBox : function() {
      displayMap.removeLayer(rect);
      rect = new L.Rectangle(new L.LatLngBounds(requestBoundingBox), { className : "blue" });
      displayMap.addLayer(rect);
      this.fillRequestForm();
    },
    fillRequestForm : function() {
      d3.select("input[name='bbox_n']").attr("value",requestBoundingBox[1][0]);
      d3.select("input[name='bbox_w']").attr("value",requestBoundingBox[0][1]);
      d3.select("input[name='bbox_s']").attr("value",requestBoundingBox[0][0]);
      d3.select("input[name='bbox_e']").attr("value",requestBoundingBox[1][1]);
    }
  }
  return MetrosApp;
}