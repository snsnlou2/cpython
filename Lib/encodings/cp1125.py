
' Python Character Mapping Codec for CP1125\n\n'
import codecs

class Codec(codecs.Codec):

    def encode(self, input, errors='strict'):
        return codecs.charmap_encode(input, errors, encoding_map)

    def decode(self, input, errors='strict'):
        return codecs.charmap_decode(input, errors, decoding_table)

class IncrementalEncoder(codecs.IncrementalEncoder):

    def encode(self, input, final=False):
        return codecs.charmap_encode(input, self.errors, encoding_map)[0]

class IncrementalDecoder(codecs.IncrementalDecoder):

    def decode(self, input, final=False):
        return codecs.charmap_decode(input, self.errors, decoding_table)[0]

class StreamWriter(Codec, codecs.StreamWriter):
    pass

class StreamReader(Codec, codecs.StreamReader):
    pass

def getregentry():
    return codecs.CodecInfo(name='cp1125', encode=Codec().encode, decode=Codec().decode, incrementalencoder=IncrementalEncoder, incrementaldecoder=IncrementalDecoder, streamreader=StreamReader, streamwriter=StreamWriter)
decoding_map = codecs.make_identity_dict(range(256))
decoding_map.update({128: 1040, 129: 1041, 130: 1042, 131: 1043, 132: 1044, 133: 1045, 134: 1046, 135: 1047, 136: 1048, 137: 1049, 138: 1050, 139: 1051, 140: 1052, 141: 1053, 142: 1054, 143: 1055, 144: 1056, 145: 1057, 146: 1058, 147: 1059, 148: 1060, 149: 1061, 150: 1062, 151: 1063, 152: 1064, 153: 1065, 154: 1066, 155: 1067, 156: 1068, 157: 1069, 158: 1070, 159: 1071, 160: 1072, 161: 1073, 162: 1074, 163: 1075, 164: 1076, 165: 1077, 166: 1078, 167: 1079, 168: 1080, 169: 1081, 170: 1082, 171: 1083, 172: 1084, 173: 1085, 174: 1086, 175: 1087, 176: 9617, 177: 9618, 178: 9619, 179: 9474, 180: 9508, 181: 9569, 182: 9570, 183: 9558, 184: 9557, 185: 9571, 186: 9553, 187: 9559, 188: 9565, 189: 9564, 190: 9563, 191: 9488, 192: 9492, 193: 9524, 194: 9516, 195: 9500, 196: 9472, 197: 9532, 198: 9566, 199: 9567, 200: 9562, 201: 9556, 202: 9577, 203: 9574, 204: 9568, 205: 9552, 206: 9580, 207: 9575, 208: 9576, 209: 9572, 210: 9573, 211: 9561, 212: 9560, 213: 9554, 214: 9555, 215: 9579, 216: 9578, 217: 9496, 218: 9484, 219: 9608, 220: 9604, 221: 9612, 222: 9616, 223: 9600, 224: 1088, 225: 1089, 226: 1090, 227: 1091, 228: 1092, 229: 1093, 230: 1094, 231: 1095, 232: 1096, 233: 1097, 234: 1098, 235: 1099, 236: 1100, 237: 1101, 238: 1102, 239: 1103, 240: 1025, 241: 1105, 242: 1168, 243: 1169, 244: 1028, 245: 1108, 246: 1030, 247: 1110, 248: 1031, 249: 1111, 250: 183, 251: 8730, 252: 8470, 253: 164, 254: 9632, 255: 160})
decoding_table = '\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~\x7fАБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдежзийклмноп░▒▓│┤╡╢╖╕╣║╗╝╜╛┐└┴┬├─┼╞╟╚╔╩╦╠═╬╧╨╤╥╙╘╒╓╫╪┘┌█▄▌▐▀рстуфхцчшщъыьэюяЁёҐґЄєІіЇї·√№¤■\xa0'
encoding_map = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9, 10: 10, 11: 11, 12: 12, 13: 13, 14: 14, 15: 15, 16: 16, 17: 17, 18: 18, 19: 19, 20: 20, 21: 21, 22: 22, 23: 23, 24: 24, 25: 25, 26: 26, 27: 27, 28: 28, 29: 29, 30: 30, 31: 31, 32: 32, 33: 33, 34: 34, 35: 35, 36: 36, 37: 37, 38: 38, 39: 39, 40: 40, 41: 41, 42: 42, 43: 43, 44: 44, 45: 45, 46: 46, 47: 47, 48: 48, 49: 49, 50: 50, 51: 51, 52: 52, 53: 53, 54: 54, 55: 55, 56: 56, 57: 57, 58: 58, 59: 59, 60: 60, 61: 61, 62: 62, 63: 63, 64: 64, 65: 65, 66: 66, 67: 67, 68: 68, 69: 69, 70: 70, 71: 71, 72: 72, 73: 73, 74: 74, 75: 75, 76: 76, 77: 77, 78: 78, 79: 79, 80: 80, 81: 81, 82: 82, 83: 83, 84: 84, 85: 85, 86: 86, 87: 87, 88: 88, 89: 89, 90: 90, 91: 91, 92: 92, 93: 93, 94: 94, 95: 95, 96: 96, 97: 97, 98: 98, 99: 99, 100: 100, 101: 101, 102: 102, 103: 103, 104: 104, 105: 105, 106: 106, 107: 107, 108: 108, 109: 109, 110: 110, 111: 111, 112: 112, 113: 113, 114: 114, 115: 115, 116: 116, 117: 117, 118: 118, 119: 119, 120: 120, 121: 121, 122: 122, 123: 123, 124: 124, 125: 125, 126: 126, 127: 127, 160: 255, 164: 253, 183: 250, 1025: 240, 1028: 244, 1030: 246, 1031: 248, 1040: 128, 1041: 129, 1042: 130, 1043: 131, 1044: 132, 1045: 133, 1046: 134, 1047: 135, 1048: 136, 1049: 137, 1050: 138, 1051: 139, 1052: 140, 1053: 141, 1054: 142, 1055: 143, 1056: 144, 1057: 145, 1058: 146, 1059: 147, 1060: 148, 1061: 149, 1062: 150, 1063: 151, 1064: 152, 1065: 153, 1066: 154, 1067: 155, 1068: 156, 1069: 157, 1070: 158, 1071: 159, 1072: 160, 1073: 161, 1074: 162, 1075: 163, 1076: 164, 1077: 165, 1078: 166, 1079: 167, 1080: 168, 1081: 169, 1082: 170, 1083: 171, 1084: 172, 1085: 173, 1086: 174, 1087: 175, 1088: 224, 1089: 225, 1090: 226, 1091: 227, 1092: 228, 1093: 229, 1094: 230, 1095: 231, 1096: 232, 1097: 233, 1098: 234, 1099: 235, 1100: 236, 1101: 237, 1102: 238, 1103: 239, 1105: 241, 1108: 245, 1110: 247, 1111: 249, 1168: 242, 1169: 243, 8470: 252, 8730: 251, 9472: 196, 9474: 179, 9484: 218, 9488: 191, 9492: 192, 9496: 217, 9500: 195, 9508: 180, 9516: 194, 9524: 193, 9532: 197, 9552: 205, 9553: 186, 9554: 213, 9555: 214, 9556: 201, 9557: 184, 9558: 183, 9559: 187, 9560: 212, 9561: 211, 9562: 200, 9563: 190, 9564: 189, 9565: 188, 9566: 198, 9567: 199, 9568: 204, 9569: 181, 9570: 182, 9571: 185, 9572: 209, 9573: 210, 9574: 203, 9575: 207, 9576: 208, 9577: 202, 9578: 216, 9579: 215, 9580: 206, 9600: 223, 9604: 220, 9608: 219, 9612: 221, 9616: 222, 9617: 176, 9618: 177, 9619: 178, 9632: 254}
