#!/usr/bin/env python
# coding=utf-8

from __future__ import print_function

import polib
from string import Formatter
import glob

filelist = glob.glob("*.po")
pos = {filename: polib.pofile(filename) for filename in filelist}

formatter = Formatter()

for name, po in pos.iteritems():
    print("Testing {}".format(name))
    for entry in po:
        if len(entry.msgstr) > 0:
            try:
                ids = [field_name
                       for literal_text, field_name, format_spec, conversion
                       in formatter.parse(entry.msgid)]
                tids = [field_name
                        for literal_text, field_name, format_spec, conversion
                        in formatter.parse(entry.msgstr)]
            except Exception as e:
                print("Got exception! {} for entry {}".format(e, entry.msgid))
            else:
                if tids is not None:
                    missing = [name for name in tids
                               if name is not None and name not in ids]
                    if len(missing) > 0:
                        print("Missing parameters {} in translation of {}".format(missing, entry.msgid))
