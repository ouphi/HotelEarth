/* Creation of the 3D Earth */
var viewer = new Cesium.Viewer('cesiumContainer', {
    navigationHelpButton: false,
    animation: false,
    timeline: false
});
viewer.terrainProvider = new Cesium.CesiumTerrainProvider({
    url : 'https://assets.agi.com/stk-terrain/world',
    requestVertexNormals : true,
    requestWaterMask: true
});
viewer.scene.globe.depthTestAgainstTerrain = true;
var layers = viewer.scene.imageryLayers;
var bingLabels = layers.addImageryProvider(new Cesium.BingMapsImageryProvider({
    url : 'https://dev.virtualearth.net',
    mapStyle : Cesium.BingMapsStyle.AERIAL_WITH_LABELS
}));
var blackMarble = layers.addImageryProvider(Cesium.createTileMapServiceImageryProvider({
    url : 'https://cesiumjs.org/blackmarble',
    credit : 'Black Marble imagery courtesy NASA Earth Observatory',
    flipXY : true
}));
blackMarble.alpha = 0.5;
blackMarble.brightness = 2;

/* Event loop for the globe */
var cartographic = new Cesium.Cartographic();
var cartesian = new Cesium.Cartesian3();
var camera = viewer.scene.camera;
var ellipsoid = viewer.scene.mapProjection.ellipsoid;
viewer.clock.onTick.addEventListener(function(clock) {
    ellipsoid.cartesianToCartographic(camera.positionWC, cartographic);
    var height = (cartographic.height * 0.001).toFixed(1);
    if (height > 5000) {
    	blackMarble.alpha = 0.5;
    	viewer.terrainProvider.requestWaterMask = true
    } else if (height < 1000) {
    	blackMarble.alpha = 0;
    	viewer.terrainProvider.requestWaterMask = false
    } else {
    	blackMarble.alpha = 0.5 - (5000 - height)/8000;
    }
    if (height > 1400)
    	bingLabels.alpha = 0
    else if (height > 400)
    	bingLabels.alpha = (1400 - height)/1000;
    else
    	bingLabels.alpha = 1
    	
    if (rotateAround && !flyingOver) {
	    var lat = rotateAround.lat;
	    var lon = rotateAround.lon;
	    var lookAt = new Cesium.Cartesian3.fromDegrees(lon, lat, 100);
	    var t = clock._currentTime.secondsOfDay*6.28/10;
	    lat += Math.cos(t/4)/3200;
	    lon += Math.sin(t/4)/3200;
	    viewer.camera.setView({
		    destination : new Cesium.Cartesian3.fromDegrees(lon, lat, 550 + Math.cos(t/16)*150),
		    orientation: {
		        heading : Cesium.Math.toRadians(180.0*Math.cos(t/32 + 3.14)), // east, default value is 0.0 (north)
		        pitch : Cesium.Math.toRadians(-35 - Math.cos(t/16)*30),    // default value (looking down)
		        roll : 0.0                             // default value
		    }
		});
    }
});

/* FlyOver Helper */
var rotateAround = false, flyingOver = false, coloredCircle = null;
function flyOver(lat, lon) {
	if (coloredCircle) {
		viewer.entities.remove(coloredCircle);
		coloredCircle = null;	
	}
	coloredCircle = viewer.entities.add({
	    position: Cesium.Cartesian3.fromDegrees(lon, lat),
	    name : 'Colored circle on surface with outline',
	    ellipse : {
	        semiMinorAxis : 30.0,
	        semiMajorAxis : 30.0,
	        material : Cesium.Color.RED.withAlpha(0.5),
	        outline : true,
	        outlineColor : Cesium.Color.RED
	    }
	})
	flyingOver = true;
	rotateAround = undefined
	var destination = new Cesium.Cartesian3.fromDegrees(lon, lat, 700)
	var dist = Cesium.Cartesian3.distance(camera.position, destination)/1000;
	viewer.camera.flyTo({
        destination : destination,
        duration: 4,
        easingFunction: Cesium.EasingFunction.CUBIC_IN_OUT,
        complete: function() {		
			rotateAround = {lat: lat, lon: lon};
			setTimeout(function() {
		        flyingOver = false;
			}, 4000);
	    }
	});
}


