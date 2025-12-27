import shlex
import re

from server import database
from server.constants import TargetType
from server.exceptions import ClientError, ServerError, ArgumentError, AreaError

from . import mod_only

__all__ = [
    'ooc_cmd_doc',
    'ooc_cmd_cleardoc',
    'ooc_cmd_view_evimod',
    'ooc_cmd_evidence_mod',
    'ooc_cmd_evidence',
    'ooc_cmd_evidence_add',
    'ooc_cmd_evidence_swap',
    'ooc_cmd_evidence_remove',
    'ooc_cmd_afk',
    'ooc_cmd_cm',
    'ooc_cmd_uncm',
    'ooc_cmd_clear_cm',
    'ooc_cmd_setcase',
    'ooc_cmd_anncase',
    'ooc_cmd_blockwtce',
    'ooc_cmd_unblockwtce',
    'ooc_cmd_judgelog',
    'ooc_cmd_testimony',
    'ooc_cmd_testimony_start',
    'ooc_cmd_te_end',
    'ooc_cmd_testimony_continue',
    'ooc_cmd_testimony_remove',
    'ooc_cmd_testimony_clear',
    'ooc_cmd_testimony_amend',
    'ooc_cmd_testimony_insert',
    'ooc_cmd_examination_start'
]


def ooc_cmd_doc(client, arg):
    """
    Show or change the link for the current case document.
    Usage: /doc [url]
    """
    if len(arg) == 0:
        client.send_ooc(f'Document: {client.area.doc}')
        database.log_room('doc.request', client, client.area)
    else:
        client.area.change_doc(arg)
        client.area.broadcast_ooc('{} changed the doc link.'.format(client.char_name))
        database.log_room('doc.change', client, client.area, message=arg)

def ooc_cmd_cleardoc(client, arg):
    """
    Clear the link for the current case document.
    Usage: /cleardoc
    Alias: /cdoc
    """
    if len(arg) != 0:
        raise ArgumentError('This command has no arguments.')
    client.area.change_doc()
    client.area.broadcast_ooc('{} cleared the doc link.'.format(client.char_name))
    database.log_room('doc.clear', client, client.area)

def ooc_cmd_view_evimod(client, arg):
    """
    View the current evidence privilege mode.
    Usage: /view_evimod
    Alias: /vevim
    """
    client.send_ooc(f'current evidence mod: {client.area.evidence_mod}')

@mod_only()
def ooc_cmd_evidence_mod(client, arg):
    """
    Change the evidence privilege mode. Refer to the documentation for more information on the function of each mode.
    Usage: /evidence_mod <FFA|Mods|CM|HiddenCM>
    Alias: /evim
    """
    if not arg or arg == client.area.evidence_mod:
        client.send_ooc(f'current evidence mod: {client.area.evidence_mod}')
    elif arg in ['FFA', 'Mods', 'CM', 'HiddenCM']:
        if client.area.evidence_mod == 'HiddenCM':
            for i in range(len(client.area.evi_list.evidences)):
                client.area.evi_list.evidences[i].pos = 'all'
        client.area.evidence_mod = arg
        client.send_ooc(f'current evidence mod: {client.area.evidence_mod}')
        database.log_room('evidence_mod', client, client.area, message=arg)
    else:
        raise ArgumentError('Wrong Argument. Use /evidence_mod <MOD>. Possible values: FFA, CM, Mods, HiddenCM')

