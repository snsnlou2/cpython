
"Color Database.\n\nThis file contains one class, called ColorDB, and several utility functions.\nThe class must be instantiated by the get_colordb() function in this file,\npassing it a filename to read a database out of.\n\nThe get_colordb() function will try to examine the file to figure out what the\nformat of the file is.  If it can't figure out the file format, or it has\ntrouble reading the file, None is returned.  You can pass get_colordb() an\noptional filetype argument.\n\nSupporte file types are:\n\n    X_RGB_TXT -- X Consortium rgb.txt format files.  Three columns of numbers\n                 from 0 .. 255 separated by whitespace.  Arbitrary trailing\n                 columns used as the color name.\n\nThe utility functions are useful for converting between the various expected\ncolor formats, and for calculating other color values.\n\n"
import sys
import re
from types import *

class BadColor(Exception):
    pass
DEFAULT_DB = None
SPACE = ' '
COMMASPACE = ', '

class ColorDB():

    def __init__(self, fp):
        lineno = 2
        self.__name = fp.name
        self.__byrgb = {}
        self.__byname = {}
        self.__allnames = None
        for line in fp:
            mo = self._re.match(line)
            if (not mo):
                print('Error in', fp.name, ' line', lineno, file=sys.stderr)
                lineno += 1
                continue
            (red, green, blue) = self._extractrgb(mo)
            name = self._extractname(mo)
            keyname = name.lower()
            key = (red, green, blue)
            (foundname, aliases) = self.__byrgb.get(key, (name, []))
            if ((foundname != name) and (foundname not in aliases)):
                aliases.append(name)
            self.__byrgb[key] = (foundname, aliases)
            self.__byname[keyname] = key
            lineno = (lineno + 1)

    def _extractrgb(self, mo):
        return [int(x) for x in mo.group('red', 'green', 'blue')]

    def _extractname(self, mo):
        return mo.group('name')

    def filename(self):
        return self.__name

    def find_byrgb(self, rgbtuple):
        'Return name for rgbtuple'
        try:
            return self.__byrgb[rgbtuple]
        except KeyError:
            raise BadColor(rgbtuple) from None

    def find_byname(self, name):
        'Return (red, green, blue) for name'
        name = name.lower()
        try:
            return self.__byname[name]
        except KeyError:
            raise BadColor(name) from None

    def nearest(self, red, green, blue):
        'Return the name of color nearest (red, green, blue)'
        nearest = (- 1)
        nearest_name = ''
        for (name, aliases) in self.__byrgb.values():
            (r, g, b) = self.__byname[name.lower()]
            rdelta = (red - r)
            gdelta = (green - g)
            bdelta = (blue - b)
            distance = (((rdelta * rdelta) + (gdelta * gdelta)) + (bdelta * bdelta))
            if ((nearest == (- 1)) or (distance < nearest)):
                nearest = distance
                nearest_name = name
        return nearest_name

    def unique_names(self):
        if (not self.__allnames):
            self.__allnames = []
            for (name, aliases) in self.__byrgb.values():
                self.__allnames.append(name)
            self.__allnames.sort(key=str.lower)
        return self.__allnames

    def aliases_of(self, red, green, blue):
        try:
            (name, aliases) = self.__byrgb[(red, green, blue)]
        except KeyError:
            raise BadColor((red, green, blue)) from None
        return ([name] + aliases)

class RGBColorDB(ColorDB):
    _re = re.compile('\\s*(?P<red>\\d+)\\s+(?P<green>\\d+)\\s+(?P<blue>\\d+)\\s+(?P<name>.*)')

class HTML40DB(ColorDB):
    _re = re.compile('(?P<name>\\S+)\\s+(?P<hexrgb>#[0-9a-fA-F]{6})')

    def _extractrgb(self, mo):
        return rrggbb_to_triplet(mo.group('hexrgb'))

class LightlinkDB(HTML40DB):
    _re = re.compile('(?P<name>(.+))\\s+(?P<hexrgb>#[0-9a-fA-F]{6})')

    def _extractname(self, mo):
        return mo.group('name').strip()

class WebsafeDB(ColorDB):
    _re = re.compile('(?P<hexrgb>#[0-9a-fA-F]{6})')

    def _extractrgb(self, mo):
        return rrggbb_to_triplet(mo.group('hexrgb'))

    def _extractname(self, mo):
        return mo.group('hexrgb').upper()
FILETYPES = [(re.compile('Xorg'), RGBColorDB), (re.compile('XConsortium'), RGBColorDB), (re.compile('HTML'), HTML40DB), (re.compile('lightlink'), LightlinkDB), (re.compile('Websafe'), WebsafeDB)]

def get_colordb(file, filetype=None):
    colordb = None
    fp = open(file)
    try:
        line = fp.readline()
        if (not line):
            return None
        if (filetype is None):
            filetypes = FILETYPES
        else:
            filetypes = [filetype]
        for (typere, class_) in filetypes:
            mo = typere.search(line)
            if mo:
                break
        else:
            return None
        colordb = class_(fp)
    finally:
        fp.close()
    global DEFAULT_DB
    DEFAULT_DB = colordb
    return colordb
_namedict = {}

def rrggbb_to_triplet(color):
    'Converts a #rrggbb color to the tuple (red, green, blue).'
    rgbtuple = _namedict.get(color)
    if (rgbtuple is None):
        if (color[0] != '#'):
            raise BadColor(color)
        red = color[1:3]
        green = color[3:5]
        blue = color[5:7]
        rgbtuple = (int(red, 16), int(green, 16), int(blue, 16))
        _namedict[color] = rgbtuple
    return rgbtuple
_tripdict = {}

def triplet_to_rrggbb(rgbtuple):
    'Converts a (red, green, blue) tuple to #rrggbb.'
    global _tripdict
    hexname = _tripdict.get(rgbtuple)
    if (hexname is None):
        hexname = ('#%02x%02x%02x' % rgbtuple)
        _tripdict[rgbtuple] = hexname
    return hexname

def triplet_to_fractional_rgb(rgbtuple):
    return [(x / 256) for x in rgbtuple]

def triplet_to_brightness(rgbtuple):
    r = 0.299
    g = 0.587
    b = 0.114
    return (((r * rgbtuple[0]) + (g * rgbtuple[1])) + (b * rgbtuple[2]))
if (__name__ == '__main__'):
    colordb = get_colordb('/usr/openwin/lib/rgb.txt')
    if (not colordb):
        print('No parseable color database found')
        sys.exit(1)
    target = 'navy'
    (red, green, blue) = rgbtuple = colordb.find_byname(target)
    print(target, ':', red, green, blue, triplet_to_rrggbb(rgbtuple))
    (name, aliases) = colordb.find_byrgb(rgbtuple)
    print('name:', name, 'aliases:', COMMASPACE.join(aliases))
    (r, g, b) = (1, 1, 128)
    (r, g, b) = (145, 238, 144)
    (r, g, b) = (255, 251, 250)
    print('finding nearest to', target, '...')
    import time
    t0 = time.time()
    nearest = colordb.nearest(r, g, b)
    t1 = time.time()
    print('found nearest color', nearest, 'in', (t1 - t0), 'seconds')
    for n in colordb.unique_names():
        (r, g, b) = colordb.find_byname(n)
        aliases = colordb.aliases_of(r, g, b)
        print(('%20s: (%3d/%3d/%3d) == %s' % (n, r, g, b, SPACE.join(aliases[1:]))))
