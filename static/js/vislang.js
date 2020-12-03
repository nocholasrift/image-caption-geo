
$(document).ready(function(){
	var xhr = null;
	$('.geoparsepy-spinner').hide();

	$('#loading-data-spinner').hide();
	$('#uploadedImg').hide();


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
			$('#uploadedImg').show();
			document.getElementById("image-caption").innerHTML=image_caption;
	  		// Show the filename in the input box.
			$("#file-upload").siblings(".custom-file-label-x").removeClass("form-control-placeholder").addClass("selected").html(fileName);
			var reader = new FileReader();
            reader.onload = displayUploadedImage;
            reader.readAsDataURL(uploaded_file.files[0]);
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

	function getColor(numb){
		if(numb < 35){
			return "red";
		} 
		if(numb < 70){
			return "orange";
		} 
		return 'limegreen'
	}

	function displayUploadedImage(e){
		$('#uploadedImg').attr('src', e.target.result);
	}

	function displayOSMURI(response){
		console.log("response received!");
		$('.geoparsepy-spinner').hide();
		if(response != 0){
			console.log("Loading up response now");

			let PrivacyScores = 
			  { 'text': response['geolink']['Text Privacy Score'],
			   'image': response['image_results']['Image Privacy Score'], 
			   'composite': response['composite scores']['Composite Privacy Score'] };

			document.getElementById("geoparse-link-result").innerHTML ='<h2><b>Privacy Scores:</b></h2>';

			let table = '<table style=\"width:100%\"><tr><th>Text Privacy</th><th>Image Privacy</th><th>Composite Privacy</th></tr>'
			table += '<tr><td style=\"color:'+ getColor(PrivacyScores['text']) +';\" >'+ PrivacyScores['text'] + '</td><td style=\"color:'+ getColor(PrivacyScores['image']) +';\" >'+ PrivacyScores['image'] + '</td><td style=\"color:'+ getColor(PrivacyScores['composite']) +';\">'+ PrivacyScores['composite'] + '</td></tr></table>';

			document.getElementById("geoparse-link-result").innerHTML+=table + '<br>';

			document.getElementById("geoparse-link-result").innerHTML+='<h3><b>Result Breakdown:</b></h3>';
			document.getElementById("geoparse-link-result").innerHTML+='<b>Text Results</b>:';
			document.getElementById("geoparse-link-result").innerHTML+='<br><li>Privacy Score: '+ PrivacyScores['text']+'</li>';
			document.getElementById("geoparse-link-result").innerHTML+='<br><li>Predicted Location: '+response['geolink']['name']+'</li>';

			document.getElementById("geoparse-link-result").innerHTML+='<br><b>Image Results</b>:';
			document.getElementById("geoparse-link-result").innerHTML+='<br><li>Privacy Score: '+ PrivacyScores['image']+'</li>';
			document.getElementById("geoparse-link-result").innerHTML+='<br><li>Predicted Location: '+response['image_results']['City']+ ', District ' +response['image_results']['District'] +'</li>';

			document.getElementById("geoparse-link-result").innerHTML+='<br><b>Composite Results</b>:';
			document.getElementById("geoparse-link-result").innerHTML+='<br><li>Privacy Score: '+ PrivacyScores['composite']+'</li>';
			document.getElementById("geoparse-link-result").innerHTML+='<br><li>Predicted Location: '+response['composite scores']['name']+'</li><br>';

        	// window.open(response['geolink']);
			var btn = document.createElement("BUTTON");
			btn.innerHTML = 'Find Revealing Image Regions';
			btn.className += 'btn btn-primary';
			btn.id = 'btn-feature-occlusion-get';
			document.getElementById("geoparse-link-result").appendChild(btn);
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

				var form_data = new FormData();
				var files = uploaded_file.files[0];
				form_data.append('image_caption', image_caption);
				form_data.append('image', files);
				btn.addEventListener ("click", function() {
					$('.geoparsepy-spinner').show();
					// Submit the form using an asynchronous call.
					xhr = $.ajax({
						url: 'feature-occlusion',
						type: 'post',
						data: form_data,
						contentType: false,
						processData: false,
						success: displayImageFeatures,
						error: displayImageFeaturesError,
					});
				});
			}
        }
        else
        	document.getElementById("geoparse-link-result").innerHTML="Text was parsed but nothing was returned :/";
	}
	
	function displayOSMURIError(response){
		console.log("Error occured in parsing");
		$('.geoparsepy-spinner').hide();
		document.getElementById("geoparse-link-result").innerHTML='Geoparsepy encountered an interal error';
	}

	function displayImageFeatures(response){
		if(response != 0){
			console.log("response recieved");
			$('.geoparsepy-spinner').hide();
			var elem = document.getElementById('btn-feature-occlusion-get');
			elem.parentNode.removeChild(elem);
			var img = document.createElement("img");
			img.src = response['location'];
			var src = document.getElementById("geoparse-link-result");
			src.appendChild(img);
			caption = '<p>The figure on the left is the inputted image the model recieved (cropped, resized). The figure on the right is the feature relevance graph. The darker the green, the more relevant that part of the image is. In other words, the most green sections are the most revealing in terms of locality. These sections are what is allowing the model to locate your image.</p>';								
			document.getElementById("geoparse-link-result").innerHTML+=caption
		}
		else
        	document.getElementById("geoparse-link-result").innerHTML+="Image was found but no output was found.";
	}

	function displayImageFeaturesError(response){
		console.log("Error occured in image occlusion");
		$('.geoparsepy-spinner').hide();
		var elem = document.getElementById('btn-feature-occlusion-get');
    	elem.parentNode.removeChild(elem);
		document.getElementById("geoparse-link-result").innerHTML+='Finding revealing image portions encountered an interal error';
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