def ooc_cmd_evidence(client, arg):
    """
    Use /evidence to read all evidence in the area.
    Use /evidence [evi_name/id] to read specific evidence.
    Usage: /evidence [evi_name/id]
    Alias: /evi
    """
    evi_list = client.area.get_evidence_list(client)
    if not evi_list:
        client.send_ooc(f"No evidence found in '{client.area.name}'.")
        return
    if arg == "":
        msg = f"== Evidence in '{client.area.name}' =="
        for i, evi_str in enumerate(evi_list):
            name, desc, image = evi_str.split("&")
            evi_msg = f"\n💼[{i}]: '{name}'"
            if arg == "" or arg.lower() in evi_msg.lower():
                msg += evi_msg
        msg += "\n|| Use /evidence [evi_name/id] to read specific evidence. ||"
        client.send_ooc(msg)
        return
    try:
        evidence = None
        for i, evi_str in enumerate(evi_list):
            name, desc, image = evi_str.split("&")
            if (arg.isnumeric() and int(arg) == i) or arg.lower() == name.lower():
                evidence = (name, desc, image)
                break
        if evidence is None:
            client.send_ooc(f"Target evidence not found! (/evidence {arg})")
            return
        name, desc, image = evidence
        index = int(arg) if arg.isnumeric() else i
        msg = f"==💼[{index}]: '{name}'=="
        msg += f"\n🖼️Image: {image}"
        msg += f"\n📃Desc: {desc}"
        msg += "\n|| Use /evidence to read all evidence in the area ||"
        client.send_ooc(msg)
    except ValueError:
        raise
    except (AreaError, ClientError):
        raise

def ooc_cmd_evidence_add(client, arg):
    """
    Add a piece of evidence.
    For sentences with spaces the arg should be surrounded in ""'s, for example /evidence_add Chair "It's a chair." chair.png
    Usage: /evidence_add [name] [desc] [image]
    Alias: /evia
    """
    try:
        max_args = 3
        args = shlex.split(arg)
        if len(args) == 0:
            raise ArgumentError("You must provide at least a name. Usage: /evidence_add [name] [desc] [image]")
        if len(args) > 3:
            raise ArgumentError(f"Too many arguments! Make sure to surround your args in \"\"'s if there's spaces. (/evidence_add {arg})")
        args = args + ([""] * (max_args - len(args)))
        if args[1] == "":
            args[1] = "<description>"
        if args[2] == "":
            args[2] = "empty.png"
    except ValueError as ex:
        client.send_ooc(f'{ex} (/evidence_add {arg})')
        return
    client.area.evi_list.add_evidence(client, args[0], args[1], args[2])
    database.log_room("evidence.add", client, client.area)
    client.area.broadcast_evidence_list()
    client.send_ooc(f"You have added evidence '{args[0]}'.")

def ooc_cmd_evidence_swap(client, arg):
    """
    Swap the positions of two evidence items on the evidence list.
    Usage: /evidence_swap <id> <id>
    Alias: /evis
    """
    args = list(arg.split(' '))
    if len(args) != 2:
        raise ClientError("you must specify 2 numbers")
    try:
        client.area.evi_list.evidence_swap(client, int(args[0]), int(args[1]))
        client.area.broadcast_evidence_list()
        client.send_ooc(f"You have swapped evidence {args[0]} with evidence {args[1]}.")
    except:
        raise ClientError("you must specify 2 numbers")

def ooc_cmd_evidence_remove(client, arg):
    """
    Remove a piece of evidence.
    Usage: /evidence_remove <evi_name/id>
    Alias: /evir
    """
    if arg == "":
        raise ArgumentError("Use /evidence_remove <evi_name/id> to remove that piece of evidence.")
    try:
        evi_list = client.area.get_evidence_list(client)
        evidence = None
        for i, evi_str in enumerate(evi_list):
            name, _, _ = evi_str.split("&")
            if (arg.isnumeric() and int(arg) == i) or arg.lower() == name.lower():
                evidence = evi_str
                break
        if evidence is None:
            raise AreaError(f"Target evidence not found! (/evidence_remove {arg})")
        evi_name = name
        client.area.evi_list.del_evidence(client, i)
        database.log_room("evidence.del", client, client.area)
        client.area.broadcast_evidence_list()
        client.send_ooc(f"You have removed evidence '{evi_name}'.")
    except ValueError:
        raise
    except (AreaError, ClientError):
        raise

