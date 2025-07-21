#!/usr/bin/env python
import argparse
import json
import os
import random
import string
import sys
import yaml
import subprocess

def parse_arguments():
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(description="Génération de configuration pour DEX et enregistrement dans Keycloak")
    
    # Paramètres DEX
    parser.add_argument("--dex-name", required=True, help="Nom du broker DEX (utilisé pour les identifiants)")
    parser.add_argument("--dex-port", type=int, default=5556, help="Port d'écoute pour DEX")
    parser.add_argument("--dex-host", default="0.0.0.0", help="Hôte d'écoute pour DEX")
    parser.add_argument("--dex-issuer-url", help="URL publique de DEX (par défaut: http://HOSTNAME:PORT)")
    parser.add_argument("--dex-tls-cert", help="Chemin vers le certificat TLS (optionnel)")
    parser.add_argument("--dex-tls-key", help="Chemin vers la clé TLS (optionnel)")
    
    # Paramètres Keycloak (IdP)
    parser.add_argument("--keycloak-url", default="http://localhost:8080", help="URL de Keycloak")
    parser.add_argument("--keycloak-realm", default="KC_AAS", help="Realm Keycloak")
    parser.add_argument("--keycloak-admin-user", default="admin", help="Utilisateur admin Keycloak")
    parser.add_argument("--keycloak-admin-password", default="admin", help="Mot de passe admin Keycloak")
    
    # Paramètres du client
    parser.add_argument("--client-id", help="ID du client (par défaut: dex-HOSTNAME)")
    parser.add_argument("--client-secret", help="Secret du client (généré aléatoirement si non fourni)")
    
    # Paramètres de sécurité supplémentaires
    parser.add_argument("--oauth-skip-approval-screen", action="store_true", help="Sauter l'écran d'approbation OAuth")
    parser.add_argument("--session-expiry", default="24h", help="Durée d'expiration de session (ex: 24h, 30m)")
    parser.add_argument("--storage-type", default="memory", choices=["memory", "sqlite3", "postgres", "mysql"], 
                     help="Type de stockage pour DEX")
    parser.add_argument("--storage-config", help="Configuration JSON pour le stockage (selon le type)")
    
    # Nouveaux paramètres pour staticClients
    parser.add_argument("--static-client-id", help="ID du client statique (ex: flask-app)")
    parser.add_argument("--static-client-name", help="Nom du client statique (ex: Flask App)")
    parser.add_argument("--static-client-secret", help="Secret du client statique")
    parser.add_argument("--static-client-redirect-uris", nargs='+', help="URIs de redirection pour le client statique")
    
    # Paramètres de logging
    parser.add_argument("--log-level", default="debug", choices=["debug", "info", "warn", "error"], help="Niveau de log DEX")
    parser.add_argument("--log-format", default="text", choices=["text", "json"], help="Format des logs DEX")
    
    # Paramètres de base de données de mots de passe
    parser.add_argument("--enable-password-db", action="store_true", help="Activer la base de données de mots de passe locale")
    
    # Paramètres OAuth2 avancés
    parser.add_argument("--oauth-response-types", nargs='+', default=["code", "token", "id_token"], 
                     help="Types de réponse OAuth2 supportés")
    
    # Paramètres de mapping des claims
    parser.add_argument("--claim-groups", default="groups", help="Claim pour les groupes")
    parser.add_argument("--claim-username", default="preferred_username", help="Claim pour le nom d'utilisateur")
    parser.add_argument("--claim-email", default="email", help="Claim pour l'email")
    parser.add_argument("--claim-name", default="name", help="Claim pour le nom complet")
    
    # Paramètres Docker
    parser.add_argument("--docker-network", default="auth-network", help="Nom du réseau Docker à utiliser (optionnel, détecté automatiquement si non fourni)")
    
    # Paramètres de sortie
    parser.add_argument("--file", help="Fichier de sortie pour sauvegarder la configuration YAML (ex: dex/config.yaml)")
    
    return parser.parse_args()

