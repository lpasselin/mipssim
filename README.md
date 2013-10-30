# MIPSSIM

Simulateur de code MIPS conçu pour le cours GIF-3000 à l'Université Laval. Testé avec Python 2.7 et 3.3.

Pour vous servir du simulateur, il faut lancer le fichier `mipssim/mipssim.py` avec comme paramètres le nom d'un fichier de configuration (placés dans le dossier `conf/`) et d'un fichier de code assembleur (placés dans le dossier `asm/`). Le programme effectuera une simulation du code donné sur un microprocesseur avec une architecture MIPS paramétrisée par le contenu du fichier de configuration (nombre d'unités fonctionnelles, nombre de cycles pour exécuter les opérations à virgule flottante, etc.).

Le simulateur imprimera l'état de la mémoire et des registres au début et à la fin de l'exécution. Pour avoir plus d'information, il faudra donner un troisième paramètre, soit un nom de fichier dans lequel déposer une *trace* de l'exécution. Ce fichier contiendra le contenu du tampon de réordonnancement, des stations de réservations et des registres à chaque cycle de la simulation. Exemple : 

    :::text
    Cycle: 11
    Program Counter : 3
    Stations de réservation:
    +---------+-------+-----+-----+----+----+------+---+
    | Station |   Op  |  Vj |  Vk | Qj | Qk | Dest | A |
    +---------+-------+-----+-----+----+----+------+---+
    |  Load1  |  L.D  | 184 |     |    |    |  5   | 0 |
    |  Store1 |  S.D  |     | 184 | 6  |    |  7   | 0 |
    |   Add1  | ADD.D |     | 3.0 | 5  |    |  6   |   |
    |  Mult1  |       |     |     |    |    |      |   |
    |   ALU1  |       |     |     |    |    |      |   |
    | Branch1 |       |     |     |    |    |      |   |
    +---------+-------+-----+-----+----+----+------+---+
    Registres: 
    +------+------+-----+-----+-----+------+-----+-----+-----+-----+-----+
    |      |  0   |  1  |  2  |  3  |  4   |  5  |  6  |  7  |  8  |  9  |
    +------+------+-----+-----+-----+------+-----+-----+-----+-----+-----+
    | ROB# |      |  3  |     |     |      |     |     |     |     |     |
    |  R0  |  0   | 192 |  -8 |  0  |  0   |  0  |  0  |  0  |  0  |  0  |
    | ROB# |      |     |     |     |      |     |  X  |  X  |  X  |  X  |
    | R10  |  0   |  0  |  0  |  0  |  0   |  0  |  X  |  X  |  X  |  X  |
    | ROB# |  5   |     |     |     |  6   |     |     |     |     |     |
    |  F0  | 10.0 | 0.0 | 3.0 | 0.0 | 13.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
    | ROB# |      |     |     |     |      |     |  X  |  X  |  X  |  X  |
    | F10  | 0.0  | 0.0 | 0.0 | 0.0 | 0.0  | 0.0 |  X  |  X  |  X  |  X  |
    +------+------+-----+-----+-----+------+-----+-----+-----+-----+-----+
    ROB: 
    +--------+-------------+---------------------+------+-------+--------+
    | Entrée | Instruction |                     | État | Dest. | Valeur |
    +--------+-------------+---------------------+------+-------+--------+
    |   2    |     S.D     |   ['F4', '0(R1)']   |  3   |       |  13.0  |
    |   3    |    DADDI    | ['R1', 'R1', '#-8'] |  3   |   R1  |  184   |
    |   4    |     BNE     |  ['R1', 'R2', '#0'] |  3   |       |  True  |
    |   5    |     L.D     |   ['F0', '0(R1)']   |  1   |   F0  |        |
    |   6    |    ADD.D    |  ['F4', 'F0', 'F2'] |  1   |   F4  |        |
    |   7    |     S.D     |   ['F4', '0(R1)']   |  1   |       |        |
    +--------+-------------+---------------------+------+-------+--------+

L'aide d'utilisation fournie par le programme avec le drapeau `-h` est la suivante : 

    :::text
    usage: mipssim.py [-h] [-L LATEX_TRACE_FILE] [-d]
                      config_file source_file [trace_file]

    Simulateur de MIPS en Python (2.7+). Testé avec Python 2.7 et 3.3.

    positional arguments:
      config_file          Fichier xml contenant la configuration du simulateur.
      source_file          Fichier contenant le code source à exécuter.
      trace_file           Ficher dans lequel sera écrit l'état du simulateur à
                           tous les pas de temps. (default: None)

    optional arguments:
      -h, --help           show this help message and exit
      -L LATEX_TRACE_FILE  Fichier pour écrire une trace sous format LaTeX
                           (surtout les tableaux). (default: None)
      -d                   Force l'impression de davantage d'information à chaque
                           étape de l'exécution dans la ligne de commande.
                           (default: False)

