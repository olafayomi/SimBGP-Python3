#!/usr/bin/env python


# Copyright (c) 2020, WAND Network Research Group
#                     Department of Computer Science
#                     University of Waikato
#                     Hamilton
#                     New Zealand
#
# Author Dimeji Fayomi (oof1@students.waikato.ac.nz)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330,
# Boston,  MA 02111-1307  USA

import os
import sys
import re


def readGMLFile(filename):
    with open(filename) as f:
        content = f.read()
    return content


def printContent(content):
    print(content)


def searchAndReplace(content):
    regex = re.compile(r'Longitude\s([0-9.]*)\n.*Internal.*\n.*Latitude\s([0-9.]*)', re.MULTILINE)
    result = re.sub(r'Longitude\s(-?[0-9.]*)\n.*Internal.*\n.*Latitude\s(-?[0-9.]*)',
                    'graphics [\n      center   [\n                 x \\1'
                    '\n                 y \\2\n      ]\n    ]',
                    content, flags=re.MULTILINE)
    result = re.sub(r'LinkSpeed\s\"([0-9.]*)\"\n.*LinkNote\s\"\s([a-z]*)\/s\"\n.*LinkLabel\s\"([0-9.]*)\s\b(Mbit|Gbit)\b\/s\"\n.*LinkSpeedUnits\s\"([A-Z])\"\n.*LinkSpeedRaw\s([0-9.]*)',
                    'simplex 1\n    bandwidth \\1\\5', result,
                    flags=re.MULTILINE | re.VERBOSE)
    return result

def writeIGenGML(result, filename):
    with open(filename, "w") as f:
        f.write(result)




if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: ProcessGML.py RawGMLFile ProcessedGMLFile \n")
        sys.exit(-1)

    content = readGMLFile(sys.argv[1])
    match = searchAndReplace(content)
    writeIGenGML(match, sys.argv[2])
    #printContent(match)
