import asyncio
from dataclasses import dataclass
from datetime import datetime
import shlex
import arrow
import pytimeparse
import json

from pytimeparse import parse

from server import database
from server.constants import TargetType
from server.exceptions import ClientError, ServerError, ArgumentError
from . import mod_only, list_commands, list_submodules, help

__all__ = [
    'ooc_cmd_motd',
    'ooc_cmd_help',
    'ooc_cmd_time',
    'ooc_cmd_myid',
    'ooc_cmd_online',
    'ooc_cmd_mods',
    'ooc_cmd_login',
    'ooc_cmd_unmod',
    'ooc_cmd_modicon',
    'ooc_cmd_refresh',
    'ooc_cmd_restart',
    'ooc_cmd_whois',
    'ooc_cmd_multiclients',
    'ooc_cmd_lastchar',
    'ooc_cmd_kick',
    'ooc_cmd_kms',
    'ooc_cmd_ban',
    'ooc_cmd_banhdid',
    'ooc_cmd_unban',
    'ooc_cmd_bans',
    'ooc_cmd_baninfo',
    'ooc_cmd_mute',
    'ooc_cmd_unmute',
    'ooc_cmd_ooc_mute',
    'ooc_cmd_ooc_unmute',
    'ooc_cmd_area_curse'
]


def ooc_cmd_motd(client, arg):
    """
    Show the message of the day or change the message of the day.
    Usage: /motd [text]
    """
    if arg == '':
        client.send_motd()
    elif client.is_mod:
        client.server.config['motd'] = arg.replace('\\n','\n')
        database.log_simple('MOTD', client, data={'text': arg})
        client.send_motd()
    else:
        raise ClientError('You must be authorized to do that.')

def ooc_cmd_help(client, arg):
    """
    Show help for a command, or show general help.
    Usage: /help
    Alias: /h
    """
    import inspect
    if arg == '':
        msg = inspect.cleandoc('''
        Welcome to tsuserver3! You can use /help <command> on any known
        command to get up-to-date help on it.
        You may also use /help <category> to see available commands for that category.

        If you don't understand a specific core feature, check the official
        repository for more information:

        https://github.com/AttorneyOnline/tsuserver3 

        Available Categories:
        ''')
        msg += '\n'
        msg += list_submodules()
        client.send_ooc(msg)
    else:
        arg = arg.lower()
        try:
            if arg in client.server.command_aliases:
                arg = client.server.command_aliases[arg]
            client.send_ooc(help(f'ooc_cmd_{arg}'))
        except AttributeError:
            try:
                msg = f'Submodule "{arg}" commands:\n\n'
                msg += list_commands(arg)
                client.send_ooc(msg)
            except AttributeError:
                client.send_ooc('No such command or submodule has been found in the help docs.')

def ooc_cmd_time(client, arg):
    """
    Returns the current server time.
    Usage: /time
    Alias: /t
    """
    if len(arg) > 0:
        raise ArgumentError("This command takes no arguments")
    from time import asctime, gmtime, time
    msg = "The current time in UTC (aka GMT) is:\n["
    msg += asctime(gmtime(time()))
    msg += "]"
    client.send_ooc(msg)

def ooc_cmd_myid(client, arg):
    """
    Get information for your current client, such as client ID.
    Usage: /myid
    Alias: /mid
    """
    if len(arg) > 0:
        raise ArgumentError("This command takes no arguments")
    info = f"You are ID: [{client.id}] | Char ID: {client.char_id} | Char Name: {client.char_name}"
    if client.showname != "":
        info += f' | Showname: {client.showname}'
    if client.is_mod:
        info += f" | IPID: {client.ipid}"
    if client.name != "":
        info += f" | OOC: {client.name}"
    client.send_ooc(info)

def ooc_cmd_online(client, _):
    """
    Show the number of players online.
    Usage: /online
    Alias: /o
    """
    client.send_player_count()

