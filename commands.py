import sys
import inspect
import urllib2
import json

import namedtuple
import persist
import editor
import dice

from mushyutils import swatch, colorfy, wrap


CommandArgs = namedtuple.namedtuple('CommandArgs', 'name tokens full actor')

"""
General, universal commands are defined here.

Arguments for functions, in parameter 'args' look like this:
(name, tokens, full, actor)
name - command name
tokens - full input, tokenized
full - full input, untokenized
actor - being object who used the command
"""

# These functions need to be identified for the bypass flag
INPUT_BLOCK = set()
MASKABLE = set()
SPECTATORABLE = set()


def spectatorable(func):
    """
    Decorate functions that cannot be masked.
    """
    if func not in SPECTATORABLE:
        SPECTATORABLE.add(func)
    return func


def maskable(func):
    """
    Decorate functions that cannot be masked.
    """
    if func not in MASKABLE:
        MASKABLE.add(func)
    return func


def block(func):
    """
    Decorate functions that require input blocking immediately after execution.
    """
    if func not in INPUT_BLOCK:
        INPUT_BLOCK.add(func)
    return func


def zap(args):
    """
    Allows the DM to force-disconnect another user. Can be used if there
    are errors regarding a user, or if someone misbehaves.
    Note: The zapped player's data is not saved!

    syntax: zap <player>
    """
    if not args.actor.dm:
        return False
    elif len(args.tokens) < 2:
        args.actor.sendMessage("Usage: zap <player>")
        return True
    
    if args.tokens[1] in args.actor.session:
        try:
            target = args.actor.session.getEntity(args.tokens[1])
            target.proxy.running = False
            target.session.remove(target)
            target.proxy.kill()
            args.actor.sendMessage("Disconnected " + target.name + ".")
        except:
            args.actor.sendMessage("Error while disconnecting user " + target.name + ".")
    return True


def alias(args):
    """
    Players may wish to create their own shortcuts, called "aliases"
    to allow easier playing. This is particularly useful if one repeats
    a non-trivial command often, such as a complex emote or roll. Up to
    20 aliases may be stored at once.

    syntax: alias <shortcut> <command>
            unalias <shortcut>

    Users may check their list of aliases with the "aliases" command.
    """
    if args.tokens[0] == "unalias":
        if len(args.tokens) < 2:
            return False
        key = args.tokens[1]
        if key in args.actor.aliases:
            del args.actor.aliases[key]
            args.actor.sendMessage('Alias "' + key + '" removed.')
            persist.saveEntity(args.actor)
        else:
            args.actor.sendMessage('Alias "' + key + '" does not exist.')

    elif args.tokens[0] == "aliases" or (args.tokens[0] == "alias" and len(args.tokens) == 1):
        if len(args.actor.aliases) == 0:
            args.actor.sendMessage("You have no saved aliases.")
            return True
        msg = "List of registered aliases:\n"
        for key in args.actor.aliases:
            msg += key + ":  " + args.actor.aliases[key] + "\n"
        args.actor.sendMessage(msg)

    else:
        if len(args.tokens) < 3:
            return False
        elif len(args.actor.aliases) >= 20:
            args.actor.sendMessage("You may only have up to 20 aliases saved at once.")
            return True
        key = args.tokens[1]
        alias_cmd = args.full[len(args.tokens[0] + args.tokens[1]) + 2:]
        args.actor.aliases[key] = alias_cmd
        args.actor.sendMessage('Alias "' + key + '" added.')
        persist.saveEntity(args.actor)

    return True


@spectatorable
def configure(args):
    """
    Players have several things they can customize for output. Players may
    configure these settings by using the "configure" command.

    syntax: configure <setting> [value]

    Below are a list of configurable options:
        wrap <number>  - number of columns per line, 0 = unwrapped (default:)
        saywrap        - wraps say output, toggle (default: off)
    """
    if len(args.tokens) < 2:
        return False

    setting = args.tokens[1]

    if setting in ("wrap", "cols"):
        try:
            if len(args.tokens) < 3:
                args.actor.sendMessage("Usage: configure wrap <number>")
                return True
            args.actor.settings["cols"] = int(args.tokens[2])
            args.actor.sendMessage("Lines will now wrap at " + args.tokens[2] + " characters.")
        except Exception:
            args.actor.sendMessage("Value must be a number (0 for unwrapped).")
    elif setting == "saywrap":
        args.actor.settings["saywrap"] = not args.actor.settings["saywrap"]
        if args.actor.settings["saywrap"]:
            args.actor.sendMessage("Turned say wrapping " + colorfy("ON", "green"))
        else:
            args.actor.sendMessage("Turned say wrapping " + colorfy("OFF", "green"))
    else:
        args.actor.sendMessage("That is not a valid setting. Check help settings for more details.")

    persist.saveEntity(args.actor)
    return True


def language(args):
    """
    Players may speak in a variety of different languages, so long as
    they have the OK from the DM. This command allows a player to list
    the languages that they know, or if they are a DM, register a
    language to a player. Languages are persistant.

    This ties in heavily with the say/whisper command.

    syntax: language <command>

    List of subcommands and syntax:
        list:           language list
        peek:           language peek <target>
        learn:          language learn <target> <language>
        forget:         language forget <target> <language>
    """
    if len(args.tokens) < 4:
        if len(args.tokens) == 1:
            if args.tokens[0] != 'languages':
                return False
        elif len(args.tokens) == 2:
            if args.tokens[1] != 'list':
                return False
        elif len(args.tokens) == 3:
            if args.tokens[1] != 'peek':
                return False
        else:
            return False

    tokens = args.tokens

    # tallies substitution
    if args.tokens[0] == 'languages':
        tokens = ['language', 'list']

    subcommand = tokens[1]
    target = ''
    language = ''
    div = ", "

    if len(tokens) > 2:
        target = tokens[2]
        target = target[0].upper() + target[1:]
    if len(tokens) > 3:
        language = tokens[3]
        language = language.lower()

    if subcommand == 'list':
        args.actor.sendMessage("You know the following languages: " + div.join(args.actor.languages))

    elif subcommand == 'peek' and target in args.actor.session:
        e = args.actor.session.getEntity(target)
        args.actor.sendMessage(target + " knows the following languages: " + div.join(args.actor.languages))

    elif subcommand in ('learn', 'register') and target in args.actor.session:
        e = args.actor.session.getEntity(target)
        e.languages.append(language)
        args.actor.sendMessage(target + " now understands the language: " + colorfy(language, "green"))
        e.sendMessage("You have learned the language: " + colorfy(language, "green"))
        persist.saveEntity(e)

    elif subcommand in ('forget', 'unregister') and target in args.actor.session:
        e = args.actor.session.getEntity(target)
        if language in e.languages:
            e.languages.remove(language)
            args.actor.sendMessage(target + " has forgotten the language: " + colorfy(language, "green"))
            e.sendMessage("You have forgotten the language: " + colorfy(language, "green"))
        else:
            args.actor.sendMessage(target + " does not know the language " + language + ".")

    else:
        return False

    return True