def ooc_cmd_cm(client, arg):
    """
    Add a case manager for the current room.
    Usage: /cm <id>
    """
    if 'CM' not in client.area.evidence_mod and not client.is_mod:
        raise ClientError('You can\'t become a CM in this area')
    if len(client.area.owners) or client.is_mod == 0:
        if len(arg) > 0:
            raise ArgumentError('You cannot nominate people to be CMs when you are not one.')
        client.area.owners.append(client)
        if client.area.evidence_mod == 'HiddenCM':
            client.area.broadcast_evidence_list()
        client.server.area_manager.send_arup_cms()
        client.area.broadcast_ooc('{} [{}] is CM in this area now.'.format(client.char_name, client.id))
        database.log_room('cm.add', client, client.area, target=client, message='self-added')
    elif client in client.area.owners or client.is_mod:
        if len(arg) > 0:
            arg = arg.split(' ')
        for id in arg:
            try:
                id = int(id)
                c = client.server.client_manager.get_targets(client, TargetType.ID, id, False)[0]
                if not c in client.area.clients:
                    raise ArgumentError('You can only nominate people to be CMs when they are in the area.')
                elif c in client.area.owners:
                    client.send_ooc('{} [{}] is already a CM here.'.format(c.char_name, c.id))
                else:
                    client.area.owners.append(c)
                    if client.area.evidence_mod == 'HiddenCM':
                        client.area.broadcast_evidence_list()
                    client.server.area_manager.send_arup_cms()
                    client.area.broadcast_ooc('{} [{}] is CM in this area now.'.format(c.char_name, c.id))
                    database.log_room('cm.add', client, client.area, target=c)
            except:
                client.send_ooc(f'{id} does not look like a valid ID.')
    else:
        raise ClientError('You must be authorized to do that.')

@mod_only(area_owners=True)
def ooc_cmd_uncm(client, arg):
    """
    Remove a case manager from the current area.
    Usage: /uncm <id>
    """
    if len(arg) > 0:
        arg = arg.split(' ')
    else:
        arg = [client.id]
    for id in arg:
        try:
            id = int(id)
            c = client.server.client_manager.get_targets(client, TargetType.ID, id, False)[0]
            if c in client.area.owners:
                client.area.owners.remove(c)
                client.server.area_manager.send_arup_cms()
                client.area.broadcast_ooc('{} [{}] is no longer CM in this area.'.format(c.char_name, c.id))
                database.log_room('cm.remove', client, client.area, target=c)
            else:
                client.send_ooc('You cannot remove someone from CMing when they aren\'t a CM.')
        except:
            client.send_ooc(f'{id} does not look like a valid ID.')

@mod_only()
def ooc_cmd_clear_cm(client, arg):
    """
    Removes all case managers from the current area.
    Usage: /clear_cm
    Alias: /ccm
    """
    client.area.owners = []
    client.server.area_manager.send_arup_cms()
    client.area.broadcast_ooc('{} [{}] is no longer CM in this area.'.format(client.char_name, client.id))
    database.log_room('cm.remove', client, client.area, target=client)

# LEGACY
def ooc_cmd_setcase(client, arg):
    """
    Set the positions you are interested in taking for a case.
    (This command is used internally by the 2.6 client.)
    """
    args = re.findall(r'(?:[^\s,"]|"(?:\\.|[^"])*")+', arg)
    if len(args) == 0:
        raise ArgumentError('Please do not call this command manually!')
    else:
        client.casing_cases = args[0]
        client.casing_cm = args[1] == "1"
        client.casing_def = args[2] == "1"
        client.casing_pro = args[3] == "1"
        client.casing_jud = args[4] == "1"
        client.casing_jur = args[5] == "1"
        client.casing_steno = args[6] == "1"

# LEGACY
def ooc_cmd_anncase(client, arg):
    """
    Announce that a case is currently taking place in this area, needing a certain list of positions to be filled up.
    Usage: /anncase <message> <def> <pro> <jud> <jur> <steno>
    """
    # XXX: Merge with aoprotocol.net_cmd_casea
    if client in client.area.owners:
        if not client.can_call_case():
            raise ClientError(
                'Please wait 60 seconds between case announcements!')
        args = re.findall(r'(?:[^\s,"]|"(?:\\.|[^"])*")+', arg)
        if len(args) == 0:
            raise ArgumentError('Please do not call this command manually!')
        elif len(args) == 1:
            raise ArgumentError(
                'You should probably announce the case to at least one person.'
            )
        else:
            if not args[1] == "1" and not args[2] == "1" and not args[
                    3] == "1" and not args[4] == "1" and not args[5] == "1":
                raise ArgumentError(
                    'You should probably announce the case to at least one person.'
                )
            msg = '=== Case Announcement ===\r\n{} [{}] is hosting {}, looking for '.format(
                client.char_name, client.id, args[0])

            lookingfor = [p for p, q in
                zip(['defense', 'prosecutor', 'judge', 'juror', 'stenographer'], args[1:])
                if q == '1']

            msg += ', '.join(lookingfor) + '.\r\n=================='

            client.server.send_all_cmd_pred('CASEA', msg, args[1], args[2],
                                            args[3], args[4], args[5], '1')

            client.set_case_call_delay()

            log_data = {k: v for k, v in
                zip(('message', 'def', 'pro', 'jud', 'jur', 'steno'), args)}
            database.log_room('case', client, client.area, message=log_data)
    else:
        raise ClientError(
            'You cannot announce a case in an area where you are not a CM!')

