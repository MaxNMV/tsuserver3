import shlex

from server import database
from server.constants import TargetType
from server.exceptions import ClientError, ArgumentError, AreaError

from . import mod_only

__all__ = [
    'ooc_cmd_bg',
    'ooc_cmd_bgs',
    'ooc_cmd_bglock',
    'ooc_cmd_allow_iniswap',
    'ooc_cmd_allow_blankposting',
    'ooc_cmd_force_nonint_pres',
    'ooc_cmd_status',
    'ooc_cmd_area',
    'ooc_cmd_getarea',
    'ooc_cmd_getareas',
    'ooc_cmd_getafk',
    'ooc_cmd_autogetarea',
    'ooc_cmd_area_lock',
    'ooc_cmd_area_unlock',
    'ooc_cmd_area_spectate',
    'ooc_cmd_knock',
    'ooc_cmd_invitelist',
    'ooc_cmd_invite',
    'ooc_cmd_uninvite',
    'ooc_cmd_area_kick',
    'ooc_cmd_delay'
]


def ooc_cmd_bg(client, arg):
    """
    Set the background of a room.
    Usage: /bg <background>
    """
    if len(arg) == 0:
        raise ArgumentError('You must specify a name. Use /bg <background>.')
    if not client.is_mod and client.area.bg_lock == "true":
        raise AreaError("This area's background is locked!")
    elif client.area.cannot_ic_interact(client):
        raise AreaError("You are not permitted to change the background in this area!")
    try:
        client.area.change_background(arg)
    except AreaError:
        raise
    client.area.broadcast_ooc(f'{client.char_name} changed the background to {arg}.')
    database.log_room('bg', client, client.area, message=arg)

def ooc_cmd_bgs(client, arg):
    """
    Display the server's available backgrounds.
    Usage: /bgs <category>
    """
    arg_norm = arg.lower().strip()
    categories = client.area.server.backgrounds_categories
    category_lookup = {cat.lower(): cat for cat in categories}
    if arg == "":
        msg = "Available Categories:"
        for category in categories:
            msg += f"\n{category}"
        client.send_ooc(msg)
        return
    elif arg_norm in category_lookup:
        bg_name = category_lookup[arg_norm]
        msg = f"Backgrounds in Category '{bg_name}':"
        for bg in categories[bg_name]:
            msg += f"\n{bg}"
        client.send_ooc(msg)
    else:
        client.send_ooc("There is no category with this name in server background list.")

@mod_only()
def ooc_cmd_bglock(client, arg):
    """
    Toggle whether or not non-moderators are allowed to change the background of a room.
    Usage: /bglock
    Alias: /lockbg
    """
    if len(arg) != 0:
        raise ArgumentError('This command has no arguments.')
    # XXX: Okay, what?
    if client.area.bg_lock == "true":
        client.area.bg_lock = "false"
    else:
        client.area.bg_lock = "true"
    client.area.broadcast_ooc('{} [{}] has set the background lock to {}.'.format(client.char_name, client.id, client.area.bg_lock))
    database.log_room('bglock', client, client.area, message=client.area.bg_lock)

@mod_only()
def ooc_cmd_allow_iniswap(client, arg):
    """
    Toggle whether or not users are allowed to swap INI files in character folders to allow playing as a character other than the one chosen in the character list.
    Usage: /allow_iniswap
    Alias: /ais
    """
    client.area.iniswap_allowed = not client.area.iniswap_allowed
    answer = 'allowed' if client.area.iniswap_allowed else 'forbidden'
    client.send_ooc(f'Iniswap is {answer}.')
    database.log_room('iniswap', client, client.area, message=client.area.iniswap_allowed)

@mod_only(area_owners=True)
def ooc_cmd_allow_blankposting(client, arg):
    """
    Toggle whether or not in-character messages purely consisting of spaces are allowed.
    Usage: /allow_blankposting
    Alias: /abp
    """
    client.area.blankposting_allowed = not client.area.blankposting_allowed
    answer = 'allowed' if client.area.blankposting_allowed else 'forbidden'
    client.area.broadcast_ooc('{} [{}] has set blankposting in the area to {}.'.format(client.char_name, client.id, answer))
    database.log_room('blankposting', client, client.area, message=client.area.blankposting_allowed)