@spectatorable
def help(args):
    """
    Check these helpfiles for something.

    syntax: help <subject>
            subject - the subject or command which you want to check for help

    Known bug: Doesn't always play nice with column wrapping.
    """
    # This would normally be circular, but this is an exceptional case
    import functionmapper

    # generate the docstring mapping first
    docs = {}
    functions = inspect.getmembers(sys.modules[__name__], inspect.isfunction)
    for functionName, function in functions:
        docs[functionName] = function.__doc__

    if len(args.tokens) == 1:
        commands = functionmapper.commandFunctions.keys()
        commands.sort()

        msg = "    "
        i = 0
        for command in commands:
            if command not in docs or docs[command] is None:
                continue
            msg = msg + command + (' ' * (15 - len(command)))
            i = (i + 1) % 4
            if i == 0:
                msg = msg + "\n    "

        args.actor.sendMessage("There are help files on the following commands.\nType help <command> for details.")
        args.actor.sendMessage(msg)

        return True

    docstring = None
    if args.tokens[1] in docs:
        docstring = docs[args.tokens[1]]

    if docstring is None:
        args.actor.sendMessage("There is no helpfile for " + args.tokens[1] + ".")
    else:
        prelude = "help file for: " + args.tokens[1] + "\n" + ("-" * len("help file for: " + args.tokens[1]))
        prelude = colorfy(prelude, 'green')
        args.actor.sendMessage(prelude + docstring)

    return True


def _speak(args, second_tense, third_tense, speak_color):
    """
    Internal function used by say, whisper, and yell.

    second_tense - You say/whisper/yell
    third_tense - He says/whispers/yells
    """
    if len(args.tokens) < 2:
        return False

    full = args.full

    # Get rid of the "say" command token
    rest_tokens = args.tokens[1:]
    full = full[len(args[0]) + 1:]

    target_entity = None
    lang = None
    color_lang = None

    # CASE 1: Match on SAY IN
    if rest_tokens[0].lower() == 'in' and len(rest_tokens) >= 3:
        lang = rest_tokens[1].lower()

        if lang in args.actor.languages:
            # cut out the "in lang" portion
            full = full[len(rest_tokens[0]) + len(rest_tokens[1]) + 2:]
            rest_tokens = rest_tokens[2:]
        else:
            lang = None

        # see if there's a target in here
        if len(rest_tokens) >= 3 and rest_tokens[0].lower() == 'to':
            target_entity = args.actor.session.getEntity(rest_tokens[1])
            if target_entity is not None:
                full = full[len(rest_tokens[0]) + len(rest_tokens[1]) + 2:]
                rest_tokens = rest_tokens[2:]

    # CASE 2: Match on SAY TO
    elif len(rest_tokens) >= 3 and rest_tokens[0].lower() == 'to':
        target_entity = args.actor.session.getEntity(rest_tokens[1])

        if target_entity is not None:
            full = full[len(rest_tokens[0]) + len(rest_tokens[1]) + 2:]
            rest_tokens = rest_tokens[2:]

        # Check for language
        if len(rest_tokens) >= 3 and rest_tokens[0].lower() == 'in':
            lang = rest_tokens[1].lower()

            if lang in args.actor.languages:
                # cut out the "in lang" portion
                full = full[len(rest_tokens[0]) + len(rest_tokens[1]) + 2:]
                rest_tokens = rest_tokens[2:]
            else:
                lang = None

    if target_entity == args.actor:
        args.actor.sendMessage("Stop speaking to yourself!")
        return True

    # Properize the remaining text
    full = full[0].upper() + full[1:]
    if full[-1] not in ('.', '!', '?'):
        full = full + '.'

    if lang is not None:
        color_lang = colorfy(lang, "green")

    # A tricky runtime decoration of Entity.sendMessage, which wraps depending on settings
    def sendMessage(target, text):
        if target.settings["saywrap"]:
            text = wrap(text, cols=60, indent="    ")
        target.sendMessage(text)

    # Say stuff to a target
    if target_entity is not None:
        for e in args.actor.session.getAllEntities():
            # in a language
            if lang is not None:
                if e == args.actor:
                    sendMessage(e, colorfy('You ' + second_tense + ' to ' + target_entity.name + ' in ' + color_lang + ', "' + full + '"', speak_color))
                elif e == target_entity:
                    if lang in target_entity.languages or e.spectator:
                        sendMessage(e, colorfy(args.actor.name + ' ' + third_tense + ' to you in ' + color_lang + ', "' + full + '"', speak_color))
                    else:
                        e.sendMessage(colorfy(args.actor.name + ' ' + third_tense + ' something to you in ' + color_lang + '.', speak_color))
                else:
                    if lang in e.languages or e.spectator:
                        sendMessage(e, colorfy(args.actor.name + ' ' + third_tense + ' to ' + target_entity.name + ' in ' + color_lang + ', "' + full + '"', speak_color))
                    else:
                        e.sendMessage(colorfy(args.actor.name + ' ' + third_tense + ' something to ' + target_entity.name + ' in ' + color_lang + '.', speak_color))
            # common
            else:
                if e == args.actor:
                    sendMessage(e, colorfy('You ' + second_tense + ' to ' + target_entity.name + ', "' + full + '"', speak_color))
                elif e == target_entity:
                    sendMessage(e, colorfy(args.actor.name + ' ' + third_tense + ' to you, "' + full + '"', speak_color))
                else:
                    sendMessage(e, colorfy(args.actor.name + ' ' + third_tense + ' to ' + target_entity.name + ', "' + full + '"', speak_color))
    # Say stuff to everyone
    else:
        for e in args.actor.session.getAllEntities():
            # in a language
            if lang is not None:
                if e == args.actor:
                    sendMessage(e, colorfy('You ' + second_tense + ' in ' + color_lang + ', "' + full + '"', speak_color))
                elif lang in e.languages or e.spectator:
                    sendMessage(e, colorfy(args.actor.name + ' ' + third_tense + ' in ' + color_lang + ', "' + full + '"', speak_color))
                else:
                    e.sendMessage(colorfy(args.actor.name + ' ' + third_tense + ' something in ' + color_lang + '.', speak_color))
            # common
            else:
                if e == args.actor:
                    sendMessage(e, colorfy('You ' + second_tense + ', "' + full + '"', speak_color))
                else:
                    sendMessage(e, colorfy(args.actor.name + ' ' + third_tense + ', "' + full + '"', speak_color))

    return True


@maskable
def say(args):
    """
    Say something out loud, in character. Unless otherwise specified, things
    are said in common.

    syntax: say [modifiers] <message>

    Modifiers can be lanaguage, or target. These are expressed naturally
    and the order does not matter. See below for examples

    examples:
        say hello
        >> Eitan says, "Hello."

        say in elven "such a snob"
        >> Eitan says in elven, "Such a snob."

        say to king Hello your majesty.
        >> Eitan says to King, "Hello your majesty."

        say in dwarven to Gimli Sup brosef?
        >> Eitan says to Gimli in dwarven, "Sup, brosef?"

        say to Legolas in elven You're one pretty elf!
        >> Eitan says to Legolas in elven, "You're one pretty elf!"


    Alternatively, as a shorthand, you may start the say command with the "'" token (no space).

    example:
        'Hello, everyone!
        >>Eitan says, "Hello, everyone!"
    """
    if args.full[-1] == '?':
        return _speak(args, 'ask', 'asks', 'white')
    elif args.full[-1] == '!':
        return _speak(args, 'exclaim', 'exclaims', 'white')
    return _speak(args, 'say', 'says', 'white')


