import commands
import namedtuple

CommandArgs = namedtuple.namedtuple('CommandArgs', 'name tokens full actor')

commandFunctions = {}
commandFunctions["configure"] = commands.configure
commandFunctions["config"] = commands.configure
commandFunctions["alias"] = commands.alias
commandFunctions["unalias"] = commands.alias
commandFunctions["aliases"] = commands.alias
commandFunctions["say"] = commands.say
commandFunctions["whisper"] = commands.whisper
commandFunctions["yell"] = commands.yell
commandFunctions["shout"] = commands.yell
commandFunctions["scream"] = commands.yell
commandFunctions["language"] = commands.language
commandFunctions["languages"] = commands.language
commandFunctions["logout"] = commands.logout
commandFunctions["help"] = commands.help
commandFunctions["who"] = commands.who
commandFunctions["pm"] = commands.pm
commandFunctions["emote"] = commands.emote
commandFunctions["ooc"] = commands.ooc
commandFunctions["roll"] = commands.roll
commandFunctions["hroll"] = commands.roll
commandFunctions["droll"] = commands.roll
commandFunctions["display"] = commands.display
commandFunctions["mask"] = commands.mask
commandFunctions["unmask"] = commands.mask
commandFunctions["status"] = commands.status
commandFunctions["glance"] = commands.glance
commandFunctions["colors"] = commands.colors
commandFunctions["paint"] = commands.paint
commandFunctions["sculpt"] = commands.sculpt
commandFunctions["brush"] = commands.brush
commandFunctions["wipe"] = commands.wipe
commandFunctions["look"] = commands.look
commandFunctions["tally"] = commands.tally
commandFunctions["tallies"] = commands.tally
commandFunctions["bag"] = commands.bag
commandFunctions["bags"] = commands.bag
commandFunctions["save"] = commands.save
commandFunctions["desc"] = commands.description
commandFunctions["description"] = commands.description
commandFunctions["exa"] = commands.examine
commandFunctions["examine"] = commands.examine
commandFunctions["hastepaste"] = commands.docshare
commandFunctions["docshare"] = commands.docshare
commandFunctions["zap"] = commands.zap
commandFunctions["init"] = commands.initiative
commandFunctions["initiative"] = commands.initiative
commandFunctions["tick"] = commands.initiative
commandFunctions["fudge"] = commands.fudge



def shorthandHandler(args):
    if len(args.tokens) < 1:
        return args

    if len(args.full) < 2:
        return args

    if args.name[0] in (';'):
        new_name = "emote"
        new_tokens = ["emote", ";", args.tokens[0][1:]] + args.tokens[1:]
        new_full = "emote ; " + args.full[1:]

        newargs = CommandArgs(name=new_name, tokens=new_tokens, full=new_full, actor=args.actor)
        return newargs

    elif args.name[0] == "'":
        new_name = "say"
        new_tokens = ["say", args.tokens[0][1:]] + args.tokens[1:]
        new_full = "say " + args.full[1:]

        newargs = CommandArgs(name=new_name, tokens=new_tokens, full=new_full, actor=args.actor)
        return newargs

    elif args.name[0] == "*":
        new_name = "ooc"
        new_tokens = ["ooc", args.tokens[0][1:]] + args.tokens[1:]
        new_full = "ooc " + args.full[1:]

        newargs = CommandArgs(name=new_name, tokens=new_tokens, full=new_full, actor=args.actor)
        return newargs

    elif args.name[0] == "#":
        new_name = "roll"
        new_tokens = ["roll", '1d' + args.tokens[0][1:]]
        new_full = "roll 1d" + args.tokens[0][1:]

        newargs = CommandArgs(name=new_name, tokens=new_tokens, full=new_full, actor=args.actor)
        return newargs

    elif args.name[0] == "$":
        new_name = "mask"
        new_tokens = ["mask", args.tokens[0][1:]] + args.tokens[1:]
        new_full = "mask " + args.full[1:]

        newargs = CommandArgs(name=new_name, tokens=new_tokens, full=new_full, actor=args.actor)
        return newargs

    elif "@" in args.name:
        new_name = "display"
        new_tokens = ["display"] + args.tokens
        new_full = "display " + args.full

        newargs = CommandArgs(name=new_name, tokens=new_tokens, full=new_full, actor=args.actor)
        return newargs

    return args