@mod_only(area_owners=True)
def ooc_cmd_force_nonint_pres(client, arg):
    """
    Toggle whether or not all pre-animations lack a delay before a character begins speaking.
    Usage: /force_nonint_pres
    Alias: /fnp
    """
    client.area.non_int_pres_only = not client.area.non_int_pres_only
    answer = 'non-interrupting only' if client.area.non_int_pres_only else 'non-interrupting or interrupting as you choose'
    client.area.broadcast_ooc('{} [{}] has set pres in the area to be {}.'.format(client.char_name, client.id, answer))
    database.log_room('force_nonint_pres', client, client.area, message=client.area.non_int_pres_only)

def ooc_cmd_status(client, arg):
    """
    Show or modify the current status of a room.
    Usage: /status <idle|rp|casing|looking-for-players|lfp|recess|gaming>
    Alias: /st
    """
    if len(arg) == 0:
        client.send_ooc(f'Current status: {client.area.status}')
    else:
        try:
            client.area.change_status(arg)
            client.area.broadcast_ooc('{} changed status to {}.'.format(client.char_name, client.area.status))
            database.log_room('status', client, client.area, message=arg)
        except AreaError:
            raise

def ooc_cmd_area(client, arg):
    """
    List areas, or go to another area/room.
    Usage: /area [<id|name>]
    Alias: /a [<id|name>]
    """
    args = arg.split()
    if len(args) == 0:
        client.send_area_list()
        return
    try:
        area = client.server.area_manager.get_area_by_id(int(args[0]))
        client.change_area(area)
        return
    except ValueError:
        try:
            area = client.server.area_manager.get_area_by_name(arg)
            client.change_area(area)
        except ValueError:
            raise ArgumentError('Area ID must be a name or a number.')
        except (AreaError, ClientError):
            raise

def ooc_cmd_getarea(client, arg):
    """
    Show information about the current or another area.
    Usage: /getarea [area id]
    Alias: /ga [area id]
    """
    if client.blinded:
        raise ArgumentError('You are blinded - you cannot use this command!')
    if len(arg) == 0:
        client.send_area_info(client.area.id, False)
        return
    try:
        client.server.area_manager.get_area_by_id(int(arg[0]))
        area = int(arg[0])
        client.send_area_info(area, False)
    except ValueError:
        raise ArgumentError('Area ID must be a number.')
    except (AreaError, ClientError):
        raise

def ooc_cmd_getareas(client, arg):
    """
    Show information about all areas.
    Usage: /getareas
    Alias: /gas
    """
    if client.blinded:
        raise ArgumentError('You are blinded - you cannot use this command!')
    client.send_area_info(-1, False)

def ooc_cmd_getafk(client, arg):
    """
    Show currently AFK-ing players in the current area or in all areas.
    Usage: /getafk [all]
    Alias: /gafk [all]
    """
    if arg == 'all':
        arg = -1
    elif len(arg) == 0:
        arg = client.area.id
    else:
        raise ArgumentError('There is only one optional argument [all].')
    client.send_area_info(arg, False, afk_check=True)

def ooc_cmd_autogetarea(client, arg):
    """
    Automatically /getarea whenever you enter a new area.
    Usage: /autogetarea
    Alias: /aga
    """
    client.autogetarea = not client.autogetarea
    toggle = "enabled" if client.autogetarea else "disabled"
    client.send_ooc(f"You have {toggle} automatic /getarea.")

def ooc_cmd_area_lock(client, arg):
    """
    Prevent users from joining the current area.
    Usage: /area_lock
    Alias: /lock
    """
    if not client.area.locking_allowed:
        client.send_ooc('Area locking is disabled in this area.')
    elif client.area.is_locked == client.area.Locked.LOCKED:
        client.send_ooc('Area is already locked.')
    elif client in client.area.owners or client.is_mod:
        client.area.lock()
    else:
        raise ClientError('Only CM can lock the area.')