@mod_only()
def ooc_cmd_blockwtce(client, arg):
    """
    Prevent a user from using Witness Testimony/Cross Examination buttons as a judge.
    Usage: /blockwtce <id>
    Alias: /bwtce <id>
    """
    if len(arg) == 0:
        raise ArgumentError('You must specify a target. Use /blockwtce <id>.')
    try:
        targets = client.server.client_manager.get_targets(client, TargetType.ID, int(arg), False)
    except:
        raise ArgumentError('You must enter a number. Use /blockwtce <id>.')
    if not targets:
        raise ArgumentError('Target not found. Use /blockwtce <id>.')
    for target in targets:
        target.can_wtce = False
        target.send_ooc('A moderator blocked you from using judge signs.')
        database.log_room('blockwtce', client, client.area, target=target)
    client.send_ooc('blockwtce\'d {}.'.format(targets[0].char_name))

@mod_only()
def ooc_cmd_unblockwtce(client, arg):
    """
    Allow a user to use WT/CE again.
    Usage: /unblockwtce <id>
    Alias: /ubwtce
    """
    if len(arg) == 0:
        raise ArgumentError('You must specify a target. Use /unblockwtce <id>.')
    try:
        targets = client.server.client_manager.get_targets(client, TargetType.ID, int(arg), False)
    except:
        raise ArgumentError('You must enter a number. Use /unblockwtce <id>.')
    if not targets:
        raise ArgumentError('Target not found. Use /unblockwtce <id>.')
    for target in targets:
        target.can_wtce = True
        target.send_ooc('A moderator unblocked you from using judge signs.')
        database.log_room('unblockwtce', client, client.area, target=target)
    client.send_ooc('unblockwtce\'d {}.'.format(targets[0].char_name))

@mod_only()
def ooc_cmd_judgelog(client, arg):
    """
    List the last 10 uses of judge controls in the current area.
    Usage: /judgelog
    Alias: /jl
    """
    if len(arg) != 0:
        raise ArgumentError('This command does not take any arguments.')
    jlog = client.area.judgelog
    if len(jlog) > 0:
        jlog_msg = '== Judge Log =='
        for x in jlog:
            jlog_msg += f'\r\n{x}'
        client.send_ooc(jlog_msg)
    else:
        raise ServerError('There have been no judge actions in this area since start of session.')
        
def ooc_cmd_afk(client, arg):
    """
    Adds an icon in getarea that indicates that the player is AFK
    Usage: /afk
    """
    client.server.client_manager.toggle_afk(client)
    
def ooc_cmd_testimony(client, arg):
    """
    List the current testimony in this area.
    Usage: /testimony
    Alias: /tes
    """
    if len(arg) != 0:
        raise ArgumentError('This command does not take any arguments.')
    testi = list(client.area.testimony.statements)
    if len(testi) <= 1:
        raise ServerError('There is no testimony in this area.')
    else:
        testi.pop(0)
        testi_msg = 'Testimony: '+ client.area.testimony.title
        i = 1
        for x in testi:
            testi_msg += f'\r\n{i}: '
            testi_msg += x[4]
            i = i + 1
        client.send_ooc(testi_msg)

