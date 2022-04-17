$(".poke-icon").each(function() {
$(this).attr("style", PokemonIcons.getPokemon($(this).data("poke")).style)})

$(".item-icon").each(function() {
$(this).attr("style", PokemonIcons.getItem($(this).data("item")).style)})

$(".poke-sprite").each(function() {
$(this).attr("src", PokemonSprites.getPokemon($(this).data("poke")).url)})
