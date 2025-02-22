import sys
import socket
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLabel,
    QVBoxLayout, QWidget, QPushButton, QHBoxLayout,
    QMessageBox, QListWidget, QListWidgetItem, QCheckBox
)
from PySide6.QtCore import Signal, QObject, Slot, Qt
from gui.hockey_field import HockeyField
from gui.terrain_config import TerrainConfig, TerrainDimensionsDialog
from networking.mqtt_client import MQTTClient
from networking.udp_discovery import UDPDiscoveryServer
from match.match_mode import MatchMode

class SignalManager(QObject):
    esp32_discovered = Signal(str, str)  # device_name, mac_address

class ESPListItem(QWidget):
    def __init__(self, device_name, mac_address, parent=None):
        super().__init__(parent)
        self.device_name = device_name
        self.mac_address = mac_address
        self.is_connected = False
        self.is_sending = False
        
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 2, 5, 2)
        self.setLayout(layout)
        
        info_label = QLabel(f"{device_name} ({mac_address})")
        layout.addWidget(info_label)
        
        layout.addStretch()
        
        self.connect_button = QPushButton("Connecter")
        self.connect_button.setFixedWidth(100)
        layout.addWidget(self.connect_button)
        
        self.send_button = QPushButton("Démarrer")
        self.send_button.setFixedWidth(80)
        self.send_button.setEnabled(False)
        layout.addWidget(self.send_button)

class RollerHockeyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # d1 qui correspond au capteur situé en bas au mileu (HG)
        # d2 qui correspond au capteur situé en bas au mileu (HD)
        # d3 qui correspond au capteur situé en bas au mileu (BM)
        self.d1 = None
        self.d2 = None
        self.d3 = None
        self.setWindowTitle("Palet de Roller Hockey Connecté")
        self.mqtt_client = None
        self.is_connected = False
        self.discovery_server = None
        self.esp_widgets = {}
        
        # Créer le gestionnaire de signaux
        self.signal_manager = SignalManager()
        self.signal_manager.esp32_discovered.connect(self.on_esp32_discovered)
        
        self._init_ui()
        self._start_discovery_server()
        
    def _init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout()
        self.layout.setSpacing(5)  # Réduit l'espacement entre les widgets
        self.layout.setContentsMargins(5, 5, 5, 5)  # Réduit les marges
        self.central_widget.setLayout(self.layout)
        
        # Mode match (maintenant en premier)
        self.match_mode = MatchMode(self)
        self.layout.addWidget(self.match_mode)
        
        # Terrain de hockey (maintenant en deuxième)
        self.hockey_field = HockeyField()
        self.layout.addWidget(self.hockey_field)
        
        # Contrôles MQTT
        mqtt_container = QWidget()
        mqtt_layout = QVBoxLayout(mqtt_container)  
        mqtt_layout.setContentsMargins(5, 5, 5, 5)  # Réduit les marges
        mqtt_layout.setSpacing(5)  # Réduit l'espacement

        # Case à cocher pour le suivi caméra dans sa propre ligne
        camera_tracking_layout = QHBoxLayout()
        camera_tracking_layout.setSpacing(5)  # Réduit l'espacement
        self.camera_tracking_checkbox = QCheckBox("Suivi caméra")
        self.camera_tracking_checkbox.stateChanged.connect(self._on_camera_tracking_changed)
        camera_tracking_layout.addWidget(self.camera_tracking_checkbox)
        camera_tracking_layout.addStretch()
        mqtt_layout.addLayout(camera_tracking_layout)

        # Personnalisation de la taille du terrain
        terrain_config_layout = QHBoxLayout()
        terrain_config_layout.setSpacing(5)  # Réduit l'espacement
        self.terrain_config_button = QPushButton("Configuration du terrain")
        self.terrain_config_button.clicked.connect(self._show_terrain_config)
        terrain_config_layout.addWidget(self.terrain_config_button)
        terrain_config_layout.addStretch()
        mqtt_layout.addLayout(terrain_config_layout)

        # Status et boutons
        status_button_layout = QHBoxLayout()
        status_button_layout.setSpacing(5)  # Réduit l'espacement
        self.status_label = QLabel("Status: Déconnecté")
        self.status_label.setStyleSheet("color: red;")
        status_button_layout.addWidget(self.status_label)
        status_button_layout.addStretch()
        mqtt_layout.addLayout(status_button_layout)
        
        self.layout.addWidget(mqtt_container)

        # Liste des ESP32
        devices_container = QWidget()
        devices_layout = QVBoxLayout(devices_container)
        devices_layout.setContentsMargins(5, 5, 5, 5)  # Réduit les marges
        devices_layout.setSpacing(5)  # Réduit l'espacement
        
        self.esp_list_label = QLabel("Palets détectés:")
        self.esp_list_label.setStyleSheet("font-weight: bold;")
        devices_layout.addWidget(self.esp_list_label)
        
        self.esp_list = QListWidget()
        self.esp_list.setMaximumHeight(50)  # Limite la hauteur de la liste
        self.esp_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: white;
            }
            QListWidget::item {
                padding: 2px;
                border-bottom: 1px solid #eeeeee;
            }
            QListWidget::item:last {
                border-bottom: none;
            }
        """)
        devices_layout.addWidget(self.esp_list)
        self.layout.addWidget(devices_container)

    def _show_terrain_config(self):
        config = TerrainConfig()
        dialog = TerrainDimensionsDialog(config.width, config.height, self)
        if dialog.exec():
            new_width = dialog.width_input.value()
            new_height = dialog.height_input.value()
            config.set_dimensions(new_width, new_height)

    def update_puck_position(self, d1=None, d2=None, d3=None):
        if d1 is not None:
            self.d1 = d1
        if d2 is not None:
            self.d2 = d2
        if d3 is not None:
            self.d3 = d3
        if self.d1 is not None and self.d2 is not None and self.d3 is not None:
            try:
                self.hockey_field.update_from_distances(self.d1, self.d2, self.d3)
            except Exception as e:
                print(f"Erreur lors de la mise à jour de la position du palet: {str(e)}")

    def update_message_area(self, message):
        """Mettre à jour la zone de message"""
        try:
            self.message_area.append(message)
        except Exception as e:
            print(f"Erreur lors de la mise à jour de la zone de message: {e}")

    def show_error(self, title, message):
        """Afficher une boîte de dialogue d'erreur"""
        QMessageBox.critical(self, title, message)

    def _start_discovery_server(self):
        """Démarrer le serveur de découverte UDP"""
        def discovery_callback(device_name, mac_address):
            # Émettre le signal depuis le thread UDP
            self.signal_manager.esp32_discovered.emit(device_name, mac_address)
            
        self.discovery_server = UDPDiscoveryServer(discovery_callback)
        self.discovery_server.start()

    @Slot(str, str)

    def start_mqtt(self):
        """Démarrer le client MQTT"""
        try:
            if self.mqtt_client is None:
                self.mqtt_client = MQTTClient(
                    message_callback=self.update_puck_position,
                    connection_callback=self.connection_status_changed
                )
                self.mqtt_client.start_mosquitto()
                self.mqtt_client.start_mqtt()
        except Exception as e:
            self.show_error("Erreur de démarrage", f"Impossible de démarrer le client MQTT: {str(e)}")
            self.mqtt_client = None
            self.connection_status_changed(False)

    def stop_mqtt(self):
        """Arrêter le client MQTT"""
        if self.mqtt_client:
            try:
                self.mqtt_client.stop_mqtt()
                self.mqtt_client = None
                self.connection_status_changed(False)
            except Exception as e:
                self.show_error("Erreur d'arrêt", f"Erreur lors de l'arrêt du client MQTT: {str(e)}")

    def connection_status_changed(self, connected):
        """Mise à jour de l'interface selon l'état de la connexion"""
        try:
            self.is_connected = connected
            
            # Mettre à jour le label de status
            if connected:
                self.status_label.setText("Status: Connecté")
                self.status_label.setStyleSheet("color: green;")
            else:
                self.status_label.setText("Status: Déconnecté")
                self.status_label.setStyleSheet("color: red;")
        except Exception as e:
            self.show_error("Erreur lors de la mise à jour du statut", str(e))

    def on_esp32_discovered(self, device_name: str, mac_address: str):
        """Callback appelé quand un nouvel ESP32 est découvert (exécuté dans le thread principal)"""
        if mac_address not in self.esp_widgets:
            # Créer le widget pour l'ESP
            esp_widget = ESPListItem(device_name, mac_address)
            
            # Connexion des signaux des boutons
            esp_widget.connect_button.clicked.connect(
                lambda checked, esp=esp_widget, mac=mac_address: 
                self.handle_esp_connect(mac, not esp.is_connected)
            )
            esp_widget.send_button.clicked.connect(
                lambda checked, esp=esp_widget, mac=mac_address: 
                self.handle_esp_send(mac, not esp.is_sending)
            )
            
            # Créer l'item de liste
            item = QListWidgetItem()
            item.setSizeHint(esp_widget.sizeHint())
            self.esp_list.addItem(item)
            self.esp_list.setItemWidget(item, esp_widget)
            
            # Stocker le widget
            self.esp_widgets[mac_address] = esp_widget

    def handle_esp_connect(self, device_id: str, should_connect: bool):
        try:
            esp_widget = self.esp_widgets[device_id]
            
            if should_connect:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    s.connect(('8.8.8.8', 80))
                    local_ip = s.getsockname()[0]
                finally:
                    s.close()

                if self.discovery_server.send_response(device_id, local_ip):
                    esp_widget.is_connected = True
                    esp_widget.connect_button.setText("Déconnecter")
                    esp_widget.connect_button.setStyleSheet("background-color: #ffcccc;")
                    esp_widget.send_button.setEnabled(True)
            else:
                if self.discovery_server.send_response(device_id, "deconnect"):  # "deconnect" au lieu de "stop"
                    esp_widget.is_connected = False
                    esp_widget.connect_button.setText("Connecter")
                    esp_widget.connect_button.setStyleSheet("")
                    esp_widget.send_button.setEnabled(False)
                    esp_widget.is_sending = False
                    esp_widget.send_button.setText(" palet")
                    esp_widget.send_button.setStyleSheet("")
        except Exception as e:
            self.show_error("Erreur de contrôle", f"Erreur lors de la gestion de la connexion: {str(e)}")

    def handle_esp_send(self, device_id: str, should_send: bool):
        try:
            esp_widget = self.esp_widgets[device_id]
            
            if should_send:
                if self.mqtt_client is None:
                    self.mqtt_client = MQTTClient(
                        message_callback=self.update_puck_position,
                        connection_callback=self.connection_status_changed
                    )
                    self.mqtt_client.start_mqtt()
                
                self.discovery_server.send_response(device_id, "start")  # Envoi de "start"
                esp_widget.is_sending = True
                esp_widget.send_button.setText("Arrêter palet")
                esp_widget.send_button.setStyleSheet("background-color: #ffcccc;")
            else:
                self.discovery_server.send_response(device_id, "stop")  # Envoi de "stop"
                esp_widget.is_sending = False
                esp_widget.send_button.setText("Démarrer palet")
                esp_widget.send_button.setStyleSheet("")
        except Exception as e:
            self.show_error("Erreur d'envoi", f"Erreur lors de la gestion des données : {str(e)}")


    def closeEvent(self, event):
        """Gérer la fermeture propre de l'application"""
        try:
            if self.mqtt_client:
                self.stop_mqtt()
            if self.discovery_server:
                self.discovery_server.stop()
            event.accept()
        except Exception as e:
            self.show_error("Erreur de fermeture", f"Erreur lors de la fermeture de l'application: {str(e)}")
            event.accept()

    def _on_camera_tracking_changed(self, state):
        """Gère le changement d'état de la case à cocher du suivi caméra"""
        is_enabled = state == Qt.CheckState.Checked.value
        self.hockey_field.position_calculator.set_camera_tracking(is_enabled)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Application du style
    app.setStyle("Fusion")
    window = RollerHockeyApp()
    window.show()
    sys.exit(app.exec())