@maskable
def whisper(args):
    """
    Works just like "say", just with whisper flavor. For more info,
    check "help say".

    syntax: whisper [modifiers] <message>
    """
    return _speak(args, 'whisper', 'whispers', 'dgray')


@maskable
def yell(args):
    """
    Works just like "say", just with yell flavor. For more info,
    check "help say".

    syntax: yell [modifiers] <message>
    """
    return _speak(args, 'yell', 'yells', 'byellow')


def pm(args):
    """
    Give a private message to someone, out of character. Other people
    cannot see these messages.
    Note: This is OOC and shouldn't be abused!

    syntax: pm <player> <message>
            player - target of the pm
            message - what you would like to say privately
    """
    if not len(args.tokens) >= 3:
        return False

    if args.tokens[1] in args.actor.session:
        target = args.actor.session.getEntity(args.tokens[1])
        target.sendMessage(colorfy("[" + args.actor.name + ">>] " +
                           args.full[len(args.tokens[0] + " " + args.tokens[1] + " "):], 'purple'))
        args.actor.sendMessage(colorfy("[>>" + target.name + "] " +
                               args.full[len(args.tokens[0] + " " + args.tokens[1] + " "):], 'purple'))
    return True


@spectatorable
def who(args):
    """
    See who is connected to the MUSH server.

    syntax: who
    """
    msg = colorfy("Currently connected players:\n", "cyan")
    for e in args.actor.session.getAllEntities():
        name = colorfy(e.name, "cyan")
        if e.dm:
            name = name + colorfy(" (DM)", "bright red")
        elif e.spectator:
            name = name + colorfy(" (S)", "bright yellow")
        msg = msg + "    " + name + "\n"
    args.actor.sendMessage(msg)
    return True


@spectatorable
def logout(args):
    """
    Logs you out of the game.

    syntax: logout
    """
    args.actor.sendMessage(colorfy("[SERVER] You have quit the session.", "bright yellow"))
    args.actor.session.broadcastExclude(colorfy("[SERVER] " + args.actor.name + " has quit the session.", "bright yellow"), args.actor)
    persist.saveEntity(args.actor)
    try:
        args.actor.proxy.running = False
        args.actor.session.remove(args.actor)
        args.actor.proxy.kill()
    except:
        return True
    return True


@maskable
def emote(args):
    """
    Perform an emote. Use the ";" or "*" token as a placeholder for your name.

    syntax: emote <description containing ; somewhere>

    example:
        emote In a wild abandon, ; breaks into a fit of giggles.
        >> In a wild abandon, Eitan breaks into a fit of giggles.

        emote Smoke drifts upwards from a pipe held between ;'s lips.'
        >> Smoke drifts upwards from a pipe held between ;'s lips.'


    If no semicolon is found, your name will be stuck at the start:
        emote yawns lazily.
        >> Eitan yawns lazily.


    Alternatively, as a shorthand, you may start an emote with the ";" token
    (with no space).

    example:
        ;laughs heartedly
        >> Eitan laughs heartedly.
    """

    if len(args.tokens) < 2:
        return False

    marking = ">"
    rest = args.full[len(args.name + " "):]

    if not ';' in args.full:
        rest = args.actor.name + " " + rest
    else:
        rest = rest.replace(';', args.actor.name)

    args.actor.session.broadcast(colorfy(marking + rest, "dark gray"))
    return True


def ooc(args):
    """
    Broadcast out of character text. Anything said here is OOC.

    syntax: ooc <message>

    example:
        ooc Do I need to use a 1d6 or 1d8 for that, DM?
        >> [OOC Justin]: Do I need to use a 1d6 or 1d8 for that, DM?


    Alternatively, as a shorthand, you may start an ooc message with the
    "%" token (no space).

    example:
        %If you keep metagaming, I'm going to kill you!
        >> [OOC DM_Eitan]: If you keep metagaming, I'm going to kill you!
    """

    if len(args.tokens) < 2:
        return False

    name = args.actor.name
    if args.actor.dm:
        name = name + " (DM)"
    marking = "[OOC " + name + "]: "
    marking = colorfy(marking, "bright red")

    rest = args.full[len(args.name + " "):]
    args.actor.session.broadcast(marking + rest)

    return True


def roll(args):
    """
    Roll a dice of a specified number of sides. The dice roll is public.

    syntax: roll <sequence> [reason]

    example:
        roll 1d20
        roll 2d6 + 2 "to hit"

    
    There are some limitations on dice.
        You cannot roll over 20 dice at once (ex: 99d20)
        You cannot roll a die with over 100 sides (ex: 1d200)
        You cannot roll less tha one die, or a die with less than two sides
        The number of dice, and the number of sides, must be numerical

    Alternatively, as a shorthand, you may roll a single die of N sides
    with no specified purpose with the "#" token (no space). Standard 1d20
    rolls can be invoked by simply using the "roll" command with no arguments.

    example:
    #6      is the same as    roll 1d6
    roll    is the same as    roll 1d20


    Rolls can also be kept hidden from others. To do this, use the
    command "hroll" instead of "roll". DMs can make a special hidden
    roll that other players can't see, but still know happened, by using
    the "droll" command.

    example:
        hroll 1d20
    """

    if len(args.tokens) == 1:
        new_tokens = [args.name, "1d20"]
        new_full = args.name + " 1d20"
        newargs = CommandArgs(name=args.name, tokens=new_tokens, full=new_full, actor=args.actor)
        args = newargs
    elif len(args.tokens) < 2:
        return False

    reason_index = args.full.find('"')
    reason = ""
    if reason_index == -1:
        reason_index = len(args.full)
    else:
        reason = args.full[reason_index+1:-1]

    dice_str = args.full[len(args.tokens[0])+1:reason_index]

    visible = True
    if args.tokens[0] in ('hroll', 'droll'):
        visible = False

    if args.tokens[0] == 'droll' and not args.actor.dm:
        return False

    result = ""
    msg = ""
    try:
        result, msg = dice.parse(dice_str)
    except dice.DiceException as e:
        e_msg = 'Bad roll formatting! The clause ' + colorfy(str(e), "bred") + " is no good!"
        e_msg += '\nFor more help, try ' + colorfy("help roll", "green") + '.'
        args.actor.sendMessage(e_msg)
        return True
    pre = args.actor.name + " "
    if not visible:
        pre += colorfy("secretly ", "bred")
    pre += "rolls " + colorfy(dice_str, "yellow")
    if reason != "":
        pre += "for " + colorfy(reason, "bred")
    pre += ".\n    "
    msg = pre + msg + "    (total = " + colorfy(str(result), "yellow") + ")"

    if visible:
        args.actor.session.broadcast(msg)
    else:
        args.actor.sendMessage(msg)
        if args.tokens[0] == 'droll':
            args.actor.session.broadcastExclude(colorfy("The DM makes a hidden roll.", "bred"), args.actor)

    return True