def ooc_cmd_area_unlock(client, arg):
    """
    Allow anyone to freely join the current area.
    Usage: /area_unlock
    Alias: /unlock
    """
    if client.area.is_locked == client.area.Locked.FREE:
        raise ClientError('Area is already unlocked.')
    elif client in client.area.owners or client.is_mod:
        client.area.unlock()
        client.send_ooc('Area is unlocked.')
    else:
        raise ClientError('Only CM can unlock area.')

def ooc_cmd_area_spectate(client, arg):
    """
    Allow users to join the current area, but only as spectators.
    Usage: /area_spectate
    Alias: /as
    """
    if not client.area.locking_allowed:
        client.send_ooc('Area locking is disabled in this area.')
    elif client.area.is_locked == client.area.Locked.SPECTATABLE:
        client.send_ooc('Area is already spectatable.')
    elif client in client.area.owners or client.is_mod:
        client.area.spectator()
    else:
        raise ClientError('Only CM can make the area spectatable.')

def ooc_cmd_knock(client, arg):
    """
    Knock on the target area ID to call on their attention to your area.
    Usage: /knock [<id>]
    Alias: /kn [<id>]
    """
    if arg == "":
        raise ArgumentError("You need to input an area name or ID to knock!")
    if client.blinded:
        raise ClientError("Failed to knock: you are blinded!")
    try:
        area = None
        for _area in client.server.area_manager.areas:
            if (_area.name.lower() == arg.lower()
                or _area.abbreviation == arg
                or (arg.isdigit() and _area.id == int(arg))):
                area = _area
                break
        if area is None:
            raise ClientError("Area not found.")
        area.send_command("RT", "knock")
        if area == client.area:
            area.broadcast_ooc(f"💢 [{client.id}]:{client.char_name} ({client.showname}) knocks for attention. 💢")
        elif area.is_locked == area.Locked.FREE:
            raise ClientError(f"Failed to knock on [{area.id}] {area.name}: area is not locked.")
        else:
            client.send_ooc(f"You have knocked on [{area.id}] {area.name}.")
            area.broadcast_ooc(f"💢 [{client.id}]:{client.char_name} ({client.showname}) is knocking from [{client.area.id}] {client.area.name} 💢")
    except (AreaError, ClientError):
        raise

@mod_only(area_owners=True)
def ooc_cmd_invitelist(client, arg):
    """
    Show the invite list of an area.
    Usage: /invitelist [area id|area name]
    Alias: /il [area id|area name]
    """
    if not arg:
        area = client.area
    else:
        try:
            area = client.server.area_manager.get_area_by_id(int(arg))
        except ValueError:
            try:
                area = client.server.area_manager.get_area_by_name(arg)
            except ValueError:
                raise ClientError("Area must be an ID or name.")
        if not client.is_mod and area.id != client.area.id:
            raise ClientError("You may only view the invite list of your own area.")
    if area.is_locked == area.Locked.FREE:
        client.send_ooc(f"{area.name} is unlocked and has no invite list.")
        return
    inv_list = area.invite_list
    if not inv_list:
        client.send_ooc(f"{area.name} has no invited users.")
        return
    lines = [f"Invite list for {area.name}:"]
    for uid in inv_list:
        targets = client.server.client_manager.get_targets(client, TargetType.ID, uid)
        c = targets[0] if targets else None
        if c:
            lines.append(f"[{area.abbreviation}] [{c.id}] {c.char_name}")
        else:
            lines.append(f"[{uid}] <offline>")
    client.send_ooc("\n".join(lines))
    
@mod_only(area_owners=True)
def ooc_cmd_invite(client, arg):
    """
    Allow a particular user to join a locked or spectator-only area.
    Usage: /invite <id>
    Alias: /i <id>
    """
    if not arg:
        raise ClientError('You must specify a target. Use /invite <id>')
    elif client.area.is_locked == client.area.Locked.FREE:
        raise ClientError('Area isn\'t locked.')
    try:
        c = client.server.client_manager.get_targets(client, TargetType.ID,
                                                     int(arg), False)[0]
        client.area.invite_list[c.id] = None
        client.send_ooc(f'You have invited [{c.id}]: {c.char_name} to your area.')
        c.send_ooc(f'You were invited and given access to {client.area.name}.')
        database.log_room('invite', client, client.area, target=c)
    except:
        raise ClientError('You must specify a target. Use /invite <id>')

