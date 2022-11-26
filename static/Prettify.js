function type_display(pokemon_type, img) {
    img.attr("src", pkmn.img.Icons.getType(pokemon_type).url)
    img.attr("alt", pokemon_type)
    return img
}

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

$(".move-category").each(function () {
$(this).text(pkmn.dex.Dex.forGen($(this).data("gen")).moves.get($(this).data("move")).category)})

$(".move-power").each(function () {
var power = pkmn.dex.Dex.forGen($(this).data("gen")).moves.get($(this).data("move")).basePower
    if (power == 0) {
        $(this).text("—")
    } else {
        $(this).text(power)
    }
})

$(".move-accuracy").each(function () {
    var accuracy = pkmn.dex.Dex.forGen($(this).data("gen")).moves.get($(this).data("move")).accuracy
    if (typeof accuracy != "number") {
        $(this).text("—")
    } else {
        $(this).text(accuracy + "%")
    }
})

$(".move-pp").each(function () {
$(this).text(pkmn.dex.Dex.forGen($(this).data("gen")).moves.get($(this).data("move")).pp)})

$(".move-priority").each(function () {
$(this).text(pkmn.dex.Dex.forGen($(this).data("gen")).moves.get($(this).data("move")).priority)})

$(".move-type").each(function () {
    var move_type = pkmn.dex.Dex.forGen($(this).data("gen")).moves.get($(this).data("move")).type
    type_display(move_type, $(this))
})

$(".move-type-text").each(function () {
    var move_type = pkmn.dex.Dex.forGen($(this).data("gen")).moves.get($(this).data("move")).type
    $(this).text(move_type)
})

$(".poke-type").each(function () {
    var types = pkmn.dex.Dex.forGen($(this).data("gen")).species.get($(this).data("poke")).types
    var images = []
    for (type in types) {
        images.push(type_display(types[type], $("<img>")))
    }
    $(this).html(images)
})

$(".poke-type-text").each(function () {
    var types = pkmn.dex.Dex.forGen($(this).data("gen")).species.get($(this).data("poke")).types
    $(this).text(types.join(", "))
})

$(".move-full-desc").each(function () {
$(this).text(pkmn.dex.Dex.forGen($(this).data("gen")).moves.get($(this).data("move")).desc)})

$(".abil-short-desc").each(function () {
$(this).text(pkmn.dex.Dex.forGen($(this).data("gen")).abilities.get($(this).data("abil")).shortDesc)})

$(".abil-full-desc").each(function () {
$(this).text(pkmn.dex.Dex.forGen($(this).data("gen")).abilities.get($(this).data("abil")).desc)})

$(".move-short-desc").each(function () {
$(this).text(pkmn.dex.Dex.forGen($(this).data("gen")).moves.get($(this).data("move")).shortDesc)})

$(".poke-type").each(function () {
    var types = pkmn.dex.Dex.forGen($(this).data("gen")).species.get($(this).data("poke")).types
    var images = []
    for (type in types) {
        images.push(type_display(types[type], $("<img>")))
    }
    $(this).html(images)
})

$(".base-stats").each(function () {
    const dex = pkmn.dex.Dex.forGen($(this).data("gen"))
    const base_stats = dex.species.get($(this).data("poke")).baseStats
    var labels = []
    var data = []
    var colors = []
    for(key in dex.stats.names) {
        if (dex.stats.names[key][0] != "[") { // Special defense in gen 1.
            labels.push(dex.stats.names[key] + ": " + base_stats[key].toString().padStart(4))
            data.push(base_stats[key])
            colors.push("hsl(" + Math.min(145, Math.max(0, base_stats[key] - 40)) + ", 70%, 50%)")
        }
    }
    new Chart(
        $(this)[0],
        {
            type: "bar",
            options: {
                events: [],
                animation: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        enabled: false
                    },
                },
                indexAxis: "y",
                scales: {
                    x: {
                        display: false,
                        suggestedMin: 0,
                        suggestedMax: 256
                    }
                }
            },

            data: {
                labels: labels,
                datasets: [
                    {
                        backgroundColor: colors,
                        label: "Stat",
                        data: data
                    }
                    ]
            }
        }
    )
})

$(".item-desc").each(function () {
    if ($(this).data("item") == "nothing") {
        $(this).text("No held item.")
    } else {
        var item_def = pkmn.dex.Dex.forGen($(this).data("gen")).items.get($(this).data("item"))
        if (item_def.shortDesc) {
            $(this).text(item_def.shortDesc)
        } else {
            $(this).text(item_def.desc)
        }
    }
})

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
        {targets: "hidden", visible: false, searchable: true},
        {targets: "unsortable", orderable: false},
        {targets: "_all", searchable: false}
    ],
    order: sort_order,
    orderClasses: false,
    language: {search: "",
               searchPlaceholder: "Search",},
    });
});
