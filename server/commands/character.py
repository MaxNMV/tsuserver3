import random

from server import database
from server.constants import TargetType
from server.exceptions import ClientError, ServerError, ArgumentError, AreaError

from . import mod_only

__all__ = [
    'ooc_cmd_charids',
    'ooc_cmd_charselect',
    'ooc_cmd_switch',
    'ooc_cmd_randomchar',
    'ooc_cmd_charcurse',
    'ooc_cmd_uncharcurse',
    'ooc_cmd_pos',
    'ooc_cmd_forcepos',
    'ooc_cmd_reload',
    'ooc_cmd_blind',
    'ooc_cmd_unblind',
    'ooc_cmd_hide_showname',
    'ooc_cmd_unhide_showname',
    'ooc_cmd_hide',
    'ooc_cmd_unhide'
]


def ooc_cmd_charids(client, arg):
    """
    Show character IDs corresponding to each character name.
    Usage: /charids
    Alias: /cids
    """
    if len(arg) != 0:
        raise ArgumentError("This command doesn't take any arguments")
    msg = 'Here is a list of all available characters on the server:'
    for c in range(0, len(client.server.char_list)):
        msg += '\n[' + str(c) + '] ' + client.server.char_list[c]
    client.send_ooc(msg)

def ooc_cmd_charselect(client, arg):
    """
    Enter the character select screen, or force another user to select another character.
    Usage: /charselect [id]
    Alias: /cs [id]
    """
    if not arg:
        client.char_select()
    else:
        force_charselect(client, arg)

@mod_only()
def force_charselect(client, arg):
    try:
        client.server.client_manager.get_targets(client, TargetType.ID,
            int(arg), False)[0].char_select()
    except:
        raise ArgumentError('Wrong arguments. Use /charselect <target\'s id>')

def ooc_cmd_switch(client, arg):
    """
    Switch to another character. If moderator and the specified character is currently being used, the current user of that character will be automatically reassigned a character.
    Usage: /switch <name|id>
    Alias: /sw <name|id>
    """
    if len(arg) == 0:
        raise ArgumentError('You must specify a character name or ID.')
    try:
        cid = int(arg)
    except ValueError:
        try:
            cid = client.server.get_char_id_by_name(arg)
        except ServerError:
            raise
    try:
        client.change_character(cid, client.is_mod)
    except ClientError:
        raise
    client.send_ooc(f'Switched to {client.char_name}.')

def ooc_cmd_randomchar(client, arg):
    """
    Select a random character.
    Usage: /randomchar
    Alias: /rc
    """
    if len(arg) != 0:
        raise ArgumentError('This command has no arguments.')
    if len(client.charcurse) > 0:
        free_id = random.choice(client.charcurse)
    else:
        try:
            free_id = client.area.get_rand_avail_char_id()
        except AreaError:
            raise
    try:
        client.change_character(free_id)
    except ClientError:
        raise
    client.send_ooc('Randomly switched to {}'.format(client.char_name))

@mod_only()
def ooc_cmd_charcurse(client, arg):
    """
    Lock a user into being able to choose only from a list of characters.
    Usage: /charcurse <id> [charids...]
    Alias: /cc <id> [charids...]
    """
    if len(arg) == 0:
        raise ArgumentError('You must specify a target ID and at least one character ID. Consult /charids for the character IDs.')
    elif len(arg) == 1:
        raise ArgumentError('You must specify at least one character ID. Consult /charids for the character IDs.')
    args = arg.split()
    try:
        targets = client.server.client_manager.get_targets(client, TargetType.ID, int(args[0]), False)
    except:
        raise ArgumentError('You must specify a valid target!')
    if targets:
        for c in targets:
            log_msg = ''
            part_msg = ' [' + str(c.id) + '] to'
            for raw_cid in args[1:]:
                try:
                    cid = int(raw_cid)
                    c.charcurse.append(cid)
                    part_msg += ' ' + str(client.server.char_list[cid]) + ','
                    log_msg += ' ' + str(client.server.char_list[cid]) + ','
                except:
                    ArgumentError('' + str(raw_cid) +
                                  ' does not look like a valid character ID.')
            part_msg = part_msg[:-1]
            part_msg += '.'
            log_msg = log_msg[:-1]
            c.char_select()
            database.log_room('charcurse', client, client.area, target=c, message=log_msg)
            client.send_ooc('Charcursed' + part_msg)
    else:
        client.send_ooc('No targets found.')

@mod_only()
def ooc_cmd_uncharcurse(client, arg):
    """
    Remove the character choice restrictions from a user.
    Usage: /uncharcurse <id>
    Alias: /ucc <id>
    """
    if len(arg) == 0:
        raise ArgumentError('You must specify a target ID.')
    args = arg.split()
    try:
        targets = client.server.client_manager.get_targets(client, TargetType.ID, int(args[0]), False)
    except:
        raise ArgumentError('You must specify a valid target!')
    if targets:
        for c in targets:
            if len(c.charcurse) > 0:
                c.charcurse = []
                database.log_room('uncharcurse', client, client.area, target=c)
                client.send_ooc(f'Uncharcursed [{c.id}].')
                c.char_select()
            else:
                client.send_ooc(f'[{c.id}] is not charcursed.')
    else:
        client.send_ooc('No targets found.')

def ooc_cmd_pos(client, arg):
    """
    Set the place your character resides in the room.
    Usage: /pos <name>
    """
    if len(arg) == 0:
        client.change_position()
        client.send_ooc('Position reset.')
    else:
        try:
            client.change_position(arg)
        except ClientError:
            raise
        client.area.broadcast_evidence_list()
        client.send_ooc('Position changed.')

