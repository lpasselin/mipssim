# MIPSSIM

Simulateur de code MIPS conçu pour le cours GIF-3000 à l'Université Laval. Testé avec Python 2.7 et 3.3.

Pour vous servir du simulateur, il faut lancer le fichier `mipssim/mipssim.py` avec comme paramètres le nom d'un fichier de configuration (placés dans le dossier `conf/`) et d'un fichier de code assembleur (placés dans le dossier `asm/`). L'aide d'utilisation fournie par le programme avec le drapeau `-h` est la suivante : 

    :::text
     usage: mipssim.py [-h] config_file source_file [trace_file]
          
     Simulateur de MIPS en Python (2.7+). Testé avec Python 2.7 et 3.3.
      
     positional arguments:
       config_file  Fichier xml contenant la configuration du simulateur.
       source_file  Fichier contenant le code source à exécuter.
       trace_file   Ficher dans lequel sera écrit l'état du simulateur à tous les
                      pas de temps.
      
     optional arguments:
       -h, --help   show this help message and exit

