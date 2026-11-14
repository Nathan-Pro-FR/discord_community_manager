# 🤖 discord_community_manager

Bot Discord autonome de création, d'administration, de statistiques en temps réel et d'analyse communautaire, accompagné d'un tableau de bord Web interactif.

## ✨ Fonctionnalités principales

* **Création automatique de serveur (SFW)** : Déploiement complet des catégories, salons textuels/vocaux, rôles et permissions sans création de doublons.
* **Statistiques en temps réel** : Comptabilisation des messages texte, médias (images, vidéos, GIF, fichiers joints), modifications, suppressions et mouvements de membres (arrivées/départs).
* **Embed permanente auto-actualisée** : Tableau de bord en direct dans un salon dédié avec mise à jour groupée toutes les 30 secondes pour respecter les limites de l'API Discord.
* **Rapports périodiques automatisés** : Bilans hebdomadaires, mensuels et trimestriels avec calcul automatique de l'évolution en pourcentage par rapport à la période précédente.
* **Détection des pics d'activité** : Alertes automatiques dans le salon de modération en cas de hausse inhabituelle de l'activité par rapport à la moyenne des 7 derniers jours.
* **Dashboard Web** : Interface responsive (ordinateur et mobile) avec graphiques interactifs (`Chart.js`), historique des rapports et exportation CSV.

## 🏗️ Architecture du projet

```text
discord-community-manager/
├── bot/
│   ├── main.py              # Point d'entrée du bot et chargement des modules
│   ├── events/
│   │   └── messages.py      # Suivi des événements (messages, médias, membres)
│   └── commands/
│       ├── setup.py         # Commandes /setup et /setup-check
│       └── stats.py         # Commandes /stats, /report-now, /dashboard
├── services/
│   ├── analytics.py         # Classification des médias et agrégation des données
│   ├── embeds.py            # Construction et mise à jour de l'embed en direct
│   └── scheduler.py         # Tâches planifiées (rapports et détection de pics)
├── dashboard/
│   ├── app.py               # API et serveur Web FastAPI
│   └── templates/
│       └── index.html       # Interface graphique du dashboard
├── database/
│   ├── connection.py        # Connexion asynchrone PostgreSQL (SQLAlchemy)
│   └── models.py            # Modèles de tables statistiques
├── docker-compose.yml       # Orchestration PostgreSQL + Bot + Dashboard
├── Dockerfile               # Image Docker Python 3.11
├── requirements.txt         # Dépendances Python
└── .env.example             # Modèle des variables d'environnement
```

## 🛠️ Prérequis et configuration Discord

1. **Docker** et **Docker Compose** installés sur votre serveur ou machine.
2. Une application créée sur le [Discord Developer Portal](https://discord.com/developers/applications) :
* Récupérez le **Token** du bot dans l'onglet *Bot*.
* Activez les **Privileged Gateway Intents** suivants :
* `Server Members Intent`
* `Message Content Intent`


* Invitez le bot sur votre serveur avec les permissions **Administrateur** (ou gestion des salons, rôles et messages).



## 🚀 Installation et démarrage

1. **Cloner ou placer les fichiers du projet dans un dossier dédié :**
```bash
cd discord-community-manager

```


2. **Configurer les variables d'environnement :**
```bash
cp .env.example .env
```


Éditez le fichier `.env` et renseignez vos identifiants :
```env
DISCORD_TOKEN=votre_token_discord_ici
DATABASE_URL=postgresql+asyncpg://dcm_user:dcm_pass@db:5432/dcm_db
DASHBOARD_ADMIN_TOKEN=un_mot_de_passe_securise
DASHBOARD_URL=http://localhost:8000
```


3. **Lancer les conteneurs avec Docker :**
```bash
docker compose up -d --build
```


4. **Initialiser le serveur Discord :**
Exécutez la commande `/setup` dans n'importe quel salon de votre serveur Discord pour créer la structure complète et activer l'embed statistique en direct.


## 💬 Commandes Slash disponibles

| Commande | Permission | Description |
| --- | --- | --- |
| `/setup` | Administrateur | Installe automatiquement les catégories, salons, rôles et permissions SFW sans doublons. |
| `/setup-check` | Administrateur | Vérifie que tous les salons de la structure attendue sont bien présents. |
| `/stats` | Tous | Affiche les statistiques globales du serveur sur les 7 derniers jours avec évolution. |
| `/stats-member` | Tous | Affiche la fiche d'activité d'un membre spécifique sur 7 jours. |
| `/stats-channel` | Tous | Affiche le volume de messages et de médias d'un salon sur 7 jours. |
| `/report-now` | Administrateur | Génère et publie immédiatement un rapport (`weekly`, `monthly` ou `quarterly`). |
| `/dashboard` | Tous | Renvoie le lien d'accès au tableau de bord Web. |


## 🌐 Dashboard Web

Le tableau de bord est accessible à l'adresse configurée dans `DASHBOARD_URL` (par défaut `http://localhost:8000`) en ajoutant le jeton d'administration défini dans `.env` :

```text
http://localhost:8000/?token=un_mot_de_passe_securise
```

Depuis l'interface, vous pouvez visualiser les indicateurs clés des 7 derniers jours, suivre l'évolution quotidienne sur un graphique interactif, consulter l'historique des rapports générés et exporter les statistiques des 90 derniers jours au format **CSV**.
---

## 🔒 Confidentialité et sécurité

* **Aucun contenu stocké** : Le bot enregistre uniquement des compteurs numériques agrégés (nombre de messages, type de médias, horodatage). Le texte des conversations et les fichiers envoyés ne sont jamais sauvegardés en base de données.
* **Protection des accès** : Le token Discord est isolé dans le fichier `.env` (à ne jamais versionner sur Git) et l'accès au dashboard est protégé par un jeton d'administration.

