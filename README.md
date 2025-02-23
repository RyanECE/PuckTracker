# PuckTracker
## Structure du projet 
/PuckTracker/
│── main.py                           # Fichier principal
│
├── gui/                              # Interface graphique
│   ├── __init__.py
│   ├── gui.py                        # Interface principale
│   ├── hockey_rink.py                # Affichage du terrain de hockey
│   ├── terrain_config.py             # Configuration du terrain
│
├── match/                            # Gestion du mode match
│   ├── __init__.py
│   ├── match_mode.py                 # Mode match (gestion des équipes, score, temps)
│
├── networking/                       # Communication réseau
│   ├── __init__.py
│   ├── mqtt_client.py                # Réception des données MQTT
│   ├── palet_position_sender.py      # Envoi de la position du palet en UDP
│   ├── udp_discovery.py              # Écoute en UDP de l'ESP32
│
├── tracking/                         # Gestion de la position du palet
│   ├── __init__.py
│   ├── puck_position.py              # Calcul de la position du palet
├── esp32/                            # Code a insérer dans les esp32
│   ├── ESP32_UWB_setup_anchor_BM/    # Code de l'ESP32 qui doit être en bas au milieu
│       ├──ESP32_UWB_setup_anchor_BM.ino
│   ├── ESP32_UWB_setup_anchor_HD/    # Code de l'ESP32 qui doit être en haut à droite
│       ├──ESP32_UWB_setup_anchor_HD.ino
│   ├── ESP32_UWB_setup_anchor_HG/    # Code de l'ESP32 qui doit être en haut à gauche du terrain
│       ├──ESP32_UWB_setup_anchor_HG.ino
│   ├── ESP32_UWB_setup_tag/          # Code de l'ESP32 qui doit être dans le palet
│       ├──ESP32_UWB_setup_tag.ino
│   ├── puck_position.py              # Calcul de la position du palet
│
└── README.md                         # Documentation du projet

## Description

PuckTracker est une application open-source faite en pythonpermetant de récupéré la position d'un palet de roller hockey et de transmettre la position du palet pour qu'une caméra suive la position du palet

## Pour installer le PuckTracker
```bash
   git clone https://github.com/RyanECE/PuckTracker.git
   cd  PuckTracker
   # Installation
   pip install -r requirements.txt
   # Pour lancer l'application
   python main.py

## Contribution

Les contributions sont les bienvenues ! Pour contribuer :

Forkez le projet.
Créez une branche pour votre fonctionnalité (git checkout -b feature/AmazingFeature).
Commitez vos modifications (git commit -m 'Add some AmazingFeature').
Poussez vers la branche (git push origin feature/AmazingFeature).
Ouvrez une Pull Request.

# Licence
Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails.