def ooc_cmd_mods(client, arg):
    """
    Show the number of moderators online. Also Show a list of moderators online for mods.
    Usage: /mods
    Alias: /mod
    """
    if client.is_mod:
        client.send_area_info(-1, True)
        client.send_ooc(
        "There are {} mods online.".format(client.server.area_manager.mods_online(),
                                                              len))
    else:
        client.send_ooc(
        "There are {} mods online.".format(client.server.area_manager.mods_online(),
                                                              len))

def ooc_cmd_login(client, arg):
    """
    Login as a moderator.
    Usage: /login <password>
    Alias: /li <password>
    """
    if len(arg) == 0:
        raise ArgumentError('You must specify the password.')
    login_name = None
    try:
        login_name = client.auth_mod(arg)
    except ClientError:
        client.send_command('AUTH', '0')
        database.log_misc('login.invalid', client)
        raise
    if client.area.evidence_mod == 'HiddenCM':
        client.area.broadcast_evidence_list()
    client.modicon = True
    client.send_ooc('Hello {}! You have successfully logged in as a moderator.'.format(
                login_name))
    client.send_command('AUTH', '1')
    database.log_simple('login', client, data={'profile': login_name})

def ooc_cmd_unmod(client, arg):
    """
    Log out as a moderator.
    Usage: /unmod
    Alias: /logout
    """
    client.is_mod = False
    client.mod_profile_name = None
    if client.area.evidence_mod == 'HiddenCM':
        client.area.broadcast_evidence_list()
    client.modicon = False
    client.send_ooc('You have peacefully logged out')
    client.send_command('AUTH', '-1')

@mod_only()
def ooc_cmd_modicon(client, arg):
    """
    Toggle the moderator icon in getareas.
    Usage: /modicon
    Alias: /micon
    """
    if len(arg) > 0:
        raise ClientError('This command does not take in any arguments!')
    if client.modicon:
        client.modicon = False
        client.send_ooc('Your Mod icon has been removed from getarea.')
    else:
        client.modicon = True
        client.send_ooc('Your Mod icon can now be seen in getarea.')

@mod_only()
def ooc_cmd_refresh(client, arg):
    """
    Reload all moderator credentials, server options, and commands without restarting the server.
    Usage: /refresh
    Alias: /rf
    """
    if len(arg) > 0:
        raise ClientError('This command does not take in any arguments!')
    else:
        try:
            client.server.refresh()
            database.log_simple('Refresh', client)
            client.send_ooc('You have reloaded the server.')
        except ServerError:
            raise

@mod_only()
def ooc_cmd_restart(client, arg):
    """
    Restart the server.
    (WARNING: The server will be *stopped* unless you set up a restart batch/bash file!)
    Usage: /restart <password>
    Alias: /rs <password>
    """
    if arg != client.server.config["restartpass"]:
        raise ArgumentError("No. Incorrect restart password.")
    database.log_simple('Restart', client)
    print(f"!!!{client.name} called /restart!!!")
    client.server.send_all_cmd_pred("CT", "WARNING", "Restarting the server...")
    asyncio.get_running_loop().stop()

@mod_only()
def ooc_cmd_whois(client, arg):
    """
    Get information about an online user.
    Usage: /whois <ipid|character|Showname|ooc name>
    Alias: /wis
    """
    if len(arg) == 0:
        raise ArgumentError('You trying to kill the server? Write a char name, ID, IPID or OOC name')
    found_clients = set()
    for c in client.server.client_manager.clients:
        ipid_match = arg.isdigit() and int(arg) == c.ipid
        char_match = arg.lower() in c.char_name.lower()
        showname_match = c.showname and arg.lower() in c.showname.lower()
        ooc_match = c.name and arg.lower() in c.name.lower()
        if ipid_match or char_match or showname_match or ooc_match:
            found_clients.add(c)
    info = f"WHOIS lookup for {arg}:"
    for c in found_clients:
        recent_chars, most_used_chars = database.char_history(c.ipid)
        last_shownames = database.recent_shownames(c.ipid)
        last_ooc_names = database.recent_ooc_names(c.ipid)
        last_hdids = database.hdid_history(c.ipid)
        info += f"\n ID: [{c.id}]"
        info += f" | Char ID: {c.char_id} | Char Name: {c.char_name}"
        if c.showname != "":
            info += f": | Showname: {c.showname}"
        info += f" | IPID: {c.ipid}"
        if c.name != "":
            info += f": | OOC Name: {c.name}"
        info += f"\n 7 last chars used: {recent_chars}"
        info += f"\n 7 most used chars: {most_used_chars}"
        info += f"\n 7 last shownames used: {last_shownames}"
        info += f"\n 7 last OOC names used: {last_ooc_names}"
        info += f"\n 7 last HDIDs used: {last_hdids}"
    info += f"\nMatched {len(found_clients)} online clients."
    client.send_ooc(info)