def generate_random_secret(length=32):
    """Génère un secret aléatoire."""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def get_keycloak_registration_command(args, client_secret):
    """Génère la commande pour enregistrer le client dans Keycloak."""
    client_id = args.client_id or args.dex_name
    dex_issuer = args.dex_issuer_url or f"http://{args.dex_name}:{args.dex_port}"
    redirect_uris = [
        f"{dex_issuer}/callback",
        f"{dex_issuer}/login/callback"
    ]

    formatted_uris = ""
    for uri in redirect_uris:
        formatted_uris += f'"{uri}" '
    formatted_uris = formatted_uris.strip()

    cmd = [
        "python3 create_client_in_kc_aas.py",
        f"--client-id {client_id}",
        f"--client-name \"DEX Broker {args.dex_name}\"",
        f"--redirect-uris {formatted_uris}",
        f"--root-url \"{dex_issuer}\"",
        f"--base-url \"{dex_issuer}\"",
        f"--keycloak-url \"{args.keycloak_url}\"",
        f"--admin-user \"{args.keycloak_admin_user}\"",
        f"--admin-password \"{args.keycloak_admin_password}\"",
        f"--realm \"{args.keycloak_realm}\""
    ]
    
    # Si un secret est fourni, utiliser l'option --quiet pour juste afficher le nouveau secret
    cmd.append("--quiet")

    if client_secret:
        cmd.append(f"--client-secret \"{client_secret}\"")
    
    return " \\\n    ".join(cmd)

def generate_dex_config(args, client_secret):
    """Génère la configuration DEX basée sur les arguments fournis."""
    client_id = args.client_id or args.dex_name
    dex_issuer = args.dex_issuer_url or f"http://{args.dex_name}:{args.dex_port}"
    
    config = {
        "issuer": dex_issuer,
        "storage": {
            "type": args.storage_type
        },
        "web": {
            "http": f"{args.dex_host}:{args.dex_port}"
        }
    }
    
    # Ajouter staticClients si configuré
    static_clients = []
    if args.static_client_id:
        static_client = {
            "id": args.static_client_id,
            "name": args.static_client_name or args.static_client_id.replace('-', ' ').title(),
            "secret": args.static_client_secret or generate_random_secret()
        }
        if args.static_client_redirect_uris:
            static_client["redirectURIs"] = args.static_client_redirect_uris
        static_clients.append(static_client)
    
    config["staticClients"] = static_clients
    
    # Configuration des connectors (toujours une liste)
    connectors = [
        {
            "type": "oidc",
            "id": f"keycloak",
            "name": f"Keycloak",
            "config": {
                "issuer": f"{args.keycloak_url}/realms/{args.keycloak_realm}",
                "clientID": client_id,
                "clientSecret": client_secret,
                "redirectURI": f"{dex_issuer}/callback",
                "insecureSkipVerify": True,
                "claimMapping": {
                    "groups": args.claim_groups,
                    "username": args.claim_username,
                    "email": args.claim_email,
                    "name": args.claim_name
                }
            }
        }
    ]
    config["connectors"] = connectors
    
    # Configuration enablePasswordDB
    config["enablePasswordDB"] = args.enable_password_db
    
    # Configuration OAuth2
    config["oauth2"] = {
        "responseTypes": args.oauth_response_types,
        "skipApprovalScreen": args.oauth_skip_approval_screen
    }
    
    # Configuration des logs
    config["logger"] = {
        "level": args.log_level,
        "format": args.log_format
    }
    
    # Ajouter la configuration TLS si fournie
    if args.dex_tls_cert and args.dex_tls_key:
        config["web"]["https"] = f"{args.dex_host}:{args.dex_port}"
        config["web"]["tlsCert"] = args.dex_tls_cert
        config["web"]["tlsKey"] = args.dex_tls_key
        del config["web"]["http"]  # Supprimer la config HTTP si HTTPS est activé
    
    # Ajouter la configuration de stockage supplémentaire si fournie
    if args.storage_config:
        try:
            storage_config = json.loads(args.storage_config)
            config["storage"].update(storage_config)
        except json.JSONDecodeError:
            print("⚠️ Erreur: La configuration de stockage fournie n'est pas un JSON valide.")
    
    # Configuration supplémentaire pour des types de stockage spécifiques
    if args.storage_type == "sqlite3" and "file" not in config["storage"]:
        config["storage"]["file"] = f"/etc/dex/{args.dex_name}.db"
    
    return config

