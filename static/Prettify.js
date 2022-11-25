$(".poke-icon").each(function() {
$(this).attr("style", pkmn.img.Icons.getPokemon($(this).data("poke")).style)})

$(".item-icon").each(function() {
    $(this).attr("style", pkmn.img.Icons.getItem($(this).data("item")).style)
    if ($(this).data("item") == "nothing") {
        $(this).css("background", "transparent url(/static/icons/no_item.png)")
        $(this).css("background-size", "100% 100%")
    }
})

$(".poke-sprite").each(function() {
$(this).attr("src", pkmn.img.Sprites.getPokemon($(this).data("poke"), {gen: $(this).data("gen")}).url)})

$(".abil-name").each(function () {
$(this).text(pkmn.dex.Dex.abilities.get($(this).data("abil")).name)})

$(".item-name").each(function () {
    if($(this).data("item") == "nothing") {
        $(this).text("Nothing")
    } else {
        $(this).text(pkmn.dex.Dex.items.get($(this).data("item")).name)
    }
})

$(".move-name").each(function () {
$(this).text(pkmn.dex.Dex.moves.get($(this).data("move")).name)})

$(".sortable").each(function () {
    sort_th = $("th.sort_desc")
    sort_dir = "desc"
    if(!sort_th.length) {
        sort_th = $("th.sort_asc")
        sort_dir = "asc"
    }

    if(sort_th.length) {
        sort_order = [[sort_th.index(), sort_dir]]
    } else {
        sort_order = []
    }

    $(this).DataTable({
    paging: false,
    autoWidth: false,
    columnDefs: [
        {targets: "searchable", searchable: true},
        {targets: "_all", searchable: false}
    ],
    order: sort_order,
    orderClasses: false,
    language: {search: "",
               searchPlaceholder: "Search",},
    });
});