@mod_only()
def ooc_cmd_multiclients(client, arg):
    """
    Get all the multi-clients of the IPID provided. Detects multiclients on the same hardware even if the IPIDs are different.
    Usage: /multiclients <ipid>
    Alias: /mc
    """
    if len(arg) == 0:
        arg = str(client.ipid)
    found_clients = set()
    for c in client.server.client_manager.clients:
        if arg == str(c.ipid):
            found_clients.add(c)
            found_clients |= set(client.server.client_manager.get_multiclients(c.ipid, c.hdid))
    info = f"Clients belonging to {arg}:"
    for c in found_clients:
        info += f"\n ID: [{c.id}]"
        info += f" | Char Name: {c.char_name}"
        if c.showname != "":
            info += f": | Showname: {c.showname}"
        info += f" | IPID: {c.ipid}"
        if c.name != "":
            info += f": | OOC {c.name}"
    info += f"\nMatched {len(found_clients)} online clients."
    client.send_ooc(info)

@mod_only()
def ooc_cmd_lastchar(client, arg):
    """
    Prints IPID of the last user on a specificed character in the current area.
    Usage: /lastchar <character name|char id>
    Alias: /lc
    """
    if not (arg):
        raise ArgumentError('You must specify a character name or ID.')
    try:
        cid = int(arg)
    except ValueError:
        try:
            cid = client.server.get_char_id_by_name(arg)
        except ServerError:
            raise
    try:
        ex_list = client.area.shadow_status[cid]
    except KeyError:
        client.send_ooc("Character hasn't been occupied in area since server start.")
        return
    last_ipid = ex_list[0]
    last_shownames = database.recent_shownames(last_ipid)
    last_ooc_names = database.recent_ooc_names(last_ipid)
    info = f"lastchar lookup for {arg}:\n"
    info += f"IPID: {ex_list}\n"
    info += f"Last Known Shownames: {last_shownames}\n"
    info += f"Last Known OOCs {last_ooc_names}."
    client.send_ooc(info)

@mod_only()
def ooc_cmd_kick(client, arg):
    """
    Kick a player.
    Usage: /kick <ipid|*|!> [reason]
    Alias: /k <ipid|*|!> [reason]
    Special cases:
     - "*" kicks everyone in the current area.
     - "!" kicks everyone in the server.
    """
    if len(arg) == 0:
        raise ArgumentError('You must specify a target. Use /kick <ipid> [reason]')
    elif arg[0] == '*':
        targets = [c for c in client.area.clients if c != client]
    elif arg[0] == '!':
        targets = [c for c in client.server.client_manager.clients if c != client]
    else:
        targets = None
    args = list(arg.split(' '))
    if targets is None:
        raw_ipid = args[0]
        try:
            ipid = int(raw_ipid)
        except:
            raise ClientError(f'{raw_ipid} does not look like a valid IPID.')
        targets = client.server.client_manager.get_targets(client, TargetType.IPID,
                                                           ipid, False)
    if targets:
        reason = ' '.join(args[1:])
        if reason == '':
            reason = 'N/A'
        for c in targets:
            database.log_misc('kick', client, target=c,data={'reason': reason})
            client.send_ooc("{} was kicked.".format(c.char_name))
            c.send_command('KK', reason)
            c.disconnect()
    else:
        try:
            client.send_ooc(f'No targets with the IPID {ipid} were found.')
        except:
            client.send_ooc('No targets to kick!')