def fudge(args):
    result, out = dice.fudge()
    msg = args.actor.name + " rolls the dice: " + out + "    (total = " + result + ")"    
    args.actor.session.broadcast(msg)
    return True


def mask(args):
    """
    Mask a command as if you were another character. Don't abuse this, DM!

    syntax: mask <name> <command>
            name - the name of the entity you wish to do something as
            command - the regular command string as if you were entering it
                      as normal

    example:
        mask King say Welcome, my subjects, to my domain!
        >> King says, "Welcome, my subjects, to my domain!"

        mask John ;bows with a flourish.
        >> John bows with a flourish.

    Alternatively, as a shorthand, you may mask as another person by using
    the "$" token (no space).

    example:
        $Nameless say Who... who am I?
        >> Nameless says, "Who... who am I?"

    Unfortunately, this can get annoying. You can set masks indefinitely by using
    the command "mask <name>". This will mask ALL commands until the DM uses the 
    command "mask clear".
    """
    # Exceptional case where we need this for husk-command-trickery
    import commandparser
    import functionmapper
    import entity
    
    if len(args.tokens) == 1 and args.tokens[0] == "unmask":
        newargs = CommandArgs("mask", ["mask", "clear"], "mask clear", args.actor)
        args = newargs

    elif len(args.tokens) == 2:
        if args.tokens[1] in ("clear", "reset", "remove"):
            args.actor.mask = None
            args.actor.sendMessage("You take off your mask.")
        else:
            huskname = args.tokens[1][0].upper() + args.tokens[1][1:]
            husk = entity.Entity(name=huskname, session=args.actor.session)
            husk.languages = args.actor.languages
            args.actor.mask = husk
            args.actor.sendMessage("You put on a " + colorfy(huskname, "green") + " mask.")
        return True

    elif not args.actor.dm:
        args.actor.sendMessage("Whoa there... This is a DM power! Bad!")
        return True

    else:
    	return False

    new_full = args.full[len(args.tokens[0] + " " + args.tokens[1] + " "):]
    new_tokens = new_full.split(" ")

    if functionmapper.commandFunctions[new_tokens[0]] not in MASKABLE:
        args.actor.sendMessage("That command cannot be masked.")
        return True

    husk = entity.Entity(name=args.tokens[1][0].upper() + args.tokens[1][1:], session=args.actor.session)
    husk.languages = args.actor.languages
    commandparser.CommandParser().parseLine(new_full, husk)
    return True


def display(args):
    """
    Display text in a color of your choosing without any "tags". Basically,
    use this as an immersion tool for typing descriptions.

    The DM may want to display text to only a particular player, and not want
    the rest of the group to be aware OOCly, allowing for better roleplay.

    syntax: display [identifier] <text>
    
    You may display things in a color, to a specific target, or both. It is
    sufficient to supply the name of the color or target. If both are
    specified, the syntax becomes:

    color@target

    To view a list of colors, type "colors". If the supplied color does not
    exist, the default is used. If the dual-identifier form is used, a target
    must be specified. The keyword "all" may be specified as well.

    example:
        display bred The flame licks at the prisoner's cheek.
        >> \033[1;31mThe flame licks at the prisoner's cheek.\033[0m

        display yellow@justin Spiritual voices wail in your mind...
        >> \033[0;33mSpiritual voices wail in your mind...\033[0m


    Alternatively, as a shorthand, having the "@" symbol in the command name
    is sufficient for sending the display command. Both a color and a target
    must be specified.

    example:
        red@all Blood trickles down your nose.
        >> \033[0;31mBlood trickles down your nose.\033[0m
    """

    if len(args.tokens) < 2:
        return False

    color = "default"
    target = None
    rest = args.full[len(args.tokens[0]) + 1:]
    if '@' not in args.tokens[1]:
        # Single token, either a color or an entity
        if args.tokens[1] in args.actor.session:
            target = args.actor.session.getEntity(args.tokens[1])
            rest = rest[len(args.tokens[1]) + 1:]
        elif args.tokens[1].lower() in swatch:
            color = args.tokens[1].lower()
            rest = rest[len(args.tokens[1]) + 1:]
    else:
        params = args.tokens[1].split("@")
        rest = rest[len(args.tokens[1]) + 1:]
        if params[0].lower() in swatch:
            color = params[0].lower()
        if params[1] in args.actor.session:
            target = args.actor.session.getEntity(params[1])
        elif params[1].lower() != "all":
            args.actor.sendMessage("There is no person named " + params[1] + ".")
            return True

    rest = colorfy(rest, color)

    if target is not None:
        target.sendMessage(rest)
        args.actor.sendMessage("You send " + target.name + ": " + rest)
    else:
        args.actor.sendMessage("You send everyone: " + rest)
        args.actor.session.broadcastExclude(rest, args.actor)

    return True


def status(args):
    """
    Set your status. This is meant to be an in-character roleplay tool. For
    example, after being struck with an arrow, you may want to set your status
    to indicate that you are injured. Treat these as an emoted "state".

    Setting these is not quiet, and will indicate to the group what is going on
    as an emote. Take care to phrase the status as a passive state. It sounds
    best if you are able to say "Soandso is..." prior to a status.

    If you specify status as "clear", it will clear your status silently.

    syntax: status <status>

    example:
        status Limping behind the group, using his staff as a cane.
        >> Eitan is limping behind the group, using his staff as a cane.

        >> glance Eitan
        >> Eitan is limping behind the group, using his staff as a cane.

        >> status clear
    """
    if len(args.tokens) < 2:
        return False

    if args.tokens[1] == 'clear':
        args.actor.status = ""
        args.actor.sendMessage("You've cleared your status.")
        return True

    status = args.full[len(args.tokens[0] + " "):]
    status = status[0].upper() + status[1:]
    if status[-1] not in (".", "!", "?"):
        status = status + "."

    args.actor.status = status
    status = status[0].lower() + status[1:]

    args.actor.sendMessage(colorfy(">You are " + status, "dark gray"))
    args.actor.session.broadcastExclude(colorfy(">" + args.actor.name + " is " + status, "dark gray"), args.actor)
    return True


@spectatorable
def glance(args):
    """
    Glance at another player to see their set status.

    syntax: glance <player>
    """

    if len(args.tokens) < 2:
        return False

    if args.tokens[1] in args.actor.session:
        target = args.actor.session.getEntity(args.tokens[1])
        args.actor.sendMessage("You glance at " + target.name + ".")
        if target.status == "":
            return True
        status = target.status[0].lower() + target.status[1:]
        args.actor.sendMessage("  " + target.name + " is " + colorfy(status, "dark gray"))
    else:
        args.actor.sendMessage('There is no player "' + args.tokens[1] + '" here.')
    return True


