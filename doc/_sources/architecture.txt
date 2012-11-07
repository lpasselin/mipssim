Architecture du MIPS 64 bits et du simulateur
=============================================

L'architecture MIPS (**Microprocessor without Interlocked Pipeline Stages**) a un jeu d'instruction réduit (**RISC**). Plus d'informations sont disponibles dans le livre du cours ou sur internet.

.. figure:: _static/class_diagram.png
    :align: center
    :alt: Diagramme de classe du simulateur de MIPS

    Figure 1. Diagramme de classe du simulateur de MIPS 64 bits représentant les principales classes du projet.


Spécifications de l'architecture
--------------------------------

Les spécifications émulées par le simulateur sont les suivantes:

- Registres entiers: 32*
- Registres à point fottant: 32
- Six (6) unités fonctionnelles supportées:

    * Load
    * Store
    * Add
    * Mult
    * ALU
    * Branch
    
- :doc:`24 instructions assembleur<interpreteur>`

\* Le registre entier R0 est à lecture seule et représente toujours 0.
