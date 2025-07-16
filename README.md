# KC_AAS : Authentification centralisée avec Keycloak et Dex

Ce projet met en place une solution d'authentification centralisée en utilisant Keycloak comme fournisseur d'identité et Dex comme passerelle OIDC. Une application Flask est utilisée pour démontrer l'intégration.

## Architecture

*   **Keycloak :** Gère les utilisateurs, les rôles et les autorisations.
*   **Dex :** Agit comme un serveur OIDC, fédérant Keycloak et l'application Flask (lancé à la demande).
*   **Flask App :** Une application simple qui utilise Dex pour authentifier les utilisateurs.

## Prérequis

*   Docker
*   docker compose
*   curl (pour les vérifications de santé)

## Installation et Démarrage

### 1. Préparation

1.  Clonez le dépôt.
2.  Ajoutez les lignes suivantes à votre fichier `/etc/hosts` :

    ```
    127.0.0.1 keycloak
    ```

### 2. Démarrage de Keycloak

Démarrez d'abord Keycloak (le fournisseur d'identité principal) :

```bash
docker compose up keycloak -d
```

Attendez que Keycloak soit complètement démarré (environ 1-2 minutes).

### 3. Lancement de Dex (à la demande)

Utilisez le script dédié pour lancer Dex quand vous en avez besoin :

```bash
./scripts/run_dex.sh
```

Ce script :
- Vérifie que Keycloak est accessible
- Lance Dex en tant que conteneur Docker standalone
- Attend que Dex soit prêt
- Fournit des informations détaillées sur le processus

### 4. Démarrage de l'application Flask

Une fois Dex en cours d'exécution, démarrez l'application Flask :

```bash
docker compose up flask-app
```

## Configuration

*   **Dex :** Configuration dans `dex/config.yaml` (mode standalone)
*   **Keycloak :** Importation automatique du realm depuis `keycloak/imports/realm-export.json`
*   **Flask :** Configuration via variables d'environnement dans `docker-compose.yml`

## Utilisation

1.  **Démarrez les services dans l'ordre :**
    - Keycloak : `docker compose up keycloak -d`
    - Dex : `./scripts/run_dex.sh`
    - Flask : `docker compose up flask-app`

2.  **Accédez à l'application :**
    - Application Flask : `http://localhost:5000`
    - Interface Keycloak : `http://localhost:8080` (admin/admin)

3.  **Processus d'authentification :**
    - Cliquez sur "Se connecter" dans l'application Flask
    - Vous serez redirigé vers Dex
    - Choisissez "Keycloak" comme fournisseur d'identité
    - Connectez-vous avec un utilisateur du realm KC_AAS

## Gestion de Dex

### Lancer Dex
```bash
./scripts/run_dex.sh
```

### Arrêter Dex
```bash
./scripts/stop_dex.sh
```

### Voir les logs de Dex
```bash
docker logs -f kc_aas_dex
```

## Avantages de cette Architecture

**Dex à la demande :**
- **Contrôle granulaire :** Lancez Dex uniquement quand nécessaire
- **Débogage facilité :** Logs isolés et configuration explicite
- **Flexibilité :** Possibilité de modifier la configuration sans affecter les autres services
- **Performance :** Économie de ressources quand Dex n'est pas nécessaire

**Séparation des responsabilités :**
- **Keycloak :** Gestion des utilisateurs et des identités (service permanent)
- **Dex :** Broker OIDC pour l'application (service à la demande)
- **Flask :** Application cliente démonstrative

## Proof of Work - Démonstration Automatisée

### Démarrage Rapide (Recommandé)

Pour une démonstration complète automatisée utilisant tous les scripts Python :

```bash
# Installation des dépendances Python
pip3 install -r requirements.txt

# Démarrage complet automatisé
./scripts/quick_start.sh
```

### Démonstration Détaillée

Pour une démonstration pas-à-pas avec explications :

```bash
# Démarrer Keycloak
docker compose up keycloak -d

# Lancer la démonstration proof of work
python3 scripts/demo_proof_of_work.py --verbose

# Ou avec un utilisateur personnalisé
python3 scripts/demo_proof_of_work.py --user-name mon-utilisateur --user-password mon-mot-de-passe
```

### Scripts Python Disponibles

Le projet inclut plusieurs scripts Python pour automatiser la configuration :

- **`create_user_in_kc_aas.py`** : Création d'utilisateurs dans Keycloak
- **`create_client_in_kc_aas.py`** : Configuration de clients OIDC dans Keycloak
- **`create_dex_config.py`** : Génération automatique de configuration Dex
- **`list_all_users.py`** : Listage des utilisateurs existants
- **`demo_proof_of_work.py`** : Démonstration complète end-to-end

### Avantages de la Proof of Work Automatisée

- **Configuration automatique** : Création automatique des utilisateurs et clients
- **Validation end-to-end** : Vérification que tous les composants fonctionnent ensemble
- **Débogage facilité** : Logs détaillés et messages d'erreur explicites
- **Reproductibilité** : Configuration identique à chaque exécution
- **Documentation vivante** : Le code sert de documentation des intégrations

## Endpoints Utiles

- **Application Flask :** `http://localhost:5000`
- **Discovery OIDC (Dex) :** `http://localhost:5556/dex/.well-known/openid-configuration`
- **Interface Keycloak :** `http://localhost:8080`
- **Health Check Flask :** `http://localhost:5000/health`
