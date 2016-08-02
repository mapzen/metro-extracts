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
    keyIndex = -1,
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

      var divHeight = document.getElementById("list-wrapper").offsetHeight,
        processScroll = true;
      if (window.innerWidth > 768)
        window.onscroll = doThisStuffOnScroll;

      function doThisStuffOnScroll() {
        if (!processScroll) return;
        if (d3.select("#content-wrapper").attr("class") && 
          d3.select("#content-wrapper").attr("class").indexOf("filtered") != -1) return;

        processScroll = false;
        var scrollTop = (window.pageYOffset !== undefined) ? window.pageYOffset : (document.documentElement || document.body.parentNode || document.body).scrollTop;
        if (scrollTop > divHeight - window.innerHeight + 56)
          d3.select("#map").style({
            "position" : "absolute",
            "top" : (divHeight - window.innerHeight + 56) + "px",
            "width" : "200%"
          });
        else
          d3.select("#map").style({
            "position" : "fixed",
            "width" : "inherit",
            "top" : "56px"
          });
        setTimeout(function(){ processScroll = true; }, 50);
      }
      
      return this;
    },
    initDisplayMap : function() {
      var options = {
          dragging: (window.self !== window.top && L.Browser.touch) ? false : true,
          tap: (window.self !== window.top && L.Browser.touch) ? false : true,
          scrollWheelZoom: false,
          scene: sceneURL,
          center: [20,0],
          zoom: (window.innerWidth > 768) ? 2 : 1,
          attribution: '<a href="https://mapzen.com/tangram">Tangram</a> | <a href="http://www.openstreetmap.org/copyright">&copy; OSM contributors</a> | <a href="https://mapzen.com/">Mapzen</a>',
          fallbackTile: L.tileLayer('https://stamen-tiles.a.ssl.fastly.net/toner-lite/{z}/{x}/{y}.png', {
            attribution: 'Map tiles by <a href="http://stamen.com">Stamen Design</a>'})
        };
      displayMap = L.Mapzen.map('map', options);

      displayMap.on('zoomend', function() {
          d3.select(".leaflet-map-pane").attr("class","leaflet-map-pane z-"+displayMap.getZoom());
      });

      // add popular extracts to map and bind a link to their page on click
      var onEachFeature = function (feature, layer) {
        extractLayers.push(layer);
        layer.bindPopup("<a href='"+feature.properties.href+"'>"+feature.properties.display_name+"</a>");

        var label = L.marker(layer.getBounds().getSouthWest(), {
          icon: L.divIcon({
            className: 'label',
            html: "<a href='"+feature.properties.href+"'>"+feature.properties.display_name+"</a>"
          })
        }).addTo(displayMap);
      }

      d3.json(geoJSONUrl, function(data){
        L.geoJson(data, { onEachFeature: onEachFeature, className : "red" }).addTo(displayMap);
      });
    },
    filterList : function(str, displayList) {
      // populates the list of countries and cities on the right
      var newData = [];
      str = str.toLowerCase().replace(/\W/g, '');
      nestedCities.forEach(function(d){
        // if str matches a country, include that whole country
        if (d.country.toLowerCase().replace(/\W/g, '').indexOf(str) != -1) {
          newData.push(d);
        } else {
        // else, look at individual cities
          var c = {
            country : d.country,
            metros : []
          }
          d.metros.forEach(function(e){ 
            if (e.name.toLowerCase().replace(/\W/g, '').indexOf(str) != -1)
              c.metros.push(e);
          });
          if (c.metros.length) newData.push(c);
        }
      });
      if (displayList) this.drawList(newData);
      return newData;
    },
    hideList : function() {
      d3.select("#content-wrapper").attr("class","filtered-typing");
    },
    drawList : function(data, request_id, display_name, noWOF) {
      // if no cities match the query, hide "popular extracts" via css
      d3.select("#content-wrapper").classed("filtered",!data.length);

      // d3 function to add list dom elements to the page
      var countries = d3.select("#extracts").selectAll(".country").data(data);
      var enterCountries = countries.enter().append("div").attr("class","country");
      countries.exit().remove();
      enterCountries.append("div").attr("class","country-name")
      var m = this;
      countries.classed("no-line", function(d){ return !d.country; }) //class for encompassed state
        .select(".country-name")
          .text(function(d){ return d.country; })
          .on("click",function(d){
            m.onSubmit(d.country, true);
          });
      var cities = countries.selectAll(".city").data(function(d){ return d.metros; });
      cities.enter().append("a").attr("class","city");
      cities.text(function(d){ return d.name; })
        .attr("href",function(d){
          // if we got to this list via encomapssed metro, save a reference to the
          // wof_id for the metro page to show the outline
          if (noWOF) return d.href;
          else return d.href + (request_id ? escape(request_id)+"/"+escape(display_name) : ""); });
      cities.exit().remove();
    },
    doSuggestion : function(query) {
      var list = this.filterList(query);
      // autocomplete dropdown list request
      if (xhr) xhr.abort();
      var m = this;
      xhr = d3.json("https://search.mapzen.com/v1/autocomplete?text="+query+"&sources=wof&api_key=search-owZDPeC", function(error, json) {
        if (json.length)
          m.showSuggestions(json, list);
        else 
          d3.json("https://search.mapzen.com/v1/autocomplete?text="+query+"&layers=neighbourhood,locality,borough,localadmin,county,macrocounty,region,macroregion,country&api_key=search-owZDPeC", function(err, results) {
            m.showSuggestions(results, list);
          });
      });
    },
    showSuggestions : function(data, list) {
      // add the title at the top of autocomplete
      if (data.features.length)
        data.features.unshift({
          label : true,
          text : "To make a new extract:"
        });

      if (list.length && list.length < 5) {
        var cities = [];
        list.map(function(d){ cities = cities.concat(d.metros); });
        data.features = cities.concat(data.features);
        data.features.unshift({
          label : true,
          text : "To download an extract right now:"
        });
      }

      var suggestion = d3.select(".autocomplete")
        .selectAll(".suggestion").data(data.features);
      suggestion.enter().append("div");
      suggestion.attr("class",function(d,i) {
          // save a dom reference to the first autocomplete suggestion
          // in case people hit enter mid-typing so it defaults to first autocomplete
          var labelClass = (d.label && d.text == "To make a new extract:") ? "label" : "label red";
          return "suggestion " + (d.label ? labelClass : "hit");
        });
      suggestion.exit().remove();
      var m = this;
      suggestion.html(function(d){
        // appends .layer to account for different WOF areas that have the same label (ex. Tokyo)
        if (d.label) return d.text;
        else if (d.name) return "<a href="+d.href+">"+d.name+"</a>";
        else return d.properties.label + "<span class='layer'>(" + d.properties.layer + ")</span>"; 
      }).on("click",function(d){
        if (d.label || d.name) return;
        m.searchOnSuggestion(d);
      });
    },
    searchOnSuggestion : function(d) {
      if (d.name)
          window.location.href = d.href;
      else {
        placeID = d.properties.source + ":" + d.properties.layer + ":" + d.properties.id;
        document.getElementById("search_input").value = d.properties.label;
        this.onSubmit(d.properties.label);
      }
    },
    selectSuggestion : function() {
      // for handling keyboard input on the autocomplete list
      var currentList = d3.selectAll(".hit");
      currentList.each(function(d, i){ 
        if (i == keyIndex) {
          document.getElementById("search_input").value = d.name ? d.name : d.properties.label;
          if (d.name)
            placeID = d.href;
          else
            placeID = d.properties.source + ":" + d.properties.layer + ":" + d.properties.id;
        }
      }).classed("selected",function(d,i){ return i == keyIndex; });
    },
    onSubmit : function(val) {
      // submit of search box
      keyIndex = -1;
      d3.selectAll(".suggestion").remove();
      this.doSearch(val);
      this.hideList();
      placeID = null;
    },
    searchError : function(query) {
      // no search results anywhere, ex. sdfsdafasdf
      d3.select("#content-wrapper").attr("class","filtered-error");
      d3.select("#search-error").select(".name").text(query);
    },
    clearSearchBox : function() {
      // triggered by "x" click or an empty search box
      document.getElementById("search_input").value = "";
      d3.select(".fa-times").style("display","none");
      this.drawList(nestedCities);
      d3.selectAll(".suggestion").remove();
      placeID = null;
      this.clearRequest();
    },
    processKeyup : function(event) {
      // master function for responding to the search box
      var inputDiv = document.getElementById("search_input");
      var val = inputDiv.value;
      var m = this;

      if (!val.length) {
        this.clearSearchBox();
        return;
      }

      d3.select(".fa-times").style("display","inline-block");

      if (event.keyCode == 40) { //arrow down
        keyIndex = Math.min(keyIndex+1, d3.selectAll(".hit")[0].length-1);
        this.selectSuggestion();   

      } else if (event.keyCode == 38) { //arrow up
        keyIndex = Math.max(keyIndex-1, 0);
        this.selectSuggestion();

      } else if (event.keyCode == 13) { //enter
        // if there are autocomplete suggestions and up/down keys were unused
        if (d3.selectAll(".hit")[0].length && keyIndex == -1)
          d3.select(".hit").each(function(d){ m.searchOnSuggestion(d); });
        else
          this.onSubmit(val);

      } else if (event.keyCode != 8 && (event.keyCode < 48 || event.keyCode > 90)) {
        // restrict autocomplete to 0-9,a-z character input, excluding delete
        return;

      } else {
        // general case of typing to filter list and get autocomplete suggestions
        keyIndex = -1;
        placeID = null;
        this.doSuggestion(val);
        this.hideList();
      }
    },
    doSearch : function(query, countrySearch) {
      d3.selectAll(".suggestion").remove();
      var m = this;

      // case if the search was selected from autocomplete
      if (placeID) {
        if (placeID.charAt(0) == "/")
          window.location.href = placeID;
        else
          d3.json("https://search.mapzen.com/v1/place?api_key=search-owZDPeC&ids="+placeID, function(error, json){
            m.requestExtract(json.features[0]);
          });
      } else {
        d3.json("https://search.mapzen.com/v1/search?text="+query+"&sources=wof&api_key=search-owZDPeC", function(error, json) {
          if (countrySearch){
            // if a country name was clicked from the list
            m.zoomMap(json.features[0].bbox);
            document.getElementById("search_input").value = query;
            m.filterList(query, true);
            window.scroll(0,0);
          } else if (json.features.length) {
            // if WOF returns a result
            document.getElementById("search_input").value = json.features[0].properties.label;
            m.requestExtract(json.features[0]);
          } else {
            // if WOF returns no results, hit the regular search API
            d3.json("https://search.mapzen.com/v1/search?text="+query+"&api_key=search-owZDPeC", function(e, j) {
              if (j.features.length)
                m.requestExtract(j.features[0], true);
              else
                m.searchError(query);
            });
          }
        });
      }
    },
    zoomMap : function(bbox) {
      displayMap.fitBounds([[bbox[1],bbox[0]],[bbox[3], bbox[2]]]);
    },
    requestExtract : function(metro, noWOF) {
      // big function for creating a custom metro
      var bbox = metro.bbox ? metro.bbox : metro.geometry.coordinates.concat(metro.geometry.coordinates),
        zoomOut = (bbox[0] == bbox[2]) ? 8 : 1;
      this.zoomMap(bbox);
      // zoomout to account for Point geometry, and zooming far enough out to see the box
      displayMap.zoomOut(zoomOut);

      var geoID = metro.properties.id;
      d3.select("input[name='wof_id']").attr("value",geoID);
      d3.select("input[name='wof_name']").attr("value",metro.properties.label);
      d3.select("input[name='display_name']").attr("value",metro.properties.label);

      // blue box on map
      requestBoundingBox = this.calculateNewBox(bbox);

      this.drawRequestBox();
      // change red fill boxes to red outlines
      d3.select("#map").classed("request-mode",true);

      // if we have WOF outline data, show this
      if (metro.type == "Feature" && !noWOF)
        d3.json(wofPrefix.replace('GEOID', geoID), function(data){
          if (!data) return;
          outline = L.geoJson(data.geometry, { className : "outline" }).addTo(displayMap);
          displayMap.addLayer(outline);
        });

      var wrapperDiv = d3.select("#content-wrapper");

      // personalize request button
      wrapperDiv.select("#make-request")
        .style("display","block")
        .selectAll(".name").text(metro.properties.name);

      // add appropriate css classes if the extract is too large
      var size = this.checkSize();
      // if it's larger than 5deg, don't bother looking for encompassing
      if (size > 5) return;

      // check to see if popular extracts encompass the request
      var p1 = L.latLng(bbox[1],bbox[0]),
        p2 = L.latLng(bbox[3],bbox[2]);
      var encompassed = [{
        country : null,
        metros : []
      }];
      // go through boxes on map to check .contains()
      extractLayers.forEach(function(l){
        if (l.getBounds().contains(p1) && l.getBounds().contains(p2)) 
          encompassed[0].metros.push({
            name : l.feature.properties.display_name,
            href : l.feature.properties.href,
            country : l.feature.properties.name.split("_")[1],
            bbox : l.feature.bbox
          })
      });

      if (encompassed[0].metros.length){
        wrapperDiv.attr("class","filtered-encompassed");
        this.drawList(encompassed, geoID, metro.properties.name, noWOF);
        return;
      }
    },
    checkSize : function() {
      // check the size of the request. we add a warning on >1deg, and fail on >5deg
      var wrapperDiv = d3.select("#content-wrapper");
      var lngDiff = Math.abs(requestBoundingBox[1][1] - requestBoundingBox[0][1]),
        latDiff = Math.abs(requestBoundingBox[1][0] - requestBoundingBox[0][0]),
        biggestDist = Math.max(latDiff, lngDiff);
      if (biggestDist > 5)
        wrapperDiv.attr("class","filtered-request-greater-5");
      else if (biggestDist > 1)
        wrapperDiv.attr("class","filtered-request-greater-1");
      else
        wrapperDiv.attr("class","filtered-default");
    },
    clearMap : function() {
      // leaflet redraw function
      if (rect) displayMap.removeLayer(rect);
      if (outline) displayMap.removeLayer(outline);
      dots.forEach(function(l){
        displayMap.removeLayer(l);
      });
      dots = [];
    },
    clearRequest : function() {
      // remove custom extract request state
      this.clearMap();
      displayMap.setView([20,0],2);
      d3.select("#map").classed("request-mode",false);
      d3.select("#content-wrapper").attr("class","");
      d3.select("#make-request").style("display","none");
    },
    calculateOffset : function(theta, d, lat1, lng1) {
      // we are setting request box slightly outside of the wof bbox
      // this funciton calculates the new latlng points via trig
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
      // calculates a relative distance offset, vs. an absolute (ex. 25km)
      // so that neighborhoods and countries have a proportional offset
      var d = Math.sqrt(Math.pow(bbox[3]-bbox[1],2) + Math.pow(bbox[2]-bbox[0], 2))*10,
        distance = (d == 0) ? 10 : d,
        northEast = this.calculateOffset(-Math.PI*3/4, distance, bbox[1], bbox[0]),
        southWest = this.calculateOffset(Math.PI/4, distance, bbox[3], bbox[2]);
      return [northEast, southWest];
    },
    drawRequestBox : function() {
      // general function for drawing the request box, dots, and filling the form with
      // appropriate bbox info
      this.clearMap();
      var m = this;
      rect = new L.Rectangle(new L.LatLngBounds(requestBoundingBox), { className : "blue" });
      displayMap.addLayer(rect);
      
      this.drawDots();

      this.fillRequestForm();
    },
    drawDots : function() {
      // drawing and redrawing the dots for drag events

      dots.forEach(function(l){
        displayMap.removeLayer(l);
      });
      dots = [];

      var m = this;

      var myIcon = L.divIcon({className: 'drag-icon'}),
        dotOptions = { icon : myIcon, draggable: true };

      // [northEast, southWest] 
      dots = [
        new L.marker(requestBoundingBox[0], dotOptions),
        new L.marker(requestBoundingBox[1], dotOptions),
        new L.marker([requestBoundingBox[0][0], requestBoundingBox[1][1]], dotOptions),
        new L.marker([requestBoundingBox[1][0], requestBoundingBox[0][1]], dotOptions)
      ];

      // if there's a better way to do this, please someone fix
      // keeping a reference to each dot affected on drag, becuase redrawing all
      // four at once is not possible
      dots[0].on("drag",function(e){
        requestBoundingBox[0] = [e.target.getLatLng().lat, e.target.getLatLng().lng];

        // NE dot affects NW and SE on drag
        displayMap.removeLayer(dots[2]);
        displayMap.removeLayer(dots[3]);
        dots[2] = new L.marker([requestBoundingBox[0][0], requestBoundingBox[1][1]], dotOptions);
        dots[3] = new L.marker([requestBoundingBox[1][0], requestBoundingBox[0][1]], dotOptions);
        displayMap.addLayer(dots[2]);
        displayMap.addLayer(dots[3]);

        m.redrawBox();
      });
      dots[1].on("drag",function(e){
        requestBoundingBox[1] = [e.target.getLatLng().lat, e.target.getLatLng().lng];

        // SW dot affects NW and SE on drag
        displayMap.removeLayer(dots[2]);
        displayMap.removeLayer(dots[3]);
        dots[2] = new L.marker([requestBoundingBox[0][0], requestBoundingBox[1][1]], dotOptions);
        dots[3] = new L.marker([requestBoundingBox[1][0], requestBoundingBox[0][1]], dotOptions);
        displayMap.addLayer(dots[2]);
        displayMap.addLayer(dots[3]);

        m.redrawBox();
      });
      dots[2].on("drag",function(e){
        requestBoundingBox[0][0] = e.target.getLatLng().lat;
        requestBoundingBox[1][1] = e.target.getLatLng().lng;

        // SE dot affects NE and SW on drag
        displayMap.removeLayer(dots[0]);
        displayMap.removeLayer(dots[1]);
        dots[0] = new L.marker(requestBoundingBox[0], dotOptions);
        dots[1] = new L.marker(requestBoundingBox[1], dotOptions);
        displayMap.addLayer(dots[0]);
        displayMap.addLayer(dots[1]);

        m.redrawBox();
      });
      dots[3].on("drag",function(e){
        requestBoundingBox[1][0] = e.target.getLatLng().lat;
        requestBoundingBox[0][1] = e.target.getLatLng().lng;

        // NW dot affects NE and SW on drag
        displayMap.removeLayer(dots[0]);
        displayMap.removeLayer(dots[1]);
        dots[0] = new L.marker(requestBoundingBox[0], dotOptions);
        dots[1] = new L.marker(requestBoundingBox[1], dotOptions);
        displayMap.addLayer(dots[0]);
        displayMap.addLayer(dots[1]);

        m.redrawBox();
      });

      dots.forEach(function(l){
        displayMap.addLayer(l);
        l.on("dragend", function(){
          m.drawDots();
          m.checkSize();
        });
      });
    },
    redrawBox : function() {
      // helper function for only redrawing the box
      displayMap.removeLayer(rect);
      rect = new L.Rectangle(new L.LatLngBounds(requestBoundingBox), { className : "blue" });
      displayMap.addLayer(rect);
      this.fillRequestForm();
    },
    fillRequestForm : function() {
      d3.select("input[name='bbox_n']").attr("value",Math.max(requestBoundingBox[1][0], requestBoundingBox[0][0]));
      d3.select("input[name='bbox_w']").attr("value",Math.min(requestBoundingBox[1][1], requestBoundingBox[0][1]));
      d3.select("input[name='bbox_s']").attr("value",Math.min(requestBoundingBox[1][0], requestBoundingBox[0][0]));
      d3.select("input[name='bbox_e']").attr("value",Math.max(requestBoundingBox[1][1], requestBoundingBox[0][1]));
    }
  }
  return MetrosApp;
}