def main():
    args = parse_arguments()
    
    # Détecter ou utiliser le réseau Docker fourni
    docker_network = args.docker_network # Use directly the provided network

    # Générer ou utiliser le secret client fourni
    client_secret = args.client_secret or generate_random_secret()
    
    # Générer la configuration DEX
    dex_config = generate_dex_config(args, client_secret)
    
    # Générer la commande d'enregistrement Keycloak
    keycloak_cmd = get_keycloak_registration_command(args, client_secret)
    
    # Afficher les résultats
    print("\n=== COMMANDE D'ENREGISTREMENT KEYCLOAK ===")
    print(f"# Exécutez cette commande pour enregistrer le client dans Keycloak:")
    print(keycloak_cmd)
    print("\n# Le secret du client sera affiché après l'exécution de la commande et sera utilisé dans la configuration DEX")
    print(f"# Si vous souhaitez utiliser un secret spécifique, ajoutez-le manuellement à la configuration DEX.")
    
    print("\n=== CONFIGURATION DEX ===")
    
    # Sauvegarder dans un fichier si spécifié
    if args.file:
        # Créer le répertoire parent si nécessaire
        output_dir = os.path.dirname(args.file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"# Répertoire créé: {output_dir}")
        
        # Écrire la configuration dans le fichier
        with open(args.file, 'w') as f:
            yaml.dump(dex_config, f, default_flow_style=False)
        print(f"# Configuration DEX sauvegardée dans: {args.file}")
        
        # Mettre à jour les commandes Docker pour utiliser le bon chemin
        config_volume_path = os.path.abspath(args.file)
        print(f"\n# Pour démarrer DEX avec cette configuration:")
        print(f"docker run -d \\")
        print(f"  --name {args.dex_name} \\")
        print(f"  --network {docker_network} \\")
        print(f"  -p {args.dex_port}:{args.dex_port} \\")
        print(f"  -v {config_volume_path}:/etc/dex/config.yaml \\")
        if args.dex_tls_cert and args.dex_tls_key:
            print(f"  -v /chemin/vers/cert:/etc/dex/tls.crt \\")
            print(f"  -v /chemin/vers/key:/etc/dex/tls.key \\")
        print(f"  ghcr.io/dexidp/dex:v2.37.0 \\")
        print(f"  dex serve /etc/dex/config.yaml")
    else:
        print("# Enregistrez cette configuration dans un fichier config.yaml pour DEX:")
        print(yaml.dump(dex_config, default_flow_style=False))
    
    if not args.file:
        print("\n=== COMMANDES DOCKER ===")
        print("# Pour démarrer un conteneur DEX avec cette configuration:")
        print(f"docker run -d \\")
        print(f"  --name {args.dex_name} \\")
        print(f"  --network {docker_network} \\")
        print(f"  -p {args.dex_port}:{args.dex_port} \\")
        print(f"  -v /chemin/vers/config.yaml:/etc/dex/config.yaml \\")
        if args.dex_tls_cert and args.dex_tls_key:
            print(f"  -v /chemin/vers/cert:/etc/dex/tls.crt \\")
            print(f"  -v /chemin/vers/key:/etc/dex/tls.key \\")
        print(f"  ghcr.io/dexidp/dex:v2.37.0 \\")
        print(f"  dex serve /etc/dex/config.yaml")
    
    print(f"\n# Note: Le réseau Docker '{docker_network}' sera utilisé pour la communication avec Keycloak.")
    print("# Si le réseau n'existe pas, créez-le avec: docker network create " + docker_network)

    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 