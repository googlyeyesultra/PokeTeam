$("#analyze").submit(function(e) {
  e.preventDefault();
  $.post({
    url: "./run_analysis",
    data: $(this).serialize(),
    dataType: "html",
    success: function(response) {
      $("#analysis_location").html(response);
      do_prettify();
      attachInputHandler();
    },
  });
  return false;
});

function attachInputHandler() {
    $(".dataTables_filter input").each(function() {
        $(this).on("keypress", enterHandler);
    });
}

function enterHandler(e) {
    if(e.which == 13) {
        $("#recommendations_table tbody tr:nth-child(1) td:nth-child(1)").each(function() {
            if(!$(this).hasClass("dataTables_empty")) addPoke($(this).text());
        });
    }
}

function addPoke(poke, analyze=true) {
  if ($(".team_member").length < 6) {
    $("#input_pokemon").append(teamMemberDisplay(poke));
  }
  if (analyze) $("#analyze").submit();
}

function teamMemberDisplay(poke) {
    var link_url = $("#input_pokemon").data("url").replace("~", poke)
    var link = $("<a class='team_link'></a>").attr("href", link_url).text(poke);
    // TODO this is code duplication from Prettify.
    var image = ($("<span class='team_image'></span>").attr("style", pkmn.img.Icons.getPokemon(poke).style))
    var remove_button = $("<a href='javascript:void(0)' class='remove_button'>⨯</a>")
    var form_field = $("<input type='hidden' name='pokemon'>").attr("value", poke);
    remove_button.attr("onclick", "removePoke(this)");
    return $("<div class='team_member'></div>").data("pokemon", poke).append(image, remove_button, link, form_field);
}

function removePoke(tag) {
    $(tag).parent().remove();
    $("#analyze").submit();
}

function swapPoke(original, new_poke) {
  $(".team_member").each(function () {
    if ($(this).data("pokemon") == original) {
        $(this).replaceWith(teamMemberDisplay(new_poke));
        return false;
    }
  });

  $("#analyze").submit();
}

function tryTeam(team) {
  $(".team_member").remove();
  for(poke of team) {
    addPoke(poke, false);
  }
  $("#analyze").submit();
}

attachInputHandler();
