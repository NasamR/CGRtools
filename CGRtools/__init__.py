# -*- coding: utf-8 -*-
#
#  Copyright 2014-2020 Ramil Nugmanov <nougmanoff@protonmail.com>
#  Copyright 2014-2019 Alexandre Varnek <varnek@unistra.fr> base idea of CGR approach
#  This file is part of CGRtools.
#
#  CGRtools is free software; you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with this program; if not, see <https://www.gnu.org/licenses/>.
#
from .containers import *
from .files import *
from .preparer import *
from .reactor import *
from .utils import *


smiles = SMILESRead.create_parser(ignore=True)
xyz = XYZRead.create_parser()


__all__ = ['smiles', 'xyz']

if 'INCHIRead' in locals():
    inchi = INCHIRead.create_parser()
    __all__.append('inchi')
