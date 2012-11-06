# -*- coding: utf-8 -*-

# Copyright (c) 2011, Yannick Hold-Geoffroy on behalf of Université Laval
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
#
#    Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
#    Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer 
#       in the documentation and/or other materials provided with the distribution.
#    Neither the name of the Université Laval nor the names of its contributors may be used to endorse or promote products derived 
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR 
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, 
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF 
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, 
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
#import re

from src.lib.prettytable import PrettyTable
from src.interpreteur import INSTRUCTION_SET, memory_re
 

class gestion_deverminage(object):
    
    def __init__(self, trace_file=None):
        if trace_file != None:
            self.trace_ptr = open(os.path.abspath(
                                  os.path.join(
                                    os.path.dirname(__file__),
                                    "..",
                                    trace_file)),
                                  'w')
        self.horloge = 0

    def __del__(self):
        if self.trace_ptr != None:
            self.trace_ptr.close()

    def mise_a_jour_trace(self, configuration):
        """
        Écriture du fichier de trace.
        """
        # Incrémentation de l'horloge
        self.horloge += 1

        # Création de la table des stations de réservation
        noneify = lambda x: x if x != None else ''
        variables_a_afficher = configuration.unite_fonctionnelle.list()
        res_table = PrettyTable(["station"] + \
                                 configuration.unite_fonctionnelle[variables_a_afficher[0]][0].keys())
        for station_type in sorted(variables_a_afficher):
            types = configuration.unite_fonctionnelle[station_type]
            for index, station_number in enumerate(types):
                # Trouver l'adresse de l'unité fonctionnelle
                for a in types[index]:
                    if a == str('op'):
                        if types[index]['op'] != None:
                            for b in types[index]['op'][1]:
                                if memory_re.match(b) is not None:
                                    R1Value = configuration.registre[str(b.split('(')[1][:-1])]
                                    if str(R1Value)[0] != str('&'):
                                        Offset = int(b.split('(')[0])
                                        AddrValue = R1Value + Offset
                                        station_number['addr'] = AddrValue
                # Trouver l'opération
                op_back = []
                if station_number['op'] is not None:
                    for inst in INSTRUCTION_SET.items():
                        if inst[1] is station_number['op'][0]:
                            op_back += inst

                # Trouver qj
                if station_number["qj"] not in [None, False]:
                    qj_back = station_number["qj"]
                    if isinstance(qj_back, str) is True and qj_back[0] == "&":
                        unite = "".join([a for a in qj_back if not a.isdigit()])
                        nouvelle = int("".join([a for a in qj_back if a.isdigit()]))
                        qj_back = unite + str(nouvelle)
                    qj_back = qj_back\
                          .replace("self.config.registre['", "")\
                          .replace("']", "")
                else:
                    qj_back = ''

                # Trouver qk
                if station_number["qk"] not in [None, False]:
                    qk_back = station_number["qk"]
                    if isinstance(qk_back, str) is True and qk_back[0] == "&":
                        unite = "".join([a for a in qk_back if not a.isdigit()])
                        nouvelle = int("".join([a for a in qk_back if a.isdigit()]))
                        qk_back = unite + str(nouvelle)
                    qk_back = qk_back\
                          .replace("self.config.registre['", "")\
                          .replace("']", "")
                else:
                    qk_back = ''

                row = [station_type + str(index + 1)] + \
                      [noneify(station_number[a]) for a in station_number.keys()]
                for index, element in enumerate(row):
                    if station_number.keys()[index - 1] == "op":
                        row[index] = op_back[0] if len(op_back) > 0 else ''
                    if station_number.keys()[index - 1] == "qj":
                        row[index] = qj_back
                    if station_number.keys()[index - 1] == "qk":
                        row[index] = qk_back
                res_table.add_row(row)

        # Table des registres
        registres = PrettyTable([' '] + [str(a) for a in range(10)])
        for row_ident in ["%s%d0" % (b, a) for b in ["R", "F"] for a in range(4)]:
            padding = ["X"] * 8 if row_ident[1] == '3' else []
            registres.add_row([row_ident] + \
                              [configuration.registre[row_ident[:row_ident.index('0')] + str(a)]
                              for a in range(10) if int(row_ident[1:]) + a < 32] + \
                              padding
                              )
        
        # ROB sous format table
        show_ROB = PrettyTable(["#", "Ocp.", "Unité fct.", "Cible", "Valeur"])
        for index, elem in enumerate(configuration.ROB):
            station_name = "".join([a for a in elem[0] if not a.isdigit()] + [str(int("".join([a for a in elem[0] if a.isdigit()])))])
            num_unite_fct = int("".join([str(int("".join([a for a in elem[0] if a.isdigit()])))]))
            unite_fct = configuration.unite_fonctionnelle["".join([a for a in elem[0] if not a.isdigit()])][num_unite_fct - 1]
            show_ROB.add_row([index,
                              noneify(unite_fct['busy']),
                              station_name,
                              elem[1][1].split(" ")[0]
                                .replace("self.config.registre['", "")
                                .replace("self.config.memoire[", "")
                                .replace("int(", "")
                                .replace(")/8", "")
                                .replace("else self.new_pc", "")
                                .replace("']", "")
                                .replace("self.new_pc", "PC")
                                .strip(" ()[]") if elem[1] != None else "",
                              elem[1][0]\
                                .replace("self.config.memoire[", "")
                                .replace("int(", "")
                                .replace(")/8", "")
                                .replace("else self.new_pc", "")
                                .strip(" ()[]")
                                if elem[1] != None else ""])

        # Affichage des tableaux précédemment créés
        self.trace_ptr.write("%s\n" % ("=" * 80))
        self.trace_ptr.write("Cycle: %d\n" % self.horloge)
        self.trace_ptr.write("Program Counter : %d\n" % configuration.PC)
        self.trace_ptr.write("Stations de réservation:\n%s\n\n" % str(res_table))
        self.trace_ptr.write("Registres: \n%s\n" % str(registres))
        self.trace_ptr.write("ROB: \n%s\n" % (str(show_ROB)))
        #self.trace_ptr.write(str(["%.2f" % a for a in self.config.memoire])+"\n")

        self.trace_ptr.flush()
