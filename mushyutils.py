import textwrap, re


swatch = {
    'black': '0;30', 'bright gray': '0;37',
    'blue': '0;34', 'white': '1;37',
    'green': '0;32', 'bright blue': '1;34',
    'cyan': '0;36', 'bright green': '1;32',
    'red': '0;31', 'bright cyan': '1;36',
    'purple': '0;35', 'bright red': '1;31',
    'yellow': '0;33', 'bright purple': '1;35',
    'dark gray': '1;30', 'bright yellow': '1;33',
    'dgray': '1;30', 'bgray': '0;37', 'bblue': '1;34',
    'bgreen': '1;32', 'bcyan': '1;36', 'bred': '1;31',
    'bpurple': '1;35', 'byellow': '1;33', 'default': '0',
    'normal': '0'
}


def colorfy(text, color):
    color = color.lower()
    key = "normal"
    if color in swatch:
        key = color
    text = text.replace("[0m", "[" + swatch[key] + "m")
    return "\033[" + swatch[key] + "m" + text + "\033[0m"


def wrap(text, cols=79):
    t = textwrap.TextWrapper()
    t.break_long_words = True
    t.subsequent_index = ""
    t.width = cols
    lines = re.split("(\n)", text)
    wrapped_lines = []
    for line in lines:
        toadd = t.wrap(line)
        wrapped_lines += toadd
    s = "\n".join(wrapped_lines)
    return s