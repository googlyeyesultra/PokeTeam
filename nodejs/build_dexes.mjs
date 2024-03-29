import * as dex from "@pkmn/dex";
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
			var moves = {};
			for(let move in json_data["pokemon"][poke]["Moves"]) {
				if(move == "nomove") {
					var move_name = "No Move";
				} else {
					var move_name = this_dex.moves.get(move).name;
				}
				moves[move_name] = json_data["pokemon"][poke]["Moves"][move];
			}
			json_data["pokemon"][poke]["Moves"] = moves;
			
			var abils = {};
			for(let abil in json_data["pokemon"][poke]["Abilities"]) {
				abils[this_dex.abilities.get(abil).name] = json_data["pokemon"][poke]["Abilities"][abil];
			}
			json_data["pokemon"][poke]["Abilities"] = abils;
			
			var items = {};
			for(let item in json_data["pokemon"][poke]["Items"]) {
				if(item == "nothing") items["Nothing"] = json_data["pokemon"][poke]["Items"][item];
				else items[this_dex.items.get(item).name] = json_data["pokemon"][poke]["Items"][item];
			}
			json_data["pokemon"][poke]["Items"] = items;
			
			if (poke in generations[gen]["pokemon"]) continue;
			generations[gen]["pokemon"][poke] = {};
			var base_stats = this_dex.species.get(poke).baseStats;
			generations[gen]["pokemon"][poke]["base_stats"] = {};

			for(let key in this_dex.stats.names) {
				var stat_name = this_dex.stats.names[key];
				if (stat_name[0] != "[") { // Special defense in gen 1.
					generations[gen]["pokemon"][poke]["base_stats"][stat_name] = base_stats[key];
				}
			}
			generations[gen]["pokemon"][poke]["types"] = this_dex.species.get(poke).types;
		}

		if (!("base_stats_short" in generations[gen])) {
            generations[gen]["base_stats_short"] = []
            for(let stat_key in this_dex.stats.shortNames) {
                var stat_name = this_dex.stats.shortNames[stat_key];
                if (stat_name[0] != "[") { // Special defense in gen 1.
					generations[gen]["base_stats_short"].push(stat_name);
				}
            }
		}
		
		var moves = {};
		for(let move in json_data["moves"]) {
			var move_data = this_dex.moves.get(move);
			if(move == "nomove") {
				var move_name = "No Move";
			} else {
				var move_name = move_data.name;
			}
			moves[move_name] = json_data["moves"][move];
			if (move_name in generations[gen]["moves"]) continue;
			generations[gen]["moves"][move_name] = {};
			if(move == "nomove") {
				generations[gen]["moves"][move_name]["short_desc"] = "Occurs when a Pokemon has an empty moveslot.";
				generations[gen]["moves"][move_name]["full_desc"] = "Occurs when a Pokemon has an empty moveslot.";
				generations[gen]["moves"][move_name]["category"] = "—";
				generations[gen]["moves"][move_name]["accuracy"] = "—";
				generations[gen]["moves"][move_name]["pp"] = "—";
				generations[gen]["moves"][move_name]["power"] = "—";
				generations[gen]["moves"][move_name]["type"] = "—";
				generations[gen]["moves"][move_name]["priority"] = "—";
			} else {
				if (move_name.startsWith("Hidden Power ")) { // Hidden Power Fire, etc. are missing descriptions.
					var hp_data = this_dex.moves.get("Hidden Power");
					generations[gen]["moves"][move_name]["short_desc"] = hp_data.shortDesc;
					generations[gen]["moves"][move_name]["full_desc"] = hp_data.desc;
				} else {
					generations[gen]["moves"][move_name]["short_desc"] = move_data.shortDesc;
					generations[gen]["moves"][move_name]["full_desc"] = move_data.desc;	
				}
				
				generations[gen]["moves"][move_name]["priority"] = move_data.priority;
				generations[gen]["moves"][move_name]["category"] = move_data.category;
				if (typeof move_data.accuracy != "number") {
					generations[gen]["moves"][move_name]["accuracy"] = "—";
				} else {
					generations[gen]["moves"][move_name]["accuracy"] = move_data.accuracy;
				}
				generations[gen]["moves"][move_name]["pp"] = move_data.pp;
				if (move_data.basePower) generations[gen]["moves"][move_name]["power"] = move_data.basePower;
				else generations[gen]["moves"][move_name]["power"] = "—";
				generations[gen]["moves"][move_name]["type"] = move_data.type;
			}
		}
		json_data["moves"] = moves;
		
		var abils = {};
		for(let abil in json_data["abilities"]) {
			var abil_data = this_dex.abilities.get(abil);
			abils[abil_data.name] = json_data["abilities"][abil];
			if (abil in generations[gen]["abilities"]) continue;
			generations[gen]["abilities"][abil_data.name] = {};
			generations[gen]["abilities"][abil_data.name]["short_desc"] = abil_data.shortDesc;
			generations[gen]["abilities"][abil_data.name]["full_desc"] = abil_data.desc;
		}
		json_data["abilities"] = abils;
		
		var items = {};
		for(let item in json_data["items"]) {
			if(item == "nothing") var item_name = "Nothing";
			else {
				var item_data = this_dex.items.get(item);
				var item_name = item_data.name;
			}
			items[item_name] = json_data["items"][item];
			if (item_name in generations[gen]["items"]) continue;
			generations[gen]["items"][item_name] = {};
			if(item_name == "Nothing") {
				generations[gen]["items"][item_name]["desc"] = "No held item.";
			} else {
				if (item_data.shortDesc) {
					generations[gen]["items"][item_name]["desc"] = item_data.shortDesc;
				} else {
					generations[gen]["items"][item_name]["desc"] = item_data.desc;
				}
			}
		}
		json_data["items"] = items;

		fs.writeFile(data_dir + file, JSON.stringify(json_data), (err) => {if (err) throw err;})
}})
	
for(let gen in generations) {
	fs.writeFile(data_dir + "gen" + gen + ".dex", JSON.stringify(generations[gen]), (err) => {if (err) throw err;})
}

// TODO do we need to wait until all files are done writing?