def ooc_cmd_kms(client, arg):
    """
    Stands for Kick MySelf - Kick other instances of the client opened by you.
    Useful if you lose connection and the old client is ghosting.
    Usage: /kms
    """
    if arg != "":
        raise ArgumentError("This command takes no arguments!")
    for target in client.server.client_manager.get_multiclients(client.ipid, client.hdid):
        if target != client:
            target.disconnect()
    client.send_ooc("Kicked other instances of client.")
    database.log_misc("kms", client)

@mod_only()
def ooc_cmd_ban(client, arg):
    """
    Ban a user. If a ban ID is specified instead of a reason,
    then the IPID is added to an existing ban record.
    Ban durations are 6 hours by default.
    Usage: /ban <ipid> "reason" ["<N> <minute|hour|day|week|month>(s)|perma"]
    Alias: /b <ipid> "reason" ["<N> <minute|hour|day|week|month>(s)|perma"]
    """
    kickban(client, arg, False)

@mod_only()
def ooc_cmd_banhdid(client, arg):
    """
    Ban both a user's HDID and IPID.
    Ban durations are 6 hours by default.
    Usage: /banhdid <ipid> "reason" ["<N> <minute|hour|day|week|month>(s)|perma"]
    Alias: /bh <ipid> "reason" ["<N> <minute|hour|day|week|month>(s)|perma"]
    """
    kickban(client, arg, True)

def _find_area(client, area_name):
    try:
        return client.server.area_manager.get_area_by_id(int(area_name))
    except:
        try:
            return client.server.area_manager.get_area_by_name(area_name)
        except ValueError:
            raise ArgumentError('Area ID must be a name or a number.')

@mod_only()
def ooc_cmd_unban(client, arg):
    """
    Unban a list of users.
    Usage: /unban <ban_id>
    Alias: /ub <ban_id>
    """
    if len(arg) == 0:
        raise ArgumentError('You must specify a target. Use /unban <ban_id...>')
    args = list(arg.split(' '))
    client.send_ooc(f'Attempting to lift {len(args)} ban(s)...')
    for ban_id in args:
        ban_info = database.find_ban(ban_id=ban_id)
        if ban_info is not None:
            try:
                special_ban_data = json.loads(ban_info.ban_data)
                if special_ban_data['ban_type'] == 'area_curse':
                    _area_uncurse(client, ban_info)
            except (KeyError, ValueError, TypeError):
                pass
            database.unban(ban_id=ban_id)
            client.send_ooc(f'Removed ban ID {ban_id}.')
            database.log_misc('unban', client, data={'id': ban_id})
        else:
            client.send_ooc(f'{ban_id} is not on the ban list.')

@mod_only()
def ooc_cmd_bans(client, _arg):
    """
    Get the 5 most recent bans.
    Usage: /bans
    Alias: /bs
    """
    msg = 'Last 5 bans:\n'
    for ban in database.recent_bans():
        time = arrow.get(ban.ban_date).humanize()
        msg += f'{time}: {ban.banned_by_name} ({ban.banned_by}) issued ban ' \
               f'{ban.ban_id} (\'{ban.reason}\')\n'
    client.send_ooc(msg)

