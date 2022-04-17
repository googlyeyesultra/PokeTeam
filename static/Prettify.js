$(".poke-icon").each(function() {
$(this).attr("style", PokemonIcons.getPokemon($(this).data("poke")).style)})

$(".item-icon").each(function() {
$(this).attr("style", PokemonIcons.getItem($(this).data("item")).style)})

$(".poke-sprite").each(function() {
$(this).attr("src", PokemonSprites.getPokemon($(this).data("poke")).url)})

$(".abil-name").each(function () {
$(this).html(Dex.abilities.get($(this).data("abil")).name)})

$(".item-name").each(function () {
$(this).html(Dex.items.get($(this).data("item")).name)})

$(".move-name").each(function () {
$(this).html(Dex.moves.get($(this).data("move")).name)})