@mod_only(area_owners=True)
def ooc_cmd_testimony_start(client, arg):
    """
    Manually start a testimony with the given title.
    Usage: /testimony_start <title>
    Alias: /tess
    """
    if arg == "":
        raise ArgumentError("You must provide a title! /testimony_start <title>.")
    if len(arg) < 3:
        raise ArgumentError("Title must contain at least 3 characters!")
    client.area.start_testimony(client, arg)
    client.area.broadcast_ooc('Please note that the first statement won\'t be recorded. To stop testifying please say "/end".')

@mod_only(area_owners=True)
def ooc_cmd_te_end(client, arg):
    """
    Manually end an active testimony or examination.
    Usage: /te_end
    Alias: /tee
    """
    client.area.end_testimony(client)

@mod_only(area_owners=True)
def ooc_cmd_testimony_continue(client, arg):
    """
    Continue an existing testimony, restarting the recording so new statements may be added.
    Usage: /testimony_continue
    Alias: /tesc
    """
    area = client.area
    if area.testimony is None or len(area.testimony.statements) == 0:
        raise ArgumentError("No testimony to continue!")
    if area.is_examining:
        raise ArgumentError("Cannot continue testimony while in examination!")
    if area.is_testifying:
        raise ArgumentError("Testimony is already being recorded!")
    area.is_testifying = True
    client.area.broadcast_ooc(f'-- {client.area.testimony.title} --\nTestimony recording restarted! All new messages will be recorded as testimony lines. Say "/end" to stop recording.')

@mod_only(area_owners=True)
def ooc_cmd_testimony_remove(client, arg):
    """
    Remove the statement at index.
    Usage: /testimony_remove <id>
    """
    try:
        index = int(arg)
    except ValueError:
        raise ArgumentError('You must provide a valid statement index to remove.')
    client.area.remove_statement(client, index)

@mod_only(area_owners=True)
def ooc_cmd_testimony_clear(client, arg):
    """
    Clears the testimony list, deleting all statements.
    Very handy, since otherwise you'd have to rewrite the testimony with
    a 1-statement new one and remove that statement manually.
    For mods and CM use only to prevent abuse.
    Usage: /testimony_clear
    Alias: /tescl
    """
    if len(arg) != 0:
        raise ArgumentError('This command does not take any arguments.')
    testi = list(client.area.testimony.statements)
    if len(testi) <= 1:
        raise ServerError('There is no testimony in this area.')
    else:
        client.area.testimony.statements = []
        client.area.testimony.title = ''
        client.send_ooc('You have cleared the testimony.')

@mod_only(area_owners=True)
def ooc_cmd_testimony_amend(client, arg):
    """
    Edit the spoken message of the statement at id.
    Usage: /testimony_amend <id> <msg>
    Alias: /tesa
    """
    args = arg.split(maxsplit=1)
    if len(args) < 2:
        raise ArgumentError("Usage: /testimony_amend <id> <msg>.")
    try:
        id = int(args[0])
    except ValueError:
        raise ArgumentError("Index must be a number!")
    new_statement = list(client.area.testimony.statements[id])
    new_statement[4] = args[1]
    client.area.amend_testimony(client, id, new_statement)

@mod_only(area_owners=True)
def ooc_cmd_testimony_insert(client, arg):
    """
    Insert into the testimony a new statement after the specified id.
    Usage: /testimony_insert <id> <msg>
    Alias: /tesi
    """
    args = arg.split(maxsplit=1)
    if len(args) <2:
        raise ArgumentError("Usage: /testimony_insert <id> <msg>.")
    try:
        id = int(args[0])
    except ValueError:
        raise ArgumentError("Index must be a number!")
    last_statement = list(client.area.testimony.statements[-1]) if client.area.testimony.statements else [None]*15
    last_statement[4] = args[1]
    new_statement = last_statement
    client.area.insert_testimony(client, id, new_statement)

@mod_only(area_owners=True)
def ooc_cmd_examination_start(client, arg):
    """
    Start an examination of the current area's testimony.
    Usage: /examination_start
    Alias: /exs
    """
    if not client.area.start_examination(client):
        return
    client.area.broadcast_ooc(f'-- {client.area.testimony.title} --\nAn examination has started!')
    client.send_ooc("Say >, <, or =<id> to navigate through the testimony. Say /end or use /te_end in ooc to end the examination.")