@mod_only()
def ooc_cmd_baninfo(client, arg):
    """
    Get information about a ban.
    By default, id identifies a ban_id.
    Usage: /baninfo <id> ['ban_id'|'ipid'|'hdid']
    Alias: /bi <id> ['ban_id'|'ipid'|'hdid']
    """
    args = arg.split(' ')
    if len(arg) == 0:
        raise ArgumentError('You must specify an ID.')
    elif len(args) == 1:
        lookup_type = 'ban_id'
    else:
        lookup_type = args[1]
    if lookup_type not in ('ban_id', 'ipid', 'hdid'):
        raise ArgumentError('Incorrect lookup type.')
    bans = database.ban_history(**{lookup_type: args[0]})
    if bans is None:
        client.send_ooc('No ban found for this ID.')
    else:
        msg = f'Bans for {lookup_type} {args[0]}:'
        for ban in bans:
            msg += f'\nBan ID: {ban.ban_id}\n'
            msg += 'Affected IPIDs: ' + \
                ', '.join([str(ipid) for ipid in ban.ipids]) + '\n'
            msg += 'Affected HDIDs: ' + ', '.join(ban.hdids) + '\n'
            msg += f'Reason: "{ban.reason}"\n'
            msg += f'Unbanned: {bool(ban.unbanned)}\n'
            msg += f'Banned by: {ban.banned_by_name} ({ban.banned_by})\n'
            ban_date = arrow.get(ban.ban_date)
            msg += f'Banned on: {ban_date.format()} ({ban_date.humanize()})\n'
            if ban.unban_date is not None:
                unban_date = arrow.get(ban.unban_date)
                msg += f'Unban date: {unban_date.format()} ({unban_date.humanize()})'
            else:
                msg += 'Unban date: N/A'
        client.send_ooc(msg)

@mod_only()
def ooc_cmd_mute(client, arg):
    """
    Prevent a user from speaking in-character.
    Usage: /mute <ipid|*>
    Alias: /mu <ipid|*>
    Special cases:
    "*" mutes everyone in the current area.
    """
    if len(arg) == 0:
        raise ArgumentError('You must specify a target. Use /mute <ipid>.')
    elif arg[0] == '*':
        clients = [c for c in client.area.clients if c.is_mod == False]
    else:
        clients = None
    args = list(arg.split(' '))    
    if clients is None:
        client.send_ooc(f'Attempting to mute {len(args)} IPIDs.')
        for raw_ipid in args:
            if raw_ipid.isdigit():
                ipid = int(raw_ipid)
                clients = client.server.client_manager.get_targets(client, TargetType.IPID, ipid, False)
                if (clients):
                    msg = 'Muted the IPID ' + str(ipid) + '\'s following clients:'
                    for c in clients:
                        c.is_muted = True
                        database.log_misc('mute', client, target=c)
                        msg += ' ' + c.char_name + ' [' + str(c.id) + '],'
                    msg = msg[:-1]
                    msg += '.'
                    client.send_ooc(msg)
                else:
                    client.send_ooc("No targets found. Use /mute <ipid> <ipid> ... for mute.")
            else:
                client.send_ooc(f'{raw_ipid} does not look like a valid IPID.')
    elif clients:
        client.send_ooc('Attempting to mute the area.')
        for c in clients:
            c.is_muted = True
            database.log_misc('mute', client, target=c)
        client.send_ooc(f'Muted {len(args)} IPIDs.')
        client.area.broadcast_ooc('Area has been muted.')

@mod_only()
def ooc_cmd_unmute(client, arg):
    """
    Unmute a user.
    Usage: /unmute <ipid|*>
    Alias: /un <ipid|*>
    Special cases:
    "*" unmutes everyone in the current area.
    """
    if len(arg) == 0:
        raise ArgumentError('You must specify a target.')
    elif arg[0] == '*':
        clients = client.area.clients
    else:
        clients = None
    args = list(arg.split(' '))
    if clients is None:
        client.send_ooc(f'Attempting to unmute {len(args)} IPIDs.')
        for raw_ipid in args:
            if raw_ipid.isdigit():
                ipid = int(raw_ipid)
                clients = client.server.client_manager.get_targets(
                    client, TargetType.IPID, ipid, False)
                if (clients):
                    msg = f'Unmuted the IPID ${str(ipid)}\'s following clients:'
                    for c in clients:
                        c.is_muted = False
                        database.log_misc('unmute', client, target=c)
                        msg += ' ' + c.char_name + ' [' + str(c.id) + '],'
                    msg = msg[:-1]
                    msg += '.'
                    client.send_ooc(msg)
                else:
                    client.send_ooc("No targets found. Use /unmute <ipid> <ipid> ... for unmute.")
            else:
                client.send_ooc(f'{raw_ipid} does not look like a valid IPID.')
    elif clients:
        client.send_ooc('Attempting to unmute the area.')
        for c in clients:
            c.is_muted = False
            database.log_misc('unmute', client, target=c)
        client.send_ooc(f'Unmuted {len(args)} IPIDs.')
        client.area.broadcast_ooc('Area has been unmuted.')

