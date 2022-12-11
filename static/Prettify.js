function type_display(pokemon_type) {
    var img = $("<img>")
    img.attr("src", pkmn.img.Icons.getType(pokemon_type).url)
    img.attr("alt", pokemon_type)
    return img
}

do_prettify();
function do_prettify() {
    $(".poke-icon").each(function() {
    $(this).attr("style", pkmn.img.Icons.getPokemon($(this).data("poke")).style)});

    $(".item-icon").each(function() {
        $(this).attr("style", pkmn.img.Icons.getItem($(this).data("item")).style)
        if ($(this).data("item") == "Nothing") {
            $(this).css("background", "transparent url(/static/icons/no_item.png)")
            $(this).css("background-size", "100% 100%")
        }
    });

    $(".poke-sprite").each(function() {
    $(this).attr("src", pkmn.img.Sprites.getPokemon($(this).data("poke"), {gen: $(this).data("gen")}).url)})

    $(".poke-type").each(function () {
        var types = $(this).data("types")
        var images = []
        for (type in types) {
            images.push(type_display(types[type]))
        }
        $(this).html(images)
        $(this).attr("data-search", types.join(" "))
    });

    $(".move-type").each(function () {
        if ($(this).data("type") == "—") {
            $(this).text("—")
        } else {
            $(this).html(type_display($(this).data("type")))
            $(this).attr("data-search", $(this).data("type"))
    }})

    $(".base-stats").each(function () {
        var labels = []
        var data = []
        var colors = []
        var stats = $(this).data("stats")
        for(key in stats) {
            labels.push(key + ": " + stats[key].toString().padStart(4))
            data.push(stats[key])
            colors.push("hsl(" + Math.min(145, Math.max(0, stats[key] - 40)) + ", 70%, 50%)")
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
    });

    $(".sortable").each(function () { //TODO rename this class - we're using it on an unsortable table.
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
        paging: $(this).hasClass("paged"),
        autoWidth: false,
        lengthChange: false,
        pagingType: "full",
        dom: '<"dataTable_controls"fi>tp',
        columnDefs: [
            {targets: "searchable", searchable: true},
            {targets: "unsortable", orderable: false},
            {targets: "force_num", novalue: "—", type: "setlow", className: "dt-body-right"},
            {targets: "_all", searchable: false}
        ],
        order: sort_order,
        orderClasses: false,
        language: {search: "", searchPlaceholder: "Search..."}
        });
    });


    $(".dataTables_filter input[type=search]").each(function() {
        $(this).focus();
    });
}
