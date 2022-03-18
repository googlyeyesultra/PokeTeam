$("#find_cores").submit(function(e) {
  e.preventDefault()
  $.post({
    url: "./find_cores",
    data: $(this).serialize(),
    dataType: "html",
    success: function(response) {
      $("#cores_location").html(response);
    },
  });
  return false;
});