@spectatorable
def examine(args):
    """
    Examines another player's profile.

    syntax: examine <player>
    """

    if len(args.tokens) != 2:
        return False

    if args.tokens[1] in args.actor.session:
        target = args.actor.session.getEntity(args.tokens[1])
        top = target.name + "'s Profile"
        args.actor.sendMessage(top)
        args.actor.sendMessage("-"*len(top))
        if target.facade is not None and target.facade != "":
            args.actor.sendMessage(target.facade)
        else:
            args.actor.sendMessage(target.name + "'s profile is empty.")
    return True


@spectatorable
def colors(args):
    """
    Displays a list of the colors available for use in certain commands.

    syntax: colors
    """

    msg = """    List of colors:
        \033[0mDEFAULT\033[0m
        \033[1;37mWHITE\033[0m
        \033[0;37mBGRAY\033[0m
        \033[1;30mDGRAY\033[0m
        \033[0;30mBLACK\033[0m
        \033[0;34mBLUE\033[0m
        \033[1;34mBBLUE\033[0m
        \033[0;36mCYAN\033[0m
        \033[1;36mBCYAN\033[0m
        \033[0;32mGREEN\033[0m
        \033[1;32mBGREEN\033[0m
        \033[0;33mYELLOW\033[0m
        \033[1;33mBYELLOW\033[0m
        \033[0;31mRED\033[0m
        \033[1;31mBRED\033[0m
        \033[0;35mPURPLE\033[0m
        \033[1;35mBPURPLE\033[0m
    """
    args.actor.sendMessage(msg)
    return True


def paint(args):
    """
    A DM may "paint" the current scene of the session for players to
    view. Two things may be painted in a scene.
        "Scene" title - The name of the scene
        "Scene" body - The description of the scene

    Players may look at the scene by using the "look" command with no
    arguments. The color of the painted text is dictated by the brush
    setting. For information on setting a color, check "help brush".

    syntax: paint <title | body> <description>

    To view a list of colors, type "colors".

    example:
        paint title Inferno Cave
        paint body Lava swirls around burning stone in a river of red.
    """
    if len(args.tokens) < 3:
        return False

    if not args.actor.dm:
        return False

    tokens = args.tokens
    stage = args.actor.session.stage
    color = stage.getBrush(args.actor)
    snip = len(tokens[0]) + len(tokens[1]) + 2

    if tokens[1] == "title":
        stage.paintSceneTitle(colorfy(args.full[snip:], color))
        args.actor.session.broadcast(colorfy(args.actor.name + " gives the scene a name.", "bright red"))

    elif tokens[1] == "body":
        stage.paintSceneBody(colorfy(args.full[snip:], color))
        args.actor.session.broadcast(colorfy(args.actor.name + " paints the scene.", "bright red"))

    else:
        return False

    return True


def sculpt(args):
    """
    A DM may "sculpt" an item of interest for players to view.
    Players may look at the item by using the "look" command the tag
    of the placed item as an argument. Players may also see a list of
    currently placed items by simply using "look" with no arguments.

    The color of the painted text is dictated by the brush setting.
    For information on setting a color, check "help brush".

    syntax: sculpt <tag> <description>
            sculpt remove <tag>

    To view a list of colors, type "colors".

    example:
        sculpt rat A little black rat scurries across the floor.
    """
    if len(args.tokens) < 3:
        return False

    if not args.actor.dm:
        return False

    if args.tokens[1] == 'remove':
        tag = args.tokens[2]
        if tag in args.actor.session.stage.objects:
            args.actor.session.stage.eraseObject(tag)
        else:
            args.actor.sendMessage("There is no " + tag + " in the scene.")

    else:
        stage = args.actor.session.stage
        color = stage.getBrush(args.actor)
        snip = len(args.tokens[0]) + len(args.tokens[1]) + 2
        stage.paintObject(args.tokens[1], colorfy(args.full[snip:], color))
        args.actor.session.broadcast(colorfy(args.actor.name + " sculpts an object into the scene.", "bright red"))

    return True


def brush(args):
    """
    A DM may set a color for scene and object creation. The
    color of all subsequent paint or sculpt commands are
    dictated by the brush, set by this command.

    The brush defaults to white if unset, or reset.

    syntax: brush <color>
            brush clean

    To view a list of colors, type "colors".
    """
    if len(args.tokens) < 2:
        return False

    if not args.actor.dm:
        return False

    color = args.tokens[1]
    if color.lower() not in swatch:
        color = color[0].upper() + color[1:]
        args.actor.sendMessage(color + ' is not a valid color. Type "colors" for a list of colors.')
    elif color == "reset":
        args.actor.session.stage.resetBrush(args.actor)
        args.actor.sendMessage("Your brush is now default.")
    else:
        args.actor.session.stage.setBrush(args.actor, color)
        args.actor.sendMessage("Your brush is now " + colorfy(color, color) + ".")

    return True


def wipe(args):
    """
    A DM may wipe an entire scene and all objects painted in it.

    syntax: wipe
    """
    if not args.actor.dm:
        return False

    stage = args.actor.session.stage
    stage.wipeScene()
    stage.wipeObjects()
    args.actor.session.broadcast(colorfy(args.actor.name + " wipes the whole scene.", "bright red"))

    return True


@spectatorable
def look(args):
    """
    Allows a player to look at a scene, or a particular painted object.

    syntax: look [tag]
            tag - the identifier to use when "looking" at an object

    To view a list of objects in the scene, simply use look without arguments.
    """
    stage = args.actor.session.stage

    if len(args.tokens) == 1:
        scene = stage.viewScene()
        if scene == "":
            args.actor.sendMessage("The scene is blank.")
        else:
            args.actor.sendMessage(scene)
        return True

    description = stage.viewObject(args.tokens[1])
    if description == "":
        args.actor.sendMessage('There is no "' + args.tokens[1] + '" in the scene.')
    else:
        args.actor.sendMessage("You look at the " + args.tokens[1] + ".")
        args.actor.sendMessage(description)
    return True


