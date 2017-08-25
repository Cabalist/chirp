#!/usr/bin/env python
# coding=utf-8
#
# Copyright 2008 Dan Smith <dsmith@danplanet.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import print_function
import gtk
import sys

from csvdump import csvapp

if hasattr(sys, "frozen"):
    log = open("debug.log", "w", 0)
    sys.stderr = log
    sys.stdout = log
    print("Log initialized")

a = csvapp.CsvDumpApp()
a.run()
