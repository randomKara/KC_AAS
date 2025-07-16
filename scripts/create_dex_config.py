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
    
    # Paramètres Docker
    parser.add_argument("--docker-network", default="auth-network", help="Nom du réseau Docker à utiliser (optionnel, détecté automatiquement si non fourni)")
    
    return parser.parse_args()

def generate_random_secret(length=32):
    """Génère un secret aléatoire."""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def get_keycloak_registration_command(args, client_secret):
    """Génère la commande pour enregistrer le client dans Keycloak."""
    client_id = args.client_id or f"dex-{args.dex_name}"
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
    client_id = args.client_id or f"dex-{args.dex_name}"
    dex_issuer = args.dex_issuer_url or f"http://{args.dex_name}:{args.dex_port}"
    
    config = {
        "issuer": dex_issuer,
        "storage": {
            "type": args.storage_type
        },
        "web": {
            "http": f"{args.dex_host}:{args.dex_port}"
        },
        "oauth2": {
            "skipApprovalScreen": args.oauth_skip_approval_screen,
            "responseTypes": ["code", "token", "id_token"]
        },
        "connectors": 
            {
                "type": "oidc",
                "id": f"keycloak-{args.keycloak_realm}",
                "name": f"Keycloak {args.keycloak_realm}",
                "config": {
                    "issuer": f"{args.keycloak_url}/realms/{args.keycloak_realm}",
                    "clientID": client_id,
                    "clientSecret": client_secret,
                    "redirectURI": f"{dex_issuer}/callback",
                    "scopes": ["openid", "profile", "email", "groups"],
                    "insecureSkipVerify": True,  # À remplacer par false en production
                    "userIDKey": "sub",
                    "userNameKey": "preferred_username",
                    "claimMapping": {
                        "groups": "groups",
                        "name": "name",
                        "email": "email"
                    }
                }
            },
        "staticClients": []  # Peut être rempli avec des clients statiques si nécessaire
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
        config["storage"]["file"] = f"/etc/dex/dex-{args.dex_name}.db"
    
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
    print("# Enregistrez cette configuration dans un fichier config.yaml pour DEX:")
    print(yaml.dump(dex_config, default_flow_style=False))
    
    print("\n=== COMMANDES DOCKER ===")
    print("# Pour démarrer un conteneur DEX avec cette configuration:")
    print(f"docker run -d \\")
    print(f"  --name dex-{args.dex_name} \\")
    print(f"  --network {docker_network} \\")  # Ajout du réseau Docker
    print(f"  -p {args.dex_port}:{args.dex_port} \\")
    print(f"  -v /chemin/vers/config.yaml:/etc/dex/config.yaml \\")
    if args.dex_tls_cert and args.dex_tls_key:
        print(f"  -v /chemin/vers/cert:/etc/dex/tls.crt \\")
        print(f"  -v /chemin/vers/key:/etc/dex/tls.key \\")
    print(f"  quay.io/dexidp/dex:latest \\")
    print(f"  dex serve /etc/dex/config.yaml")
    
    print(f"\n# Note: Le réseau Docker '{docker_network}' sera utilisé pour la communication avec Keycloak.")
    print("# Si le réseau n'existe pas, créez-le avec: docker network create " + docker_network)
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 