
$(document).ready(function(){
	var xhr = null;
	$('.geoparsepy-spinner').hide();

	$('#loading-data-spinner').hide();


	$("#form-text-upload").on("submit", function(e){
		// Prevent multiple AJAX calls. 
		// if(xhr && xhr.readyState != 4){ xhr.abort(); e.preventDefault(); return false;}
		document.getElementById("OSMURI-container").style.visibility="visible";

		image_caption = $("#text-input").val();
		uploaded_file = document.getElementById("file-upload");
		console.log(uploaded_file.files[0]);
		// If the filename is too long then shorten.

		var fileName = uploaded_file.value.split("\\").pop();
		if (fileName.length > 22) {
			fileName = fileName.substring(0, 10) + "..." + fileName.substring(fileName.length - 10, fileName.length);
		}

		// If the file size is bigger than 32MB then don't submit.
		var filesize = uploaded_file.files[0].size / 1024 / 1024;
	  	if (filesize > 32) {
	  		var message =  "File size of " + filesize.toFixed(1) + "MB exceeds limit of 32MB";
	  		$('#geoparse-link-result').empty();
	  		$('#geoparse-link-result').showError(message);
	  	} else {
	  		// Show the filename in the input box.
			$("#file-upload").siblings(".custom-file-label-x").removeClass("form-control-placeholder").addClass("selected").html(fileName);

			// Clear any error messages and show loading bar.
			document.getElementById("geoparse-link-result").innerHTML="";
			$('.geoparsepy-spinner').show();

			var form_data = new FormData();
        	var files = uploaded_file.files[0];
	    	form_data.append('image_caption', image_caption);
        	form_data.append('image', files);

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
	  	}

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
				if (k == "confidence")
					document.getElementById("geoparse-link-result").innerHTML+='<br><li>'+k+': '+response[k]+'\%</li>';
				else
					document.getElementById("geoparse-link-result").innerHTML+='<br><li>'+k+': '+response[k]+'</li>';
			}
			// document.getElementById("geoparse-link-result").innerHTML+='<br><li>'+k+': '+response[k]+'</li>';
        	// window.open(response['geolink']);


        }
        else
        	document.getElementById("geoparse-link-result").innerHTML="Text was parsed but nothing was returned :/";
	}

	function displayOSMURIError(response){
		console.log("Error occured in parsing");
		$('.geoparsepy-spinner').hide();
		document.getElementById("geoparse-link-result").innerHTML='Geoparsepy encountered an interal error';
	}

	function databaseLoaded(response){
		console.log("database loaded...");
	}

	$(window).keydown(function(event){
	    if(event.keyCode == 13) {
	      event.preventDefault();
	      return false;
	    }
  	});

  	$("#file-upload").change(function(){
  		var fileName = $(this).val().split("\\").pop();
		if (fileName.length > 22) {
			fileName = fileName.substring(0, 10) + "..." + fileName.substring(fileName.length - 10, fileName.length);
		}

	    document.getElementById('file-upload-label').innerHTML = fileName;
  	});

});
