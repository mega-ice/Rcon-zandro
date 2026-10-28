protocol_ver = int(4)

svrc = {
	'OldProtocol': 			int(32),
	'Banned': 				int(33),
	'Salt': 				int(34),
	'LoggedIn': 			int(35),
	'InvalidPassword': 		int(36),
	'Message': 				int(37),
	'Update': 				int(38),
	'TabComplete': 			int(39),
	'TooManyTabCompletes': 	int(40),  # was incorrectly aliased to Update (38); verify against live server traffic
}

clrc = {
	'BeginConnection': 		52,
	'Password': 			53,
	'Command': 				54,
	'Pong': 				55,
	'Disconnect': 			56,
	'TabComplete': 			57,
}

svrcu = {
	'PlayerData':			int(0),
	'AdminCount': 			int(1),
	'Map': 					int(77),
}