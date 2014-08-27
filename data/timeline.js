$(document).ready(function() {
  
  // Init slider object
  $('#slider').slider({
    value: 1785,
    min: 1785,
    max: 1867,
    step: 1,
    animate: 'fast',
    slide: function(event, ui) {
      $('#current-year').html('Year: ' + ui.value);
      setData(ui.value);
    },
  });

  function getYear() {
    var year = $('#slider').slider('value');
    return year;
  };

  function setYear(newYear) {
    $('#slider').slider('value', newYear);
    $('#current-year').html('Year: ' + newYear);
    setData(newYear);
  };

  function incrementYear(increment) {
    year = getYear();
    year += increment;
    setYear(year);
  };

  var year = getYear();
  var playing = false;

  // Initialize page with default year
  $('#current-year').html('Year: ' + year);
  setData(year);

  // Skip forward button
  $('#skip-forward').on('click', this, function () {
    incrementYear(1);
  });

  // Skip backward button
  $('#skip-backward').on('click', this, function () {
    incrementYear(-1);
  });

  // Play/Pause animation functionality
  $('#animate-control').on('click', this, function () {
    if (playing === false) {
      $("#icon-target").attr("src","images/pause.png");
      window.animate = setInterval(function() {
        incrementYear(1);
        year = getYear();
        playing = true;
        // year based conditionals for stopping and basemap/marker layer selection
        if (year === 1867) {
          clearInterval(animate);
          $("#icon-target").attr("src","images/play.png");
          playing = false;
        }
      }, 500);
    } else if (playing === true) {
      $("#icon-target").attr("src","images/play.png");
      clearInterval(animate);
      playing = false;
    }
  });

});
