$("#find_cores").submit(function(e) {
  e.preventDefault()

  if(!e.target.reportValidity()) {
    $(".advanced-options").attr("open", true);
    e.target.reportValidity(); // We rerun this since if it was closed we couldn't display the message.
    return false;
  }

  $("#filter_cores").val("").focus();
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

function filterCores() {
    keywords = $("#filter_cores").val().toLowerCase().split(" ");
    $(".core-inner").each(function() {
        pokemon = $(this).data("pokes");
        for(word of keywords) {
            found = false;
            for(poke of pokemon) {
                if(poke.includes(word)) {
                    found = true;
                    break;
                }
            }
            if(!found) {
                $(this).hide();
                return;
            }
        }

        $(this).show();
    });
}