@mod_only()
def ooc_cmd_ooc_mute(client, arg):
    """
    Prevent a user from talking out-of-character.
    Usage: /ooc_mute <ooc-name|*|!>
    Alias: /oocm <ooc-name|*|!>
    Special cases:
    "*" ooc mutes everyone in the current area.
    "!" ooc mutes everyone in the server.
    """
    alert = None
    if len(arg) == 0:
        raise ArgumentError('You must specify a target. Use /ooc_mute <OOC-name>.')
    elif arg[0] == '*':
        targets = [c for c in client.area.clients if c.is_mod == False]
        alert = "Area has been OOC muted."
    elif arg[0] == '!':
        targets = [c for c in client.server.client_manager.clients if c.is_mod == False]
        alert = "Server has been OOC muted."
    else:
        targets = client.server.client_manager.get_targets(client,
                                                       TargetType.OOC_NAME,
                                                       arg, False)
    if not targets:
        raise ArgumentError('Targets not found. Use /ooc_mute <OOC-name>.')
    for target in targets:
        target.is_ooc_muted = True
        database.log_room('ooc_mute', client, client.area, target=target)
    client.send_ooc('Muted {} existing client(s).'.format(
        len(targets)))
    if alert:
        client.area.broadcast_ooc(alert)

@mod_only()
def ooc_cmd_ooc_unmute(client, arg):
    """
    Allow an OOC-muted user to talk out-of-character.
    Usage: /ooc_unmute <ooc-name|*|!>
    Alias: /oocu <ooc-name|*|!>
    Special cases:
    "*" ooc unmutes everyone in the current area.
    "!" ooc unmutes everyone in the server.
    """
    alert = None
    if len(arg) == 0:
        raise ArgumentError('You must specify a target. Use /ooc_unmute <OOC-name>.')
    elif arg[0] == '*':
        targets = client.area.clients
        alert = "Area has been OOC unmuted."
    elif arg[0] == '!':
        targets = [c for c in client.server.client_manager.clients if c.is_mod == False]
        alert = "Server has been OOC unmuted."
    else:
        targets = client.server.client_manager.get_ooc_muted_clients()
    if not targets:
        raise ArgumentError('Targets not found. Use /ooc_unmute <OOC-name>.')
    for target in targets:
        target.is_ooc_muted = False
        database.log_room('ooc_unmute', client, client.area, target=target)
    client.send_ooc('Unmuted {} existing client(s).'.format(len(targets)))
    if alert:
        client.area.broadcast_ooc(alert)

