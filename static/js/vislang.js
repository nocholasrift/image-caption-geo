
$(document).ready(function(){
	var xhr = null;
	// document.getElementById("OSMURI-container").style.visibility="hidden";

	$('#loading-data-spinner').hide();


	$("#form-text-upload").on("submit", function(e){
		// Prevent multiple AJAX calls. 
		// if(xhr && xhr.readyState != 4){ xhr.abort(); e.preventDefault(); return false;}

		$('.geoparsepy-spinner').show();
		document.getElementById("geoparse-link-result").innerHTML="";

		image_caption = $("#text-input").val()

  		// Prepare data to be sent with form.
  		var form_data = new FormData();
    	form_data.append('image_caption', image_caption);

		console.log(image_caption);
    	// Submit the form using an asynchronous call.
  		xhr = $.ajax({
            url: 'simple-demo',
            type: 'post',
            data: form_data,
            contentType: false,
            processData: false,
            success: displayOSMURI,
            error: displayOSMURIError,
        });

  		// Avoid a browser POST request.
        e.preventDefault();
        return false;
	});

	function displayOSMURI(response){
		console.log("response received!");
		$('.geoparsepy-spinner').hide();
		if(response != 0){
			console.log("Loading up response now");
			document.getElementById("geoparse-link-result").innerHTML='Text was parsed: <a href="'+response['geolink']+'">'+response['geolink']+'</a>';
			for (let k in response){
				if (k == "geolink") 	continue;
				document.getElementById("geoparse-link-result").innerHTML+='<br><li>'+k+': '+response[k]+'</li>';
			}
        	// window.open(response['geolink']);

        }
	}

	function displayOSMURIError(response){
		console.log("Error occured in parsing");
		$('.geoparsepy-spinner').hide();
		document.getElementById("geoparse-link-result").innerHTML='Geoparsepy encountered an interal error';
	}

	function databaseLoaded(response){
		console.log("database loaded...");
	}

})