def tally(args):
    """
    A player or DM may create a generic "tally" to keep track of something.
    Tallies may be saved (persistent) or not (removed after logout).

    syntax: tally <subcommand> <tag>

    List of subcommands and syntax:
        Add/Sub:        tally add/sub <tag> [amount]
        Change:         tally change <tag> <value>
        Check:          tally check [tag]
        Peek:           tally peek <entity> [tag]
        Create:         tally create <tag> [initial]
        Destroy:        tally destroy <tag>
        Share:          tally share <tag> [entity]
        Save/Unsave:    tally save/unsave <tag>

    There are a few shorthand commands for your convenience. You may increment
    or decrement a tally easily using the following syntax:
        tally <tag> ++
        tally <tag> --

    You may also check the values for all your tallies by simply entering
    the command 'tallies'.
    """

    if len(args.tokens) < 3:
        if len(args.tokens) == 1:
            if args.tokens[0] != 'tallies':
                return False
        elif len(args.tokens) == 2:
            if args.tokens[1] != 'check':
                return False
        else:
            return False

    tokens = args.tokens

    # tallies substitution
    if args.tokens[0] == 'tallies':
        tokens = ['tally', 'check']

    # shorthand substitution
    elif '++' in args.full or '--' in args.full:
        if tokens[2] == '++':
            tokens = ['tally', 'add', tokens[1]]
        elif tokens[2] == '--':
            tokens = ['tally', 'sub', tokens[1]]

    subcommand = tokens[1]
    tag = ''
    if len(tokens) > 2:
        tag = tokens[2]

    if subcommand == 'create':
        if tag in args.actor.tallies:
            args.actor.sendMessage("Tally " + tag + " already exists.")
        else:
            value = 0
            if len(tokens) > 3:
                value = int(tokens[3])
            args.actor.tallies[tag] = value
            args.actor.sendMessage("Tally " + tag + " initialized to " + str(value) + ".")

    elif subcommand == 'destroy' or subcommand == 'delete':
        if tag in args.actor.tallies:
            del args.actor.tallies[tag]
            args.actor.sendMessage("Tally " + tag + " destroyed.")
        else:
            args.actor.sendMessage("Tally " + tag + " does not exist.")

    elif subcommand == 'add':
        if tag in args.actor.tallies:
            value = 1
            if len(tokens) > 3:
                value = int(tokens[3])
            args.actor.tallies[tag] += value
            args.actor.sendMessage("Tally " + tag + " incremented to: " + str(args.actor.tallies[tag]))
        else:
            args.actor.sendMessage("Tally " + tag + " does not exist.")

    elif subcommand == 'subtract' or subcommand == 'sub':
        if tag in args.actor.tallies:
            value = 1
            if len(tokens) > 3:
                try:
                    value = int(tokens[3])
                except:
                    return False
            args.actor.tallies[tag] -= value
            args.actor.sendMessage("Tally " + tag + " incremented to: " + str(args.actor.tallies[tag]))
        else:
            args.actor.sendMessage("Tally " + tag + " does not exist.")

    elif subcommand == 'change':
        if tag in args.actor.tallies:
            if len(tokens) > 3:
                try:
                    value = int(tokens[3])
                except:
                    return False
                args.actor.tallies[tag] = value
                args.actor.sendMessage("Tally " + tag + " value now set to " + str(value) + ".")
            else:
                args.actor.sendMessage("Usage: tally change <tag> <amount>")
        else:
            args.actor.sendMessage("Tally " + tag + " does not exist.")

    elif subcommand == 'share' or subcommand == 'show' or subcommand == 'display':
        if tag in args.actor.tallies:
            if len(tokens) > 3:
                if tokens[3] in args.actor.session:
                    target = args.actor.session.getEntity(tokens[3])
                    target.sendMessage(args.actor.name + " shares a tally with you: [" +
                                       colorfy(tag, 'white') + ": " + colorfy(str(args.actor.tallies[tag]), 'cyan') + "]")
                    args.actor.sendMessage("You share tally " + tag + " with " + tokens[3] + ": [" +
                                           colorfy(tag, 'white') + ": " + colorfy(str(args.actor.tallies[tag]), 'cyan') + "]")
            else:
                args.actor.session.broadcast(args.actor.name + " shares a tally: [" +
                                             colorfy(tag, 'white') + ": " + colorfy(str(args.actor.tallies[tag]), 'cyan') + "]")
        else:
            args.actor.sendMessage("Tally " + tag + " does not exist.")

    elif subcommand == 'peek':
        if not args.actor.dm:
            return False
        target = args.actor.session.getEntity(tag)
        if not target:
            return False
        tag = ''
        if len(tokens) > 3:
            tag = tokens[3]
        if tag == '':
            keys = target.tallies.keys()
            if len(keys) == 0:
                args.actor.sendMessage(target.name + "has no tallies.")
                return True

            args.actor.sendMessage("------" + target.name.upper() + "'S TALLIES------")
            sorted(keys)
            perma_mark = "(" + colorfy("saved", "green") + ")"
            for key in keys:
                s = "    [" + colorfy(key, 'white') + ": " + colorfy(str(target.tallies[key]), 'cyan') + "]"
                if key in target.tallies_persist:
                    s = s + " " + perma_mark
                args.actor.sendMessage(s)
        elif tag in target.tallies:
            args.actor.sendMessage("The value of " + target.name + "'s tally " + tag + " is " + colorfy(str(args.actor.tallies[tag]), 'cyan') + ".")
        else:
            args.actor.sendMessage(target.name + "'s tally " + tag + " does not exist.")


    elif subcommand == 'save':
        args.actor.tallies_persist.append(tag)
        args.actor.sendMessage("Tally " + tag + " marked for saving.")

    elif subcommand == 'check' or subcommand == 'list':
        if len(tokens) > 2:
            tag = tokens[2]
            if tag in args.actor.tallies:
                args.actor.sendMessage("The value of tally " + tag + " is " + colorfy(str(args.actor.tallies[tag]), 'cyan') + ".")
                if tag in args.actor.tallies_persist:
                    args.actor.sendMessage("    This tally is marked to be saved.")
            else:
                args.actor.sendMessage("Tally " + tag + " does not exist.")
        else:
            keys = args.actor.tallies.keys()
            if len(keys) == 0:
                args.actor.sendMessage("You have no tallies.")
                return True

            args.actor.sendMessage("------TALLIES------")
            sorted(keys)
            perma_mark = "(" + colorfy("saved", "green") + ")"
            for key in keys:
                s = "    [" + colorfy(key, 'white') + ": " + colorfy(str(args.actor.tallies[key]), 'cyan') + "]"
                if key in args.actor.tallies_persist:
                    s = s + " " + perma_mark
                args.actor.sendMessage(s)

    elif subcommand == 'unsave':
        if tag in args.actor.tallies_persist:
            args.actor.tallies_persist.remove(tag)
            args.actor.sendMessage("Tally " + tag + " no longer marked for saving.")
        else:
            args.actor.sendMessage("Tally " + tag + " does not exist.")

    else:
        return False

    return True