@mod_only()
def ooc_cmd_area_curse(client, arg):
    """
    Ban a player from all areas except one, even if they reconnect.
    To uncurse. use the /unban command.
    Usage: /area_curse <ipid> <area_ID> "reason" ["<N> <minute|hour|day|week|month>(s)|perma"]
    Alias: /ac <ipid> <area_ID> "reason" ["<N> <minute|hour|day|week|month>(s)|perma"]
    """
    args = shlex.split(arg)
    default_ban_duration = client.server.config['default_ban_duration']
    if len(args) < 3:
        raise ArgumentError('Not enough arguments.')
    else:
        ipid = _convert_ipid_to_int(args[0])
        target_area = _find_area(client, args[1])
        reason = args[2]
    if len(args) == 3:
        ban_duration = parse(str(default_ban_duration))
        unban_date = arrow.get().shift(seconds=ban_duration).datetime
    elif len(args) == 4:
        duration = args[3]
        ban_duration = parse(str(duration))
        if duration is None:
            raise ArgumentError('Invalid ban duration.')
        elif 'perma' in duration.lower():
            unban_date = None
        else:
            if ban_duration is not None:
                unban_date = arrow.get().shift(seconds=ban_duration).datetime
            else:
                raise ArgumentError(f'{duration} is an invalid ban duration')
    else:
        raise ArgumentError(f'Ambiguous input: {arg}\nPlease wrap your arguments '
                            'in quotes.')
    special_ban_data = json.dumps({'ban_type': 'area_curse','target_area': target_area.id})
    ban_id = database.ban(ipid, reason, ban_type='ipid', banned_by=client,
                          unban_date=unban_date, special_ban_data=special_ban_data)
    targets = client.server.client_manager.get_targets(client, TargetType.IPID, ipid, False)
    for c in targets:
        c.send_ooc('You are now bound to this area.')
        c.area_curse = target_area.id
        c.area_curse_info = database.find_ban(ban_id=ban_id)
        try:
            c.change_area(target_area)
        except ClientError:
            pass
        database.log_misc('area_curse', client, target=c, data={'ban_id': ban_id, 'reason': reason})
    if targets:
        client.send_ooc(f'{len(targets)} clients were area cursed.')
    client.send_ooc(f'{ipid} was area cursed. Ban ID: {ban_id}')

def _area_uncurse(client, ban_info):
    for ipid in ban_info.ipids:
        targets = client.server.client_manager.get_targets(client, TargetType.IPID, ipid, False)
        for c in targets:
            database.log_misc('uncurse', c, data={'id': ban_info.ban_id})
            c.area_curse = None
            c.area_curse_info = None
            c.send_ooc('You were uncursed from your area. Be free!')

def _convert_ipid_to_int(value):
    try:
        return int(value)
    except ValueError:
        raise ClientError(f'{value} does not look like a valid IPID.')

@mod_only()
def kickban(client, arg, ban_hdid):
    args = shlex.split(arg)
    if len(args) < 2:
        raise ArgumentError("Not enough arguments.")
    elif len(args) == 2:
        reason = None
        ban_id = None
        try:
            ban_id = int(args[1])
            unban_date = None
        except ValueError:
            reason = args[1]
            unban_date = arrow.get().shift(hours=6).datetime
    elif len(args) == 3:
        ban_id = None
        reason = args[1]
        if "perma" in args[2]:
            unban_date = None
        else:
            duration = pytimeparse.parse(args[2], granularity="hours")
            if duration is None:
                raise ArgumentError("Invalid ban duration.")
            unban_date = arrow.get().shift(seconds=duration).datetime
    else:
        raise ArgumentError(f"Ambiguous input: {arg}\nPlease wrap your arguments " "in quotes.")
    try:
        raw_ipid = args[0]
        ipid = int(raw_ipid)
    except ValueError:
        raise ClientError(f"{raw_ipid} does not look like a valid IPID.")
    ban_id = database.ban(
        ipid,
        reason,
        ban_type="ipid",
        banned_by=client,
        ban_id=ban_id,
        unban_date=unban_date,
    )
    if ipid is not None:
        targets = client.server.client_manager.get_targets(client, TargetType.IPID, ipid, False)
        if targets:
            for c in targets:
                if ban_hdid:
                    database.ban(c.hdid, reason,
                                 ban_type="hdid", ban_id=ban_id)
                c.send_command("KB", reason)
                c.disconnect()
                database.log_misc("ban", client, target=c,
                                  data={"reason": reason})
            client.send_ooc(f"{len(targets)} clients were kicked.")
        client.send_ooc(f"{ipid} was banned. Ban ID: {ban_id}")
