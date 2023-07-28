var selected = -1;

$("#analyze").submit(function(e) {
  e.preventDefault();

  if(!e.target.reportValidity()) {
    $(".advanced-options").attr("open", true);
    e.target.reportValidity(); // We rerun this since if it was closed we couldn't display the message.
    return false;
  }

  selected = -1;
  $.post({
    url: "./run_analysis",
    data: $(this).serialize(),
    dataType: "html",
    success: function(response) {
      $("#analysis_location").html(response);
      do_prettify();
      attachInputHandlers();
    },
  });
  return false;
});

function attachInputHandlers() {
    $("#recommendations_table_filter input").keydown(keyHandler);
    $("#recommendations_table").on("page.dt", function() {selected = -1;});
    $("#recommendations_table").on("search.dt", function() {
        selected = -1;
        clearHighlights();
    });
}

function keyHandler(e) {
    var table_is_empty = $("#recommendations_table tbody tr:first td:first").hasClass("dataTables_empty");
    if(!table_is_empty) {
        if(e.key == "ArrowUp") {
            selected--;
            if(selected < 0) selected = 0;
            highlightSelected();
            e.preventDefault();
        } else if(e.key == "ArrowDown") {
            selected++;
            var num_rows = $("#recommendations_table tbody tr").length;
            if(selected >= num_rows) selected = num_rows - 1;
            highlightSelected();
            e.preventDefault();
        } else if(e.key == "Enter") {
            if(selected < 0) selected = 0;
            var td = $("#recommendations_table tbody tr").eq(selected).children("td:first");
            addPoke(td.text());
            e.preventDefault();
        }
    }
}

function clearHighlights() {
    $("#recommendations_table tbody tr").removeClass("selected-row");
}

function highlightSelected() {
    clearHighlights();
    $("#recommendations_table tbody tr").eq(selected).addClass("selected-row");
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
    remove_button.attr("title", "Remove " + poke + " from the team.")
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

attachInputHandlers();
$("#analyze").submit();
