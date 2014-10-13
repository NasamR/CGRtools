#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  rdfrw.py
#
#  Copyright 2014 Ramil Nugmanov <stsouko@live.ru>
#  This file is part of condenser.
#
#  condenser is free software; you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#

import numpy


def main():
    print "This file is part of condenser."
    return 0


class SDFwrite(object):
    def __init__(self, fileTowrite, coordtype): #инициализация
        self.__coordtype = coordtype
        self.__fileTowrite = open(fileTowrite, 'w')

    def close(self):
        self.__fileTowrite.close()

    def writedata(self, data):
        self.__fileTowrite.write(
            "\n  SDF generated by condenser. (c) Ramil I. Nugmanov\n\n%3s%3s  0  0  0  0            999 V2000\n" % (
                len(data['substrats']['maps']), len(data['substrats']['diff'])))
        for i, j in zip(data['substrats']['maps'], data['products']['maps']): #перебираем построчно исходный файл
            if self.__coordtype == 3:
                i['x2'], i['y2'], i['z2'] = j['x'] * 100, j['y'] * 100, j['z'] * 100
                i['x'] *= 100
                i['y'] *= 100
                i['z'] *= 100
                self.__fileTowrite.write(
                    "%(x)5d%(x2)5d%(y)5d%(y2)5d%(z)5d%(z2)5d %(element)-3s%(izotop)2s%(charge)3s  0  0  0  0  0%(mark)3s  0%(map)3s  0  0\n" % i)
            elif self.__coordtype == 2:
                i['x2'], i['y2'], i['z2'] = j['x'], j['y'], j['z']
                self.__fileTowrite.write(
                    "%(x2)10.4f%(y2)10.4f%(z2)10.4f %(element)-3s%(izotop)2s%(charge)3s  0  0  0  0  0%(mark)3s  0%(map)3s  0  0\n" % i)
            else:
                self.__fileTowrite.write(
                    "%(x)10.4f%(y)10.4f%(z)10.4f %(element)-3s%(izotop)2s%(charge)3s  0  0  0  0  0%(mark)3s  0%(map)3s  0  0\n" % i)
        for i in data['substrats']['diff']:
            self.__fileTowrite.write("%3s%3s%3s  0  0  0  0\n" % i)
        self.__fileTowrite.write("M  END\n")
        for i in data['substrats']['meta'].items():
            self.__fileTowrite.write(">  <%s>\n%s\n" % i)
        self.__fileTowrite.write("$$$$\n")


#        self.close()
#        return True


if __name__ == '__main__':
    main()