@mod_only(area_owners=True)
def ooc_cmd_forcepos(client, arg):
    """
    Set the place another character resides in the room.
    Usage: /forcepos <pos> <target>
    Alias: /fp <pos> <target>
    """
    args = arg.split()
    if len(args) < 1:
        raise ArgumentError('Not enough arguments. Use /forcepos <pos> <target>. Target should be ID, OOC-name or char-name. Use /getarea for getting info like "[ID] char-name".')
    targets = []
    pos = args[0]
    if len(args) > 1:
        targets = client.server.client_manager.get_targets(client, TargetType.CHAR_NAME, " ".join(args[1:]), True)
        if len(targets) == 0 and args[1].isdigit():
            targets = client.server.client_manager.get_targets(client, TargetType.ID, int(args[1]), True)
        if len(targets) == 0:
            targets = client.server.client_manager.get_targets(client, TargetType.OOC_NAME, " ".join(args[1:]), True)
        if len(targets) == 0:
            raise ArgumentError('No targets found.')
    else:
        for c in client.area.clients:
            targets.append(c)
    for t in targets:
        try:
            t.change_position(pos)
            t.area.broadcast_evidence_list()
            t.send_ooc(f'Forced into /pos {pos}.')
            database.log_room('forcepos', client, client.area, target=t, message=pos)
        except ClientError:
            raise
    client.area.broadcast_ooc('{} forced {} client(s) into /pos {}.'.format(client.char_name,len(targets), pos))

def ooc_cmd_reload(client, arg):
    """
    Reload a character to its default position and state.
    Usage: /reload
    Alias: /rl
    """
    if len(arg) != 0:
        raise ArgumentError("This command doesn't take any arguments")
    try:
        client.reload_character()
    except ClientError:
        raise
    client.send_ooc('Character reloaded.')

@mod_only()
def ooc_cmd_blind(client, arg):
    """
    Blind the targeted player(s) from being able to see or talk IC.
    Usage: /blind <id>
    Alias: /bl <id>
    """
    if len(arg) == 0:
        raise ArgumentError('You must specify a target.')
    try:
        targets = client.server.client_manager.get_targets(client, TargetType.ID, int(arg), False)
    except:
        raise ArgumentError('You must specify a target. Use /blind <id>.')
    if targets:
        c = targets[0]
        if c.blinded:
            raise ClientError('Client [{}] {} already blinded!'.format(c.id, c.name))
        c.blind(True)
        client.send_ooc('You have blinded [{}] {} from using /getarea and seeing non-broadcasted IC messages.'.format(c.id, c.name))
    else:
        raise ArgumentError('No targets found.')

@mod_only()
def ooc_cmd_unblind(client, arg):
    """
    Undo the effects of the blind command.
    Usage: /unblind <id>
    Alias: /ubl <id>
    """
    if len(arg) == 0:
        raise ArgumentError('You must specify a target.')
    try:
        targets = client.server.client_manager.get_targets(client, TargetType.ID, int(arg), False)
    except:
        raise ArgumentError('You must specify a target. Use /unblind <id>.')
    if targets:
        c = targets[0]
        if not c.blinded:
            raise ClientError('Client [{}] {} already unblinded!'.format(c.id, c.name))
        c.blind(False)
        client.send_ooc('You have revealed [{}] {} for using /getarea and seeing non-broadcasted IC messages.'.format(c.id, c.name))
    else:
        raise ArgumentError('No targets found.')

def ooc_cmd_hide_showname(client, arg):
    """
    Hide your showname from getarea.
    Usage: /hide_showname
    Alias: /hs
    """
    if len(arg) != 0:
        raise ArgumentError('This command has no arguments.')
    if client.showname_hidden:
        raise ClientError('Your showname is already hidden!')
    client.hide_showname(True)
    client.send_ooc("You have hidden your showname from getarea.")

def ooc_cmd_unhide_showname(client, arg):
    """
    Reveal your showname in getarea.
    Usage: /unhide_showname
    Alias: /uhs
    """
    if len(arg) != 0:
        raise ArgumentError('This command has no arguments.')
    if not client.showname_hidden:
        raise ClientError('Your showname is already revealed!')
    client.hide_showname(False)
    client.send_ooc("You have revealed your showname in getarea.")

@mod_only()
def ooc_cmd_hide(client, arg):
    """
    Hide player from getarea and playercounts.
    Usage: /hide <id>
    Alias: /hi <id>
    """
    if not arg:
        client.hide(True)
        client.send_ooc("You have been hidden.")
    else:
        targets = client.server.client_manager.get_targets(client, TargetType.ID, int(arg), False)
        if targets:
            c = targets[0]
            if c.hidden:
                raise ClientError('Client [{}] {} already hidden!'.format(c.id, c.char_name, c.name))
            c.hide(True)
            c.send_ooc("You have been hidden.")
            client.send_ooc('You have hidden [{}] {}.'.format(c.id, c.char_name, c.name))
        else:
            client.send_ooc('No targets found.')

@mod_only()
def ooc_cmd_unhide(client, arg):
    """
    Unhide player from getarea and playercounts.
    Usage: /unhide <id>
    Alias: /uhi
    """
    if not arg:
        client.hide(False)
        client.send_ooc("You have been revealed.")
    else:
        targets = client.server.client_manager.get_targets(client, TargetType.ID, int(arg), False)
        if targets:
            c = targets[0]
            if not c.hidden:
                raise ClientError('Client [{}] {} already revealed!'.format(c.id, c.char_name, c.name))
            c.hide(False)
            c.send_ooc("You have been revealed.")
            client.send_ooc('You have revealed [{}] {}.'.format(c.id, c.char_name, c.name))
        else:
            client.send_ooc('No targets found.')