@mod_only(area_owners=True)
def ooc_cmd_uninvite(client, arg):
    """
    Revoke an invitation for a particular user.
    Usage: /uninvite <id>
    Alias: /uin <id>
    """
    if client.area.is_locked == client.area.Locked.FREE:
        raise ClientError('Area isn\'t locked.')
    elif not arg:
        raise ClientError('You must specify a target. Use /uninvite <id>')
    arg = arg.split(' ')
    targets = client.server.client_manager.get_targets(client, TargetType.ID,
                                                       int(arg[0]), False)
    if targets:
        try:
            for c in targets:
                client.send_ooc(f"You have removed [{c.id}]: {c.char_name} from the whitelist.")
                c.send_ooc(f"You were removed from the {client.area.name}'s whitelist.")
                database.log_room('uninvite', client, client.area, target=c)
                if client.area.is_locked != client.area.Locked.FREE:
                    client.area.invite_list.pop(c.id)
        except AreaError:
            raise
        except ClientError:
            raise
    else:
        client.send_ooc("No targets found.")

@mod_only(area_owners=True)
def ooc_cmd_area_kick(client, arg):
    """
    Remove a user from the current area and move them to another area.
    If id is a * char, it will kick everyone but you and CMs from current area to destination.
    If id is a !, it will kick everyone including CM's from current area to destination.
    If id is afk, it will only kick all the afk people.
    Usage:
        - CMs: /area_kick <id>
        - Mods: /area_kick <id> [area id]
    Alias: /ak <id>
    """
    if not client.is_mod:  
        if client.area.is_locked == client.area.Locked.FREE:
            raise ClientError('Area isn\'t locked.')
    if not arg:
        raise ClientError('You must specify a target. Use /area_kick <id> [area id]')
    args = shlex.split(arg)
    if args[0] == "afk":
        targets = client.server.client_manager.get_targets(client, TargetType.AFK, args[0], False)
    elif args[0] == "*":
        targets = [
            c
            for c in client.area.clients
            if c != client and c not in client.area.owners
        ]
    elif args[0] == "!":
        targets = [
            c
            for c in client.area.clients
            if c != client
        ]
    else:
        # Try to find by char name first
        targets = client.server.client_manager.get_targets(client, TargetType.CHAR_NAME, args[0])
        # If that doesn't work, find by client ID
        if len(targets) == 0 and args[0].isdigit():
            targets = client.server.client_manager.get_targets(client, TargetType.ID, int(args[0]))
        # If that doesn't work, find by OOC Name
        if len(targets) == 0:
            targets = client.server.client_manager.get_targets(client, TargetType.OOC_NAME, args[0])
    if len(targets) == 0:
        client.send_ooc(f"No targets found by search term '{args[0]}'.")
        return
    try:
        for c in targets:
            if client.is_mod:
                if len(args) == 1:
                    kick_area = client.server.area_manager.get_area_by_id(0)
                    output = 0
                else:
                    kick_area = client.server.area_manager.get_area_by_id(int(args[1]))
                    output = args[1]
            else:
                kick_area = client.server.area_manager.get_area_by_id(0)
                output = 0
            client.send_ooc(f"Attempting to kick {c.char_name} to area {output}.")
            c.change_area(kick_area)
            c.send_ooc(f"You were kicked from the area to area {output}.")
            database.log_room('area_kick', client, client.area, target=c, message=output)
            if client.area.is_locked != client.area.Locked.FREE:
                client.area.invite_list.pop(c.id, None)
    except AreaError:
        raise
    except ClientError:
        raise

@mod_only()
def ooc_cmd_delay(client, arg):
    """
    Change the minimum delay between messages, default is 100.
    Usage: /delay [delay]
    Alias: /d [delay]
    """
    if len(arg) == 0:
        client.area.next_message_delay = 100
    else:        
        client.area.next_message_delay = int(arg)    
    database.log_room('delay', client, client.area, message=client.area.next_message_delay)
