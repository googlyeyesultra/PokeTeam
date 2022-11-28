import * as dex from '@pkmn/dex';
import * as fs from "fs";

//const data_dir = "./datasets/";
const data_dir = "./datasets_temp/";

var generations = {};

fs.readdirSync(data_dir).forEach(file => {
	if (file.slice(-5) == ".json") {
		var json_data = JSON.parse(fs.readFileSync(data_dir + file));
		var gen = json_data["info"]["gen"];
		if (!(gen in generations)) {
			generations[gen] = {"pokemon": {}, "items": {}, "moves": {}, "abilities": {}};
		}
		var this_dex = dex.Dex.forGen(gen);
		for(let poke in json_data["pokemon"]) {
			if (poke in generations[gen]["pokemon"]) continue;
			generations[gen]["pokemon"][poke] = {};
			var base_stats = this_dex.species.get(poke).baseStats;
			generations[gen]["pokemon"][poke]["base_stats"] = {}
			for(let key in this_dex.stats.names) {
				var stat_name = this_dex.stats.names[key];
				if (stat_name[0] != "[") { // Special defense in gen 1.
					generations[gen]["pokemon"][poke]["base_stats"][stat_name] = base_stats[key]
				}
			}
			generations[gen]["pokemon"][poke]["types"] = this_dex.species.get(poke).types
		}
		for(let move of json_data["moves"]) {
			if (move in generations[gen]["moves"]) continue;
			generations[gen]["moves"][move] = {};
			if(move == "nomove") {
				generations[gen]["moves"][move]["name"] = "No Move";
				generations[gen]["moves"][move]["short_desc"] = "Occurs when a Pokemon has an empty moveslot.";
				generations[gen]["moves"][move]["full_desc"] = "Occurs when a Pokemon has an empty moveslot.";
				generations[gen]["moves"][move]["category"] = "—";
				generations[gen]["moves"][move]["accuracy"] = "—";
				generations[gen]["moves"][move]["pp"] = "—";
				generations[gen]["moves"][move]["power"] = "—";
				generations[gen]["moves"][move]["type"] = "—";
				generations[gen]["moves"][move]["priority"] = "—";
			} else {
				var move_data = this_dex.moves.get(move);
				generations[gen]["moves"][move]["name"] = move_data.name;
				generations[gen]["moves"][move]["short_desc"] = move_data.shortDesc;
				generations[gen]["moves"][move]["full_desc"] = move_data.desc;
				generations[gen]["moves"][move]["category"] = move_data.category;
				if (typeof move_data.accuracy != "number") {
					generations[gen]["moves"][move]["accuracy"] = "—";
				} else {
					generations[gen]["moves"][move]["accuracy"] = move_data.accuracy;
				}
				generations[gen]["moves"][move]["pp"] = move_data.pp;
				generations[gen]["moves"][move]["power"] = move_data.basePower;
				generations[gen]["moves"][move]["type"] = move_data.type;
				generations[gen]["moves"][move]["priority"] = move_data.priority;
			}
		}
		for(let abil of json_data["abilities"]) {
			if (abil in generations[gen]["abilities"]) continue;
			generations[gen]["abilities"][abil] = {};
			var abil_data = this_dex.abilities.get(abil);
			generations[gen]["abilities"][abil]["name"] = abil_data.name;
			generations[gen]["abilities"][abil]["short_desc"] = abil_data.shortDesc;
			generations[gen]["abilities"][abil]["full_desc"] = abil_data.desc;
		}
		for(let item of json_data["items"]) {
			if (item in generations[gen]["items"]) continue;
			generations[gen]["items"][item] = {};
			if(item == "nothing") {
				generations[gen]["items"][item]["name"] = "Nothing";
				generations[gen]["items"][item]["desc"] = "No held item.";
			} else {
				var item_data = this_dex.items.get(item);
				generations[gen]["items"][item]["name"] = item_data.name;
				if (item_data.shortDesc) {
					generations[gen]["items"][item]["desc"] = item_data.shortDesc;
				} else {
					generations[gen]["items"][item]["desc"] = item_data.desc;
				}
			}
		}
}})
	
for(let gen in generations) {
	fs.writeFile(data_dir + "gen" + gen + ".dex", JSON.stringify(generations[gen]), (err) => {if (err) throw err;})
}