def bag(args):
    """
    A player or DM may create a generic "bag" to keep track of items.
    Bags may be saved (persistent) or not (removed after logout).

    syntax: bag <subcommand> <tag>

    List of subcommands and syntax:

        Add/Remove:     bag add/remove <tag> <item>
        Check:          bag check [tag]
        Create:         bag create <tag> [initial]
        Empty:          bag empty <tag>
        Destroy:        bag destroy <tag>
        Share:          bag share <tag | all> [entity]
        Save/Unsave:    bag save/unsave <tag>



    You may also check the contents for all your bags by simply entering
    the command 'bags'.
    """

    if len(args.tokens) < 3:
        if len(args.tokens) == 1:
            if args.tokens[0] != 'bags':
                return False
        elif len(args.tokens) == 2:
            if args.tokens[1] != 'check':
                return False
        else:
            return False

    tokens = args.tokens

    # bags substitution
    if args.tokens[0] == 'bags':
        tokens = ['bag', 'check']

    subcommand = tokens[1]
    tag = ''
    if len(tokens) > 2:
        tag = tokens[2]

    if subcommand == 'create':
        if tag in args.actor.bags:
            args.actor.sendMessage("Bag " + tag + " already exists.")
        else:
            args.actor.bags[tag] = []
            args.actor.sendMessage("Bag " + tag + " created.")

    elif subcommand == 'destroy':
        if tag in args.actor.bags:
            del args.actor.bags[tag]
            args.actor.sendMessage("Bag " + tag + " destroyed.")
        else:
            args.actor.sendMessage("Bag " + tag + " does not exist.")

    elif subcommand == 'add' or subcommand == 'put':
        if len(tokens) < 4:
            args.actor.sendMessage("Usage: bag add <tag> <item>")
        elif tag in args.actor.bags:
            item = tokens[3]
            args.actor.bags[tag].append(item)
            args.actor.sendMessage("Item " + item + " added to bag " + tag + ".")
        else:
            args.actor.sendMessage("Bag " + tag + " does not exist.")

    elif subcommand == 'remove' or subcommand == 'take':
        if len(tokens) < 4:
            args.actor.sendMessage("Usage: bag remove <tag> <item>")
        elif tag in args.actor.bags:
            item = tokens[3]
            if item in args.actor.bags[tag]:
                args.actor.bags.remove(item)
                args.actor.sendMessage("Item " + item + " removed from bag " + tag + ".")
            else:
                args.actor.sendMessage("Bag " + tag + " does not contain item " + tokens[3] + ".")
        else:
            args.actor.sendMessage("Bag " + tag + " does not exist.")

    elif subcommand == 'empty':
        if tag in args.actor.bags:
            args.actor.bags[tag] = []
            args.actor.sendMessage("Bag " + tag + " emptied.")
        else:
            args.actor.sendMessage("Bag " + tag + " does not exist.")

    elif subcommand == 'share' or subcommand == 'show' or subcommand == 'display':
        keys = args.actor.bags.keys()
        if len(keys) == 0:
            args.actor.sendMessage("You have no bags.")
            return True
        sorted(keys)

        if tag == 'all':
            if len(tokens) > 3:
                if tokens[3] in args.actor.session:
                    target = args.actor.session.getEntity(tokens[3])
                    target.sendMessage(args.actor.name + " shares some bags with you: ")
                    args.actor.sendMessage("You share your bags with " + tokens[3] + ".")
                    for key in keys:
                        target.sendMessage("    " + key + ": " + str(args.actor.bags[key]))
            else:
                args.actor.sendMessage("You share your bags.")
                msg = args.actor.name + " shares some bags:"
                for key in keys:
                    msg += "\n    " + key + ": " + str(args.actor.bags[key])
                args.actor.session.broadcastExclude(msg, args.actor)

        elif tag in args.actor.bags:
            if len(tokens) > 3:
                if tokens[3] in args.actor.session:
                    target = args.actor.session.getEntity(tokens[3])
                    target.sendMessage(args.actor.name + " shares a bag (" + tag + ") with you: " + str(args.actor.bags[tag]))
                    args.actor.sendMessage("You share a bag (" + tag + ") with " + tokens[3] + ".")
            else:
                args.actor.session.broadcast(args.actor.name + " shares a bag (" + tag + "): " + str(args.actor.bags[tag]))
        else:
            args.actor.sendMessage("Bag " + tag + " does not exist.")

    elif subcommand == 'save':
        args.actor.bags_persist.append(tag)
        args.actor.sendMessage("Bag " + tag + " marked for saving.")

    elif subcommand == 'check' or subcommand == 'list':
        if len(tokens) > 2:
            tag = tokens[2]
            if tag in args.actor.bags:
                args.actor.sendMessage("The bag (" + tag + ") contains the following items: " + str(args.actor.bags[tag]))
            else:
                args.actor.sendMessage("Bag " + tag + " does not exist.")
        else:
            keys = args.actor.bags.keys()
            if len(keys) == 0:
                args.actor.sendMessage("You have no bags.")
                return True

            args.actor.sendMessage("------BAGS------")
            sorted(keys)
            perma_mark = "(" + colorfy("saved", "green") + ")"
            for key in keys:
                s = "    " + key
                if key in args.actor.bags_persist:
                    s = s + " " + perma_mark
                s = s + ": " + str(args.actor.bags[key])
                args.actor.sendMessage(s)

    elif subcommand == 'unsave':
        if tag in args.actor.bags_persist:
            args.actor.bags_persist.remove(tag)
            args.actor.sendMessage("Bag " + tag + " no longer marked for saving.")
        else:
            args.actor.sendMessage("Bag " + tag + " does not exist.")

    else:
        return False

    return True


@maskable
def initiative(args):
    """
    A DM can keep track of turn orderings by using the initiative command.
    The DM first sets the ordering by having everyone use the "init roll"
    subcommand, which will add them to the initiative tracker. A DM may also
    modify the ordering by hand, using the subcommands below.

    Once satisifed, the DM must "commit" the ordering to be tracked. A DM can
    always reset the ordering to the last commit by using "reset", or wipe
    the ordering and commit by using "wipe". After each turn, the DM should
    use the "tick" command.

    All commands are for DM only with the exception of the roll command.

    syntax: init <subcommand>

    List of subcommands and syntax:
        Roll:           init roll <sequence>
        Tick:           init tick
        Add:            init add <name> <value>
        Remove:         init remove <name>
        Promote/Demote: init promote/demote <name>
        Check:          init check
        Commit:         init commit
        List:           init display
        Reset:          init reset
        Wipe:           init wipe

    There are a few shorthand commands for your convenience. You may bump up
    or down the ordering of a player prior to commiting.
        init <name> ++
        init <name> --

    You may also check the ordering by simply using the command with no argument.

    A DM may use the command "tick" as a shorthand for "init tick".
    """
    tokens = args.tokens
    if len(args.tokens) == 1:
        if args.name == "tick":
            tokens = ['init', 'tick']
        else:
            tokens = ['init', 'check']
    elif len(args.tokens) == 2 and args.tokens[1] not in ('check', 'commit', 'display', 'reset', 'wipe', 'tick', 'roll'):
        return False
    elif len(args.tokens) >= 3:
        if args.tokens[2] == "++":
            tokens = ['init', 'promote', args.tokens[1]]
        elif args.tokens[2] == "--":
            tokens = ['init', 'demote', args.tokens[1]]
        elif args.tokens[1] not in ('roll', 'remove', 'promote', 'demote'):
            return False

    if not args.actor.dm and args.tokens[1] != 'roll':
        return False

    subcommand = tokens[1]
    tracker = args.actor.session.tracker
    if subcommand == 'roll':
        dice_str = "1d20"
        if len(tokens) > 3:
            dice_str = " ".join(tokens[2:])

        result = ""
        msg = ""
        try:
            result, msg = dice.parse(dice_str)
        except dice.DiceException as e:
            e_msg = 'Bad roll formatting! The clause ' + colorfy(str(e), "bred") + " is no good!"
            e_msg += '\nFor more help on roll syntax, check ' + colorfy("help roll", "green") + '.'
            args.actor.sendMessage(e_msg)
            return True
        pre = args.actor.name + " rolls for initative: " + colorfy(dice_str, "yellow")
        pre += ".\n    "
        msg = pre + msg + "    (total = " + colorfy(str(result), "yellow") + ")"
        tracker.add(args.actor.name, result)
        args.actor.session.broadcast(msg)

    elif subcommand == 'add':
        if len(tokens != 4):
            return False
        num = 1
        try:
            num = int(tokens[3])
        except ValueError:
            args.actor.sendMessage("The value must be a number.")
            return True
        tracker.add(tokens[2], num)
        args.actor.sendMessage("Added " + tokens[2].lower() + " to the tracker.")

    elif subcommand == 'remove':
        try:
            tracker.remove(tokens[2])
        except AttributeError:
            args.actor.sendMessage(tokens[2] + " is not being tracked.")
            return True
        args.actor.sendMessage("Removed " + tokens[2] + " from the tracker.")

    elif subcommand == 'promote':
        try:
            tracker.promote(tokens[2])
        except AttributeError:
            args.actor.sendMessage(tokens[2] + " is not being tracked.")
            return True
        args.actor.sendMessage("Promoted " + tokens[2] + ".")

    elif subcommand == 'demote':
        try:
            tracker.demote(tokens[2])
        except AttributeError:
            args.actor.sendMessage(tokens[2] + " is not being tracked.")
            return True
        args.actor.sendMessage("Demoted " + tokens[2] + ".")

    elif subcommand == 'check':
        queue = tracker.queue
        ordering = tracker.order
        s = "Queue: " + ", ".join(x[0] for x in queue) + "\n"
        s += "Ordering: " +  ", ".join(ordering)
        args.actor.sendMessage(str(s));

    elif subcommand == 'commit':
        tracker.commit()
        args.actor.session.broadcast(colorfy("The DM has set the turn order.", "bred"))
        args.actor.session.broadcast(str(tracker))
        args.actor.session.broadcast(colorfy("It is now " + tracker.peek() + "'s turn.", "bred"))

    elif subcommand == 'display':
        if len(tracker.order) == 0:
            args.actor.sendMessage("No ordering has been committed.")
            return True
        args.actor.session.broadcast(str(tracker))
        args.actor.session.broadcast(colorfy("It is now " + tracker.peek() + "'s turn.", "bred"))

    elif subcommand == 'reset':
        tracker.reset()
        args.actor.session.broadcast("Tracker order reset. Recommit when ready.")

    elif subcommand == 'tick':
        if (tracker.tick()):
            args.actor.session.broadcast(str(tracker))
            args.actor.session.broadcast(colorfy("It is now " + tracker.peek() + "'s turn.", "bred"))
        else:
            args.actor.sendMessage("The tracker is not committed.")

    elif subcommand == 'wipe':
        tracker.wipe()
        args.actor.session.broadcast("Tracker wiped.")

    else:
        return False

    return True


