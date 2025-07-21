# Problèmes et Améliorations Potentielles

## Dépendance de Dex sur Keycloak

Dex dépend de Keycloak pour fonctionner correctement. Si Dex démarre avant que Keycloak ne soit complètement opérationnel, Dex peut planter.

### Améliorations Proposées

1.  **Healthcheck pour Keycloak :**
    *   Ajouter un healthcheck à Keycloak dans le `docker-compose.yml`.
    *   Malheureusement, les commandes courantes comme `curl`, `wget`, `nc` ou `telnet` ne sont pas disponibles dans l'image Keycloak.
2.  **Script de Démarrage :**
    *   Remplacer la configuration `docker compose` par un script shell.
    *   Ce script pourrait vérifier l'état de Keycloak (par exemple, en essayant de se connecter à l'API) avant de démarrer Dex.

### Logs à Vérifier en Cas de Crash de Dex

*   **Logs de Keycloak :** Vérifiez si Keycloak a démarré correctement et s'il n'y a pas d'erreurs.
*   **Logs de Dex :** Vérifiez les erreurs de connexion à Keycloak ou les problèmes de configuration.

### Erreur Failed to resolve 'dex' 

* **Forcer le nom du réseau**: Le nom de réseau doit être forcé dans le docker compose pour que le docker dex soit dans le même.
* **Verifier l'id du conteneur**: L'id du conteneur sera l'adresse à utiliser par l'application dans le même réseau.

