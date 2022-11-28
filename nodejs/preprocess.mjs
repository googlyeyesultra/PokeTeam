import * as dex from '@pkmn/dex';
import * as fs from "fs";

const data_dir = "./datasets_temp/";

fs.readdirSync(data_dir).forEach(file => {
	if (file.slice(-5) == ".json") {
		var json_data = JSON.parse(fs.readFileSync(data_dir + file));
		var this_dex = dex.Dex.forGen(json_data["info"]["gen"]);
		for(let poke in json_data["pokemon"]) {
			var base_stats = this_dex.species.get(poke).baseStats;
			json_data["pokemon"][poke]["base_stats"] = {}
			for(let key in this_dex.stats.names) {
				var stat_name = this_dex.stats.names[key];
				if (stat_name[0] != "[") { // Special defense in gen 1.
					json_data["pokemon"][poke]["base_stats"][stat_name] = base_stats[key]
				}
			}
			json_data["pokemon"][poke]["types"] = this_dex.species.get(poke).types
		}
		for(let move in json_data["moves"]) {
			if(move == "nomove") {
				json_data["moves"][move]["name"] = "No Move";
				json_data["moves"][move]["short_desc"] = "Occurs when a Pokemon has an empty moveslot.";
				json_data["moves"][move]["full_desc"] = "Occurs when a Pokemon has an empty moveslot.";
				json_data["moves"][move]["category"] = "—";
				json_data["moves"][move]["accuracy"] = "—";
				json_data["moves"][move]["pp"] = "—";
				json_data["moves"][move]["power"] = "—";
				json_data["moves"][move]["type"] = "—";
				json_data["moves"][move]["priority"] = "—";
			} else {
				var move_data = this_dex.moves.get(move);
				json_data["moves"][move]["name"] = move_data.name;
				json_data["moves"][move]["short_desc"] = move_data.shortDesc;
				json_data["moves"][move]["full_desc"] = move_data.desc;
				json_data["moves"][move]["category"] = move_data.category;
				if (typeof move_data.accuracy != "number") {
					json_data["moves"][move]["accuracy"] = "—";
				} else {
					json_data["moves"][move]["accuracy"] = move_data.accuracy;
				}
				json_data["moves"][move]["pp"] = move_data.pp;
				json_data["moves"][move]["power"] = move_data.basePower;
				json_data["moves"][move]["type"] = move_data.type;
				json_data["moves"][move]["priority"] = move_data.priority;
			}
		}
		for(let abil in json_data["abilities"]) {
			var abil_data = this_dex.abilities.get(abil);
			json_data["abilities"][abil]["name"] = abil_data.name;
			json_data["abilities"][abil]["short_desc"] = abil_data.shortDesc;
			json_data["abilities"][abil]["full_desc"] = abil_data.desc;
		}
		for(let item in json_data["items"]) {
			if(item == "nothing") {
				json_data["items"][item]["name"] = "Nothing";
				json_data["items"][item]["desc"] = "No held item.";
			} else {
				var item_data = this_dex.items.get(item);
				json_data["items"][item]["name"] = item_data.name;
				if (item_data.shortDesc) {
					json_data["items"][item]["desc"] = item_data.shortDesc;
				} else {
					json_data["items"][item]["desc"] = item_data.desc;
				}
			}
		}
	
		fs.writeFile(data_dir + file, JSON.stringify(json_data), (err) => {if (err) throw err;})
	}
	
})