@spectatorable
def save(args):
    """
    Saves all persistent stuff.

    Syntax: save
    """
    persist.saveEntity(args.actor)
    args.actor.sendMessage("Profile saved.")
    return True


def aspect(args):
    """
    DMs can set aspects on players. Anyone can check aspects.

    syntax: aspect <subcommand>

    List of subcommands and syntax:

        Add/Remove:     aspect add/remove <player> <aspect>
        Check:          aspect check <player>


    You may also check all the aspects for all players by typing "aspects".
    """

    if len(args.tokens) < 4:
        if len(args.tokens) == 1:
            if args.tokens[0] != 'aspects':
                return False
        elif len(args.tokens) == 3:
            if args.tokens[1] != 'check':
                return False
        else:
            return False

    tokens = args.tokens

    # bags substitution
    if args.tokens[0] == 'aspects':
        tokens = ['aspect', 'check', 'all']

    subcommand = tokens[1]
    if subcommand not in ('check', 'add', 'remove'):
        return False

    target = args.actor.session.getEntity(tokens[2])
    if subcommand == 'check':
        if not target and tokens[2] == 'all':
            s = ""
            for e in args.actor.session:
                s += e.name + " has the following aspects:\n    " + "\n    ".join(e.aspects) + "\n\n"
            args.actor.sendMessage(s)
        elif target:
            args.actor.sendMessage(target.name + " has the following aspects:\n    " + "\n    ".join(target.aspects))
        else:
            return False
            
    elif subcommand in ('add', 'remove'):
        aspect = " ".join(tokens[3:]).strip()
        if not target or aspect == '':
            return False

        index = -1
        for i in range(len(target.aspects)):
            a = target.aspects[i]
            if a.strip.lower() == aspect.lower():
                index = i

        if subcommand == 'add' and index == -1:
            target.aspects.append(aspect);
            args.actor.session.broadcast(target.name + " " + colorfy("acquires", "bgreen") + " the aspect: " + colorfy(aspect, "yellow") + ".")
        elif subcommand == 'remove' and index != -1:
            args.actor.session.broadcast(target.name + " " + colorfy("loses", "bred") + " the aspect: " + colorfy(aspect, "yellow") + ".")
            del target.aspects[index]
        else:
            return False
    return True


@block
def description(args):
    """
    A player may create a description for his or her character.

    syntax: description | desc

    You may clear your description by using the following command:
        desc clear

    You may check your own description by using the "examine" command.
    """
    if len(args.tokens) > 1 and args.tokens[1] in ("clear", "erase", "clean"):
        args.actor.facade = ""
        persist.saveEntity(args.actor)
        args.actor.sendMessage("Description erased.")
        return True

    args.actor.sendMessage("Opening the Mushy editor.")
    editor_instance = editor.Editor(args.actor)
    editor_instance.launch(callback=_description, callback_args=args)
    return True


def _description(args, text):
    args.actor.facade = text
    persist.saveEntity(args.actor)
    args.actor.sendMessage("Profile saved.")


@block
def docshare(args):
    """
    This is a command for sharing large text documents with the group.

    It opens up the in-server editor, and sends the text to hastebin, 
    a really nice minimalist pastebin alternative. The link is then broadcast
    to all users for viewing.

    This is good for larger documents, because it can be shared with users 
    without spamming their client.

    Syntax: docshare [user1] [user2] ...

    The DM may specify users to share the document privately
    """
    args.actor.sendMessage("Opening the Mushy editor.")
    editor_instance = editor.Editor(args.actor)
    editor_instance.launch(callback=_docshare, callback_args=args)
    return True


def _docshare(args, text):
    """
    Callback from hastepaste.
    """
    try:
        req = urllib2.Request("http://hastebin.com/documents", text)
        response = urllib2.urlopen(req)
        d = json.loads(response.read())
        link = "http://hastebin.com/raw/" + d['key']

        sent = []
        if len(args.tokens[1:]) > 0:
            names = args.tokens[1:]
            for i in range(len(names)):
                names[i] = names[i].lower()

            for name in names:
                target = args.actor.session.getEntity(name)
                target.sendMessage(colorfy("DM " + args.actor.name + " shares a document with you: " + link, "red"))
                sent.append(target.name)
            args.actor.sendMessage(colorfy("You share a document with: " + str(sent), "red"))
        else:
            args.actor.session.broadcast(colorfy("DM " + args.actor.name + " shares a document with the session: " + link, "red"))
    except urllib2.HTTPError:
        print "Server: Exception occurred while uploading to hastebin."
        args.actor.sendMessage("There was an issue with uploading your document to hastebin.")
        args.actor.sendMessage("Chances are that either hastebin is down, or your document was too large.")
