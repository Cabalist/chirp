#!/usr/bin/python
#
# Copyright 2011 Rick Farina <sidhayn@gmail.com>
#     based on modification of Dan Smith's original work
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from chirp import chirp_common, yaesu_clone, util
from chirp import bitwise

#interesting offsets which may be checksums needed later
#0x0393 checksum1?
#0x0453 checksum1a?
#0x0409 checksum2?
#0x04C9 checksum2a?

mem_format = """
#seekto 0x7F4A;
u8 checksum;

#seekto 0x20CA;
struct {
  u8 even_pskip:1,
     even_skip:1,
     even_valid:1,
     even_masked:1,
     odd_pskip:1,
     odd_skip:1,
     odd_valid:1,
     odd_masked:1;
} flags[900];

#seekto 0x244A;
struct {
  u8   unknown1;
  u8   mode:2,
       duplex:2,
       tune_step:4;
  bbcd freq[3];
  u8   power:2,
       unknown2:4,
       tmode:2;
  u8   name[6];
  bbcd offset[3];
  u8   unknown3:2,
       tone:6;
  u8   unknown4:1,
       dcs:7;
  u8   unknown5;
  u8   unknown6;
  u8   unknown7:4,
       automode:1,
       unknown8:3;
} memory[900];
"""

#power is 11 for 1W and 00 for 100mW
#fix auto mode setting and auto step setting

DUPLEX = ["", "-", "+", "split"]
MODES  = ["FM", "AM", "WFM", "FM"] # last is auto
TMODES = ["", "Tone", "TSQL", "DTCS"]

#still need to verify 9 is correct, and add auto: look at byte 1 and 20
STEPS = [ 5.0, 9, 10.0, 12.5, 15.0, 20.0, 25.0, 50.0, 100.0 ]
#STEPS = list(chirp_common.TUNING_STEPS)
#STEPS.remove(6.25)
#STEPS.remove(30.0)
#STEPS.append(100.0)
#STEPS.append(9.0) #this fails because 9 is out of order in the list

#Empty char should be 0xFF but right now we are coding in a space
CHARSET = list("0123456789" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ " + "+-/?[](){}??_?????????????*??,'|????\?????" + "?"*59)

class VX3Radio(yaesu_clone.YaesuCloneModeRadio):
    BAUD_RATE = 19200
    VENDOR = "Yaesu"
    MODEL = "VX-3"

    # 41 48 30 32 38
    _model = "AH028"
    _memsize = 32587
    _block_lengths = [ 10, 32577 ]
    #right now this reads in 45 seconds and writes in 123 seconds
    #attempts to speed it up appear unstable, more testing required
    _block_size = 8

    def _update_checksum(self):
        cs = 0
        for i in range(0x0000, 0x7F4A):
            cs += ord(self._mmap[i])
        cs %= 256
        print "Checksum3 old=%02x new=%02x" % (self._memobj.checksum, cs)
        self._memobj.checksum = cs

    def process_mmap(self):
        self._memobj = bitwise.parse(mem_format, self._mmap)

    def get_features(self):
        rf = chirp_common.RadioFeatures()
        rf.has_bank = False
        rf.has_dtcs_polarity = False
        rf.valid_modes = list(set(MODES))
        rf.valid_tmodes = list(TMODES)
        rf.valid_duplexes = list(DUPLEX)
        rf.valid_tuning_steps = list(STEPS)
        rf.valid_bands = [(0.5, 999.0)]
        rf.valid_skips = ["", "S", "P"]
        rf.memory_bounds = (1, 900)
        rf.can_odd_split = True
        rf.has_ctone = False
        return rf

    def get_raw_memory(self, number):
        return self._memobj.memory[number].get_raw()

    def get_memory(self, number):
        _mem = self._memobj.memory[number-1]
        _flag = self._memobj.flags[(number-1)/2]

        nibble = ((number-1) % 2) and "even" or "odd"
        used = _flag["%s_masked" % nibble] and _flag["%s_valid" % nibble]
        pskip = _flag["%s_pskip" % nibble]
        skip = _flag["%s_skip" % nibble]

        mem = chirp_common.Memory()
        mem.number = number
        if not used:
            mem.empty = True
            return mem

        mem.freq = int(_mem.freq) / 1000.0
        mem.offset = int(_mem.offset) / 1000.0
        mem.rtone = mem.ctone = chirp_common.TONES[_mem.tone]
        mem.tmode = TMODES[_mem.tmode]
        mem.duplex = DUPLEX[_mem.duplex]
        mem.mode = MODES[_mem.mode]
        mem.dtcs = chirp_common.DTCS_CODES[_mem.dcs]
        mem.tuning_step = STEPS[_mem.tune_step]
        mem.skip = pskip and "P" or skip and "S" or ""

        for i in _mem.name:
            if i == 0xFF:
                break
            mem.name += CHARSET[i & 0x7F]
        return mem

    def _wipe_memory(self, mem):
        mem.set_raw("\x00" * (mem.size() / 8))
        mem.power = 0b11 #this sets power to full by default
        #the following settings are set to match the defaults
        #on the radio, some of these fields are unknown
        mem.name = [0xFF for i in range(0, 6)]
        mem.unknown5 = 0x0D #not sure what this is
        mem.unknown7 = 0b0001 #this likely is part of autostep
        mem.automode = 0b1 #autoselect mode


    def set_memory(self, mem):
        _mem = self._memobj.memory[mem.number-1]
        _flag = self._memobj.flags[(mem.number-1)/2]

        nibble = ((mem.number-1) % 2) and "even" or "odd"
      
        was_valid = int(_flag["%s_valid" % nibble])

        _flag["%s_masked" % nibble] = not mem.empty
        _flag["%s_valid" % nibble] = not mem.empty
        if mem.empty:
            return

        if not was_valid:
            self._wipe_memory(_mem)

        _mem.freq = int(mem.freq * 1000)
        _mem.offset = int(mem.offset * 1000)
        _mem.tone = chirp_common.TONES.index(mem.rtone)
        _mem.tmode = TMODES.index(mem.tmode)
        _mem.duplex = DUPLEX.index(mem.duplex)
        _mem.mode = MODES.index(mem.mode)
        _mem.dcs = chirp_common.DTCS_CODES.index(mem.dtcs)
        _mem.tune_step = STEPS.index(mem.tuning_step)

        _flag["%s_pskip" % nibble] = mem.skip == "P"
        _flag["%s_skip" % nibble] = mem.skip == "S"

        for i in range(0, 6):
            _mem.name[i] = CHARSET.index(mem.name.ljust(6)[i])
        if mem.name.strip(): _mem.name[0] |= 0x80
      
    def get_banks(self):
        return []

    def filter_name(self, name):
        return chirp_common.name6(name, just_upper=True)