/* Vue.JS business */
var vue = new Vue({
  el: '#hotel-earth-ui',
  mounted : function() {
	  $(".cesium-viewer-animationContainer, .cesium-viewer-timelineContainer, .cesium-viewer-bottom, .cesium-viewer-toolbar").remove();
  },
  data: {
    hotels: [],
    query: null,
    network_error: false,
    current_hotel: null,
    final_searchbar: false 
  },
  methods: {
	  displaySwipebox: function() {
		var pictures = [];
		for (var i = 0; i < this.current_hotel._source.pictures.length; i++)
			if (this.current_hotel._source.pictures[i] && this.current_hotel._source.pictures[i] != "#")
				pictures.push({href: this.current_hotel._source.pictures[i], title: String(i+1)+" / "+String(this.current_hotel._source.pictures.length)})
		$.swipebox(pictures); 
	  },
	  prettifyDescription: function(description) {
		  description = description.trim().replace(/\n+/g, '<br /><br />');
		  var splitAt = description.indexOf("We speak your language!");
		  var descriptionBefore = description.substring(0, splitAt);
		  var descriptionAfter = description.substring(splitAt);
		  descriptionAfter = descriptionAfter.replace(/<br \/><br \/>/g, "<br />");
		  descriptionAfter = descriptionAfter.replace("Hotel Chain<br />:<br />", "Hotel Chain: ")
		  return descriptionBefore + descriptionAfter;
	  },
	  releaseCamera: function() {
		rotateAround = false;
		flyingOver = true;
		var lon = this.current_hotel._source.longitude;
		var lat = this.current_hotel._source.latitude;
		viewer.camera.flyTo({
			destination : new Cesium.Cartesian3.fromDegrees(lon, lat, 550),
			duration: 1,
			complete: function() {
				flyingOver = false;
				var shouldShowHelpPopup = true;
				try {
					shouldShowHelpPopup = localStorage.getItem("didShowCameraHelpPopup") != "true";
					localStorage.setItem("didShowCameraHelpPopup", "true");
				} catch(err) {
					shouldShowHelpPopup = true;
				}
				if (shouldShowHelpPopup)
					alert("Use the mouse and the CTRL/SHIFT buttons to move around this hotel's position.");
			}
		});
	  },
	  flyBack: function() {
		var self = this;
		var lat = self.current_hotel._source.latitude;
		var lon = self.current_hotel._source.longitude;
		self.current_hotel = null;
		var height = 1400;
		flyingOver = true;
		rotateAround = false;
		viewer.camera.flyTo({
			destination : new Cesium.Cartesian3.fromDegrees(lon, lat, height),
			duration: 2,
			complete: function() {flyingOver = false}
		});
	  },
	  flyOver: function(hotel) {
		  this.current_hotel = hotel;
		  flyOver(hotel._source.latitude, hotel._source.longitude)
	  },
	  elasticSearchOnKeyUp: function(item) {
		  if ($("aside").hasClass("final"))
		  	this.elasticSearch(item);
	  },
	  elasticSearch: function(item) {
		var self = this;
		var data = {
		   from : 0,
		   size : 50,
		   query: {
		        multi_match: {
		            query:  item.srcElement.value,
		            type:   "most_fields",
		            fields: [ "city", "country", "name", "description" ]
		        }
		    }
		};
		$.ajax({
		  method: "POST",
		  url: window.location.href+"api/_search",
			beforeSend: function(xhr) { 
			  xhr.setRequestHeader("Authorization", "Basic " + btoa("elastic:changeme")); 
			},
		  data: JSON.stringify(data),
		  dataType : 'json',
		  contentType: 'application/json',
		})
		.done(function( data ) {
			self.network_error = false;
			self.final_searchbar = true;
			self.hotels = data.hits.hits;
			if (!$("aside").hasClass("final")) {
				$("#searchBar, aside, #cesiumContainer").addClass("final");
				
			}
			if (self.hotels.length == 0)
				return;
			var lat = self.hotels[0]._source.latitude;
			var lon = self.hotels[0]._source.longitude;
			var height = 10320589;
			if (!flyingOver)
				viewer.camera.flyTo({
					destination : new Cesium.Cartesian3.fromDegrees(lon, lat, height),
					duration: 2
				});
		})
		.fail(function( data ) {
		  self.hotels = [];
		  self.network_error = true;
		});
	}
  }
})


$(window).load(function() {
	if( /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ) {
		alert("Dear visitor, we prefer if you use a desktop or a laptop to visit this website :)");
	} else {
		$("body").css('opacity', '1');
	}
})