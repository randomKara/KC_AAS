# KC_AAS : Authentification centralisée avec Keycloak et Dex

Ce projet met en place une solution d'authentification centralisée en utilisant Keycloak comme fournisseur d'identité et Dex comme passerelle OIDC. Une application Flask est utilisée pour démontrer l'intégration.

## Architecture

*   **Keycloak :** Gère les utilisateurs, les rôles et les autorisations.
*   **Dex :** Agit comme un serveur OIDC, fédérant Keycloak et l'application Flask.
*   **Flask App :** Une application simple qui utilise Dex pour authentifier les utilisateurs.

## Prérequis

*   Docker
*   docker compose

## Installation

1.  Clonez le dépôt.
2.  Ajoutez les lignes suivantes à votre fichier `/etc/hosts` :

    ```
    127.0.0.1 keycloak
    127.0.0.1 dex
    ```
3.  Exécutez `docker compose up --build` pour démarrer les services.

## Configuration

*   La configuration de Dex se trouve dans `dex/config.yaml`.
*   Les utilisateurs et les rôles Keycloak sont importés depuis `keycloak/imports/realm-export.json`.
*   L'application Flask est configurée via des variables d'environnement dans le `docker-compose.yml`.

## Utilisation

1.  Accédez à l'application Flask à l'adresse `http://localhost:5000`.
2.  Vous serez redirigé vers Dex pour vous authentifier.
3.  Choisissez Keycloak comme fournisseur d'identité.
4.  Connectez-vous avec un utilisateur défini dans `keycloak/imports/realm-export.json`.

## Points d'attention

*   Le fichier `docker-compose.yml` contient un délai (`sleep 60`) pour assurer que Keycloak soit démarré avant Dex. Cette solution est temporaire et devrait être améliorée avec un mécanisme de healthcheck plus robuste. Voir `ISSUE.md` pour plus de détails.
