protocol_ver = 4

svrc = {
    'OldProtocol':         32,
    'Banned':              33,
    'Salt':                34,
    'LoggedIn':            35,
    'InvalidPassword':     36,
    'Message':             37,
    'Update':              38,
    'TabComplete':         39,
    'TooManyTabCompletes': 40,  # was incorrectly aliased to Update (38); verify against live server traffic
}

clrc = {
    'BeginConnection': 52,
    'Password':        53,
    'Command':         54,
    'Pong':            55,
    'Disconnect':      56,
    'TabComplete':     57,
}

svrcu = {
    'PlayerData': 0,
    'AdminCount': 1,
    'Map':        77,
}
