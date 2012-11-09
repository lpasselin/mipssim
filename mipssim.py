#!/usr/bin/env python3
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

"""
Simulateur d'architecture MIPS 64 bits

Auteurs : Yannick Hold-Geoffroy, Mathieu Juneau et Vincent Martel.
Maintenance : Julien-Charles Lévesque.
"""

# Operation warning
import sys
if sys.version_info < (2, 7):
    print('ATTENTION!!!')
    print('Vous tentez de lancer mipssim.py sur une version de Python inférieure à 2.7!')
    print('Python 2.6 et ses versions antérieures ne supportent pas OrderedDict, qui')
    print('est requise pour ce simulateur.')
    sys.exit(1)

from src.configuration import *
from src.interpreteur import *
from src.simulateur import *

import getopt


class Usage(Exception):
    """
    Déclaration des exceptions relatives aux entrées de l'utilisateur.
    """
    def __init__(self, msg):
        self.msg = msg


def main(argv=None):
    # Indications sur le lancement du simulateur et nom des auteurs (Requis pour le TP)
    print('Simulateur de MIPS en Python (2.7+)')
    print('Étudiants: %s' % "Name")
    
    # Évaluation des arguments
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "hd", ["help", "debug"])
            if opts != [] and '-d' in list(zip(*opts))[0]:
                debug = True
            else:
                debug = False

            if opts != [] and '-h' in list(zip(*opts))[0]:
                print("""Utilisation de mipssim.py :
    python ./mipssim.py config.xml source.mips [trace.txt]

Testé avec les versions de python suivantes: 2.7, 3.2
        """)
                return
        except getopt.error as msg:
                raise Usage(msg)
        try:
            config_file = args[0]
            source_file = args[1]
        except:
            raise Usage('Veuillez spécifier le fichier de configuration et le fichier source.')
        try:
            trace_file = args[2]
        except:
            # Fichier de trace optionnel
            trace_file = None
    except Usage as err:
        sys.stderr.write("%s\nErreur en analysant les paramètres. Pour un exemple d'utilisation, passez -h en argument.\n" % (err.msg))
        sys.stderr.flush()
        return 2
    
    # Début du programme.
    # Le path du fichier de configuration est dans config_file
    # Le path du fichier de source est dans source_file
    # Le path du fichier de trace est dans trace_file, s'il y a lieu, sinon il s'évalue à None

    # Génération de la configuration du MIPS
    config = mips_configuration(config_file)

    # Génération de l'interpréteur
    interpreter = mips_interpreteur(source_file)

    # Génération du simulateur
    simulateur = mips_simulateur(config, interpreter, trace_file)

    # Affichage de l'état initial de la mémoire et des registre.
    print("État initial des registres: " + str(config.registre))
    print("État initial de la mémoire: " + str(config.memoire))

    # Démarrage du simulateur
    print('Démarrage du simulateur')
    retour = simulateur.go(debug)
    print('Arrêt du simulateur')

    # Affichage de l'état final de la mémoire et des registre.
    print("État final des registres: " + str(config.registre))
    print("État final de la mémoire: " + str(config.memoire))

    # Affichage de l'état du processus à sa terminaison.
    if retour == 0:
        print('Simulation terminée avec succès')
    else:
        print('Une erreur est survenue lors de l`exécution du programme')
    return retour

if __name__ == "__main__":
    sys.exit(main())
