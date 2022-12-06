$("#analyze").submit(function(e) {
  e.preventDefault()
  $.post({
    url: "./run_analysis",
    data: $(this).serialize(),
    dataType: "html",
    success: function(response) {
      $("#analysis_location").html(response);
    },
  });
  return false;
});

function handleAddPoke(poke) {
  // Find and set first empty selector. 0 can't be empty.
  for(let i = 0; i <= 5; i++) {
    id = "#selectors-" + i;
    if(!$(id).val()) {
      $(id).val(poke);
      break;
    }
  }

  $("#analyze").submit()
}

function handleSwapPoke(original, new_poke) {
  for(let i = 0; i <= 5; i++) {
    id = "#selectors-" + i;
    if($(id).val() == original) {
      $(id).val(new_poke);
      break;
    }
  }

  $("#analyze").submit()
}

function tryTeam(team) {
  for(let i = 0; i <= 5; i++) {
    id = "#selectors-" + i;
    $(id).val(team[i])
  }

  $("#analyze").submit()
}
