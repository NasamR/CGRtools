# -*- coding: utf-8 -*-
#
#  Copyright 2018-2020 Ramil Nugmanov <nougmanoff@protonmail.com>
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
from collections import defaultdict, deque
from typing import List, Optional, Tuple
from .._functions import lazy_product
from ..exceptions import InvalidAromaticRing


class Aromatize:
    __slots__ = ()

    def thiele(self) -> bool:
        """
        Convert structure to aromatic form (Huckel rule ignored). Return True if found any kekule ring.
        Also marks atoms as aromatic. For pyroles, furans, thiophene, phospholes bonds kepts in Kekule form.
        """
        atoms = self._atoms
        bonds = self._bonds
        sh = self._hybridizations

        rings = defaultdict(set)  # aromatic? skeleton. include quinones
        for ring in self.sssr:
            if all(sh[n] == 2 and atoms[n].atomic_number in (5, 6, 7, 15) for n in ring):
                n, *_, m = ring
                rings[n].add(m)
                rings[m].add(n)
                for n, m in zip(ring, ring[1:]):
                    rings[n].add(m)
                    rings[m].add(n)
        if not rings:
            return False

        double_bonded = [n for n in rings if any(m not in rings and b.order == 2 for m, b in bonds[n].items())]
        if double_bonded:  # delete quinones
            for n in double_bonded:
                for m in rings.pop(n):
                    rings[m].discard(n)
            while True:
                try:
                    n = next(n for n, ms in rings.items() if len(ms) == 1)
                except StopIteration:
                    break
                m = rings.pop(n).pop()
                pm = rings.pop(m)
                pm.discard(n)
                for x in pm:
                    rings[x].discard(m)
        if not rings:
            return False

        n_sssr = sum(len(x) for x in rings.values()) // 2 - len(rings) + len(self._connected_components(rings))
        if not n_sssr:
            return False
        rings = self._sssr(rings, n_sssr)  # search rings again

        seen = set()
        for ring in rings:
            seen.update(ring)
            n, *_, m = ring
            bonds[n][m]._Bond__order = 4
            for n, m in zip(ring, ring[1:]):
                bonds[n][m]._Bond__order = 4
        for n in seen:
            sh[n] = 4

        self.flush_cache()
        self._fix_stereo()  # check if any stereo centers vanished.
        return True

    def kekule(self) -> bool:
        """
        Convert structure to kekule form. Return True if found any aromatic ring. Set implicit hydrogen count and
        hybridization marks on atoms.

        Only one of possible double/single bonds positions will be set.
        For enumerate bonds positions use `enumerate_kekule`.
        """
        kekule = next(self.__kekule_full(), None)
        if kekule:
            self.__kekule_patch(kekule)
            self.flush_cache()
            return True
        return False

    def enumerate_kekule(self):
        """
        Enumerate all possible kekule forms of molecule.
        """
        for form in self.__kekule_full():
            copy = self.copy()
            copy._Aromatize__kekule_patch(form)
            yield copy

    def check_thiele(self, fast=True) -> bool:
        """
        Check basic aromaticity errors of molecule.

        :param fast: don't try to solve kekule form
        """
        try:
            if fast:
                self.__prepare_rings()
            else:
                next(self.__kekule_full(), None)
        except InvalidAromaticRing:
            return False
        return True

    def __prepare_rings(self):
        atoms = self._atoms
        charges = self._charges
        radicals = self._radicals
        bonds = self._bonds
        hydrogens = self._hydrogens

        rings = defaultdict(set)  # aromatic skeleton
        pyroles = set()

        double_bonded = set()
        triple_bonded = set()
        for n, m_bond in bonds.items():
            for m, bond in m_bond.items():
                bo = bond.order
                if bo == 4:
                    rings[n].add(m)
                elif bo == 2:
                    double_bonded.add(n)
                elif bo == 3:
                    triple_bonded.add(n)

        if not rings:
            return rings, pyroles, set()
        elif not triple_bonded.isdisjoint(rings):
            raise InvalidAromaticRing('triple bonds connected to rings')

        for r in self.sssr:
            if set(r).issubset(rings):
                n, *_, m = r
                if n not in rings[m]:
                    rings[m].add(n)
                    rings[n].add(m)
                for n, m in zip(r, r[1:]):
                    if n not in rings[m]:
                        rings[m].add(n)
                        rings[n].add(m)

        if any(len(ms) not in (2, 3) for ms in rings.values()):
            raise InvalidAromaticRing('not in ring aromatic bond or hypercondensed rings')

        double_bonded &= rings.keys()
        if any(len(rings[n]) != 2 for n in double_bonded):  # double bonded never condensed
            raise InvalidAromaticRing('quinone valence error')
        if any(atoms[n].atomic_number not in (6, 15, 16, 34, 52) or charges[n] for n in double_bonded):
            raise InvalidAromaticRing('quinone should be neutral S, Se, Te, C, P atom')

        for n in rings:
            an = atoms[n].atomic_number
            ac = charges[n]
            ab = len(bonds[n])
            if an == 6:  # carbon
                if ac == 0:
                    if ab not in (2, 3):
                        raise InvalidAromaticRing
                elif ac in (-1, 1):
                    if radicals[n]:
                        if ab == 2:
                            double_bonded.add(n)
                        else:
                            raise InvalidAromaticRing
                    elif ab == 3:
                        double_bonded.add(n)
                    elif ab == 2:  # benzene an[cat]ion or pyrole
                        pyroles.add(n)
                    else:
                        raise InvalidAromaticRing
                else:
                    raise InvalidAromaticRing
            elif an in (7, 15):
                if ac == 0:  # pyrole or pyridine. include radical pyrole
                    if radicals[n]:
                        if ab != 2:
                            raise InvalidAromaticRing
                        double_bonded.add(n)
                    elif ab == 3:
                        if an == 7:  # pyrole only possible
                            double_bonded.add(n)
                        else:  # P(III) or P(V)H
                            pyroles.add(n)
                    elif ab == 2:
                        ah = hydrogens[n]
                        if not ah:
                            pyroles.add(n)
                        elif ah == 1:  # only pyrole
                            double_bonded.add(n)
                        else:
                            raise InvalidAromaticRing
                    elif ab != 4 or an != 15:  # P(V) in ring
                        raise InvalidAromaticRing
                elif ac == -1:  # pyrole only
                    if ab != 2 or radicals[n]:
                        raise InvalidAromaticRing
                    double_bonded.add(n)
                elif ac != 1:
                    raise InvalidAromaticRing
                elif radicals[n]:
                    if ab != 2:  # not cation-radical pyridine
                        raise InvalidAromaticRing
                elif ab == 2:  # pyrole cation or protonated pyridine
                    pyroles.add(n)
                elif ab != 3:  # not pyridine oxyde
                    raise InvalidAromaticRing
            elif an == 8:  # furan
                if ab == 2 and (ac == 0 and not radicals[n] or ac == 1 and radicals[n]):
                    double_bonded.add(n)
                else:
                    raise InvalidAromaticRing
            elif an in (16, 34, 52):  # thiophene
                if n not in double_bonded:  # not sulphoxyde or sulphone
                    if ab == 2:
                        if radicals[n]:
                            if ac == 1:
                                double_bonded.add(n)
                            else:
                                raise InvalidAromaticRing('S, Se, Te cation-radical expected')
                        if ac == 0:
                            double_bonded.add(n)
                        elif ac != 1:
                            raise InvalidAromaticRing('S, Se, Te cation in benzene like ring expected')
                    else:
                        raise InvalidAromaticRing('S, Se, Te hypervalent ring')
            elif an == 5:  # boron
                if ac == 0:
                    if ab == 2:
                        if radicals[n]:  # C=1O[B]OC=1
                            double_bonded.add(n)
                        else:  # b1ccccc1 or C=1O[BH]OC=1
                            pyroles.add(n)
                    elif not radicals[n]:
                        double_bonded.add(n)
                    else:
                        raise InvalidAromaticRing
                elif ac == 1:
                    if ab == 2 and not radicals[n]:
                        double_bonded.add(n)
                    else:
                        raise InvalidAromaticRing
                elif ac == -1:
                    if ab == 2:
                        if not radicals[n]:  # C=1O[B-]OC=1 or [bH-]1ccccc1
                            pyroles.add(n)
                        # anion-radical is benzene like
                    elif radicals[n]:  # C=1O[B-*](R)OC=1
                        double_bonded.add(n)
                    else:
                        pyroles.add(n)
                else:
                    raise InvalidAromaticRing
            else:
                raise InvalidAromaticRing(f'only B, C, N, P, O, S, Se, Te possible, not: {atoms[n].atomic_symbol}')
        return rings, pyroles, double_bonded

    def __kekule_patch(self, patch):
        bonds = self._bonds
        atoms = set()
        for n, m, b in patch:
            bonds[n][m]._Bond__order = b
            atoms.add(n)
            atoms.add(m)
        for n in atoms:
            self._calc_hybridization(n)
            self._calc_implicit(n)

    def __kekule_full(self):
        rings, pyroles, double_bonded = self.__prepare_rings()
        atoms = set(rings)
        components = []
        while atoms:
            start = atoms.pop()
            component = {start: rings[start]}
            queue = deque([start])
            while queue:
                current = queue.popleft()
                for n in rings[current]:
                    if n not in component:
                        queue.append(n)
                        component[n] = rings[n]

            components.append(component)
            atoms.difference_update(component)

        for keks in lazy_product(*(self.__kekule_component(c, double_bonded & c.keys(), pyroles & c.keys())
                                   for c in components)):
            yield [x for x in keks for x in x]

    @staticmethod
    def __kekule_component(rings, double_bonded, pyroles):
        # (current atom, previous atom, bond between cp atoms, path deep for cutting [None if cut impossible])
        stack: List[List[Tuple[int, int, int, Optional[int]]]]
        if double_bonded:  # start from double bonded if exists
            start = next(iter(double_bonded))
            stack = [[(next(iter(rings[start])), start, 1, 0)]]
        else:  # select not pyrole not condensed atom
            try:
                start = next(n for n, ms in rings.items() if len(ms) == 2 and n not in pyroles)
            except StopIteration:  # all pyroles. select not condensed atom.
                try:
                    start = next(n for n, ms in rings.items() if len(ms) == 2)
                except StopIteration:  # fullerene?
                    start = next(iter(rings))
                    double_bonded.add(start)
                    stack = [[(next_atom, start, 2, 0)] for next_atom in rings[start]]
                else:
                    stack = [[(next_atom, start, 1, 0)] for next_atom in rings[start]]
            else:
                stack = [[(next_atom, start, 1, 0)] for next_atom in rings[start]]

        size = sum(len(x) for x in rings.values()) // 2
        path = []
        hashed_path = set()
        nether_yielded = True

        while stack:
            atom, prev_atom, bond, _ = stack[-1].pop()
            path.append((atom, prev_atom, bond))
            hashed_path.add(atom)

            if len(path) == size:
                yield path
                if nether_yielded:
                    nether_yielded = False
                del stack[-1]
                if stack:
                    path = path[:stack[-1][-1][-1]]
                    hashed_path = {x for x, *_ in path}
            elif atom != start:
                for_stack = []
                closures = []
                loop = 0
                for next_atom in rings[atom]:
                    if next_atom == prev_atom:  # only forward. behind us is the homeland
                        continue
                    elif next_atom == start:
                        loop = next_atom
                    elif next_atom in hashed_path:  # closure found
                        closures.append(next_atom)
                    else:
                        for_stack.append(next_atom)

                if loop:  # we found starting point.
                    if bond == 2:  # finish should be single bonded
                        if double_bonded:  # ok
                            stack[-1].insert(0, (loop, atom, 1, None))
                        else:
                            del stack[-1]
                            if stack:
                                path = path[:stack[-1][-1][-1]]
                                hashed_path = {x for x, *_ in path}
                            continue
                    elif double_bonded:  # we in quinone ring. finish should be single bonded
                        # side-path for storing double bond or atom is quinone or pyrole
                        if for_stack or atom in double_bonded or atom in pyroles:
                            stack[-1].insert(0, (loop, atom, 1, None))
                        else:
                            del stack[-1]
                            if stack:
                                path = path[:stack[-1][-1][-1]]
                                hashed_path = {x for x, *_ in path}
                            continue
                    else:  # finish should be double bonded
                        stack[-1].insert(0, (loop, atom, 2, None))
                        bond = 2  # grow should be single bonded

                if bond == 2 or atom in double_bonded:  # double in - single out. quinone has two single bonds
                    for next_atom in closures:
                        path.append((next_atom, atom, 1))  # closures always single-bonded
                        stack[-1].remove((atom, next_atom, 1, None))  # remove fork from stack
                    for next_atom in for_stack:
                        stack[-1].append((next_atom, atom, 1, None))
                elif len(for_stack) == 1:  # easy path grow. next bond double or include single for pyroles
                    next_atom = for_stack[0]
                    if next_atom in double_bonded:  # need double bond, but next atom quinone
                        if atom in pyroles:
                            stack[-1].append((next_atom, atom, 1, None))
                        else:
                            del stack[-1]
                            if stack:
                                path = path[:stack[-1][-1][-1]]
                                hashed_path = {x for x, *_ in path}
                    else:
                        if atom in pyroles:  # try pyrole and pyridine
                            opposite = stack[-1].copy()
                            opposite.append((next_atom, atom, 2, None))
                            stack[-1].append((next_atom, atom, 1, len(path)))
                            stack.append(opposite)
                        else:
                            stack[-1].append((next_atom, atom, 2, None))
                            if closures:
                                next_atom = closures[0]
                                path.append((next_atom, atom, 1))  # closures always single-bonded
                                stack[-1].remove((atom, next_atom, 1, None))  # remove fork from stack
                elif for_stack:  # fork
                    next_atom1, next_atom2 = for_stack
                    if next_atom1 in double_bonded:  # quinone next from fork
                        if next_atom2 in double_bonded:  # bad path
                            del stack[-1]
                            if stack:
                                path = path[:stack[-1][-1][-1]]
                                hashed_path = {x for x, *_ in path}
                        else:
                            stack[-1].append((next_atom1, atom, 1, None))
                            stack[-1].append((next_atom2, atom, 2, None))
                    elif next_atom2 in double_bonded:  # quinone next from fork
                        stack[-1].append((next_atom2, atom, 1, None))
                        stack[-1].append((next_atom1, atom, 2, None))
                    else:  # new path
                        opposite = stack[-1].copy()
                        stack[-1].append((next_atom1, atom, 1, None))
                        stack[-1].append((next_atom2, atom, 2, len(path)))
                        opposite.append((next_atom2, atom, 1, None))
                        opposite.append((next_atom1, atom, 2, None))
                        stack.append(opposite)
                elif closures and atom not in pyroles:  # need double bond, but closure should be single bonded
                    del stack[-1]
                    if stack:
                        path = path[:stack[-1][-1][-1]]
                        hashed_path = {x for x, *_ in path}

        if nether_yielded:
            raise InvalidAromaticRing(f'kekule form not found for: {list(rings)}')


__all__ = ['Aromatize']
