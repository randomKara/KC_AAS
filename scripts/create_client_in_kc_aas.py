#!/usr/bin/env python
import os
import json
import time
import urllib3
import requests
import argparse
import sys

# Désactiver les avertissements liés aux certificats SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def parse_arguments():
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(description="Création d'un client dans Keycloak")
    
    # Paramètres de connexion à Keycloak
    parser.add_argument("--keycloak-url", default="http://localhost:8080", help="URL de Keycloak")
    parser.add_argument("--admin-user", default="admin", help="Nom d'utilisateur administrateur")
    parser.add_argument("--admin-password", default="admin", help="Mot de passe administrateur")
    parser.add_argument("--realm", default="KC_AAS", help="Realm cible")
    
    # Paramètres du client
    parser.add_argument("--client-id", required=True, help="ID du client à créer")
    parser.add_argument("--client-name", help="Nom du client (si différent de l'ID)")
    parser.add_argument("--public", action="store_true", help="Définit le client comme public (par défaut: confidentiel)")
    
    # URIs et origines
    parser.add_argument("--redirect-uris", nargs="+", default=["http://localhost:8000/*"], 
                      help="URIs de redirection (plusieurs valeurs séparées par des espaces)")
    parser.add_argument("--web-origins", nargs="+", default=["*"], 
                      help="Origines web autorisées (plusieurs valeurs séparées par des espaces)")
    parser.add_argument("--root-url", help="URL racine du client")
    parser.add_argument("--base-url", help="URL de base du client")
    
    # Flux d'authentification
    parser.add_argument("--enable-direct-access", action="store_true", default=True, 
                      help="Active les subventions d'accès direct")
    parser.add_argument("--enable-standard-flow", action="store_true", default=True, 
                      help="Active le flux standard")
    parser.add_argument("--enable-implicit-flow", action="store_true", 
                      help="Active le flux implicite")

    # Ajout de l'argument client-secret
    parser.add_argument("--client-secret", help="Secret du client")
    
    # Paramètres avancés
    parser.add_argument("--enable-service-accounts", action="store_true", 
                      help="Active les comptes de service")
    parser.add_argument("--enable-authorization", action="store_true", 
                      help="Active l'autorisation (RBAC)")
    parser.add_argument("--no-wait", action="store_true", 
                      help="Ne pas attendre la fin de la création du client")
    parser.add_argument("--quiet", action="store_true", 
                      help="Mode silencieux (affiche seulement le secret du client)")
    
    return parser.parse_args()

def get_admin_token(keycloak_url, admin_user, admin_password, quiet=False):
    """Obtient un token d'accès administrateur pour Keycloak."""
    token_url = f"{keycloak_url}/realms/master/protocol/openid-connect/token"
    payload = {
        "username": admin_user,
        "password": admin_password,
        "grant_type": "password",
        "client_id": "admin-cli"
    }
    
    try:
        response = requests.post(token_url, data=payload, verify=False)
        response.raise_for_status()
        if not quiet:
            print("Token d'administrateur obtenu avec succès.")
        return response.json()["access_token"]
    except Exception as e:
        print(f"Erreur lors de l'obtention du token: {e}")
        if hasattr(response, 'text'):
            print(f"Réponse: {response.text}")
        return None

def create_client(token, keycloak_url, realm_name, client_data, quiet=False):
    """Crée un client dans un realm spécifique."""
    clients_url = f"{keycloak_url}/admin/realms/{realm_name}/clients"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        # Vérifier si le client existe déjà
        response = requests.get(
            f"{clients_url}?clientId={client_data['clientId']}", 
            headers=headers, 
            verify=False
        )
        response.raise_for_status()
        existing_clients = response.json()
        
        if existing_clients:
            if not quiet:
                print(f"Le client '{client_data['clientId']}' existe déjà dans le realm '{realm_name}'.")
            return existing_clients[0]['id']
        
        # Créer le client
        response = requests.post(clients_url, headers=headers, json=client_data, verify=False)
        
        if response.status_code == 201 or response.status_code == 204:
            # Le client a été créé avec succès, récupérer son ID
            client_id = None
            get_response = requests.get(
                f"{clients_url}?clientId={client_data['clientId']}", 
                headers=headers, 
                verify=False
            )
            
            if get_response.status_code == 200:
                clients = get_response.json()
                if clients:
                    client_id = clients[0]['id']
            
            if not quiet:
                print(f"Client '{client_data['clientId']}' créé avec succès dans le realm '{realm_name}'. ID: {client_id}")
            return client_id
        else:
            print(f"Erreur lors de la création du client: {response.status_code}")
            if hasattr(response, 'text'):
                print(f"Réponse: {response.text}")
            return None
    except Exception as e:
        print(f"Erreur lors de la création du client: {e}")
        return None

def get_client_secret(token, keycloak_url, realm_name, client_id, quiet=False):
    """Récupère le secret d'un client."""
    secret_url = f"{keycloak_url}/admin/realms/{realm_name}/clients/{client_id}/client-secret"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(secret_url, headers=headers, verify=False)
        
        if response.status_code == 200:
            secret = response.json()['value']
            if not quiet:
                print(f"Secret du client récupéré avec succès.")
            return secret
        else:
            print(f"Erreur lors de la récupération du secret du client: {response.status_code}")
            if hasattr(response, 'text'):
                print(f"Réponse: {response.text}")
            return None
    except Exception as e:
        print(f"Erreur lors de la récupération du secret du client: {e}")
        return None

def regenerate_client_secret(token, keycloak_url, realm_name, client_id, quiet=False):
    """Régénère le secret d'un client."""
    secret_url = f"{keycloak_url}/admin/realms/{realm_name}/clients/{client_id}/client-secret"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(secret_url, headers=headers, verify=False)
        
        if response.status_code == 200:
            secret = response.json()['value']
            if not quiet:
                print(f"Secret du client régénéré avec succès.")
            return secret
        else:
            print(f"Erreur lors de la régénération du secret du client: {response.status_code}")
            if hasattr(response, 'text'):
                print(f"Réponse: {response.text}")
            return None
    except Exception as e:
        print(f"Erreur lors de la régénération du secret du client: {e}")
        return None

def verify_client_exists(token, keycloak_url, realm_name, client_id_value, quiet=False):
    """Vérifie si un client existe dans un realm."""
    clients_url = f"{keycloak_url}/admin/realms/{realm_name}/clients?clientId={client_id_value}"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(clients_url, headers=headers, verify=False)
        response.raise_for_status()
        
        clients = response.json()
        if clients:
            client = clients[0]
            if not quiet:
                print(f"\n=== VÉRIFICATION DU CLIENT ===")
                print(f"Le client '{client_id_value}' existe dans le realm '{realm_name}':")
                print(f"ID: {client['id']}")
                print(f"Nom: {client['name'] if 'name' in client else client_id_value}")
                print(f"Activé: {client['enabled']}")
                print(f"Type: {client['protocol']}")
                print(f"Access Type: {client['publicClient']}")
            
            # Récupérer et afficher le secret si c'est un client confidentiel
            secret = None
            if not client.get('publicClient', True):
                secret = get_client_secret(token, keycloak_url, realm_name, client['id'], quiet)
                if secret and not quiet:
                    print(f"Secret: {secret}")
            
            return True, secret
        else:
            if not quiet:
                print(f"Le client '{client_id_value}' n'existe pas dans le realm '{realm_name}'.")
            return False, None
    except Exception as e:
        print(f"Erreur lors de la vérification de l'existence du client: {e}")
        return False, None

def main():
    """Fonction principale du script."""
    # Analyser les arguments
    args = parse_arguments()
    
    # Afficher le message de démarrage
    if not args.quiet:
        print(f"Création d'un client dans le realm {args.realm}...")
    
    # Attendre avant de démarrer si besoin
    if not args.no_wait:
        if not args.quiet:
            print("Attente de 3 secondes pour s'assurer que Keycloak est prêt...")
        time.sleep(3)
    
    # 1. Obtenir un token d'administrateur
    token = get_admin_token(args.keycloak_url, args.admin_user, args.admin_password, args.quiet)
    if not token:
        print("Impossible d'obtenir un token d'accès. Arrêt du script.")
        return 1
    
    # 2. Définir les données du client à créer
    client_name = args.client_name or args.client_id
    
    client_data = {
        "clientId": args.client_id,
        "name": client_name,
        "enabled": True,
        "protocol": "openid-connect",
        "publicClient": args.public,
        "directAccessGrantsEnabled": args.enable_direct_access,
        "standardFlowEnabled": args.enable_standard_flow,
        "implicitFlowEnabled": args.enable_implicit_flow,
        "serviceAccountsEnabled": args.enable_service_accounts,
        "authorizationServicesEnabled": args.enable_authorization,
        "redirectUris": args.redirect_uris,
        "webOrigins": args.web_origins
    }
    
    # Ajouter les URLs racine et de base si fournies
    if args.root_url:
        client_data["rootUrl"] = args.root_url
    if args.base_url:
        client_data["baseUrl"] = args.base_url
    
    # Ajouter le secret si fourni et le client n'est pas public
    if args.client_secret and not client_data["publicClient"]:
        client_data["secret"] = args.client_secret
    
    # 3. Créer le client dans le realm cible
    client_uuid = create_client(token, args.keycloak_url, args.realm, client_data, args.quiet)
    
    if client_uuid:
        client_secret = None
        # 4. Si le client est confidentiel, récupérer son secret
        if not client_data["publicClient"]:
            client_secret = get_client_secret(token, args.keycloak_url, args.realm, client_uuid, args.quiet)
            if not client_secret:
                if not args.quiet:
                    print("Génération d'un nouveau secret...")
                client_secret = regenerate_client_secret(token, args.keycloak_url, args.realm, client_uuid, args.quiet)
        
        # 5. Vérifier que le client existe bien
        client_exists, _ = verify_client_exists(token, args.keycloak_url, args.realm, args.client_id, args.quiet)
        
        if not args.quiet:
            print(f"\n✅ Client '{args.client_id}' créé avec succès dans le realm '{args.realm}'.")
            if not client_data["publicClient"] and client_secret:
                print(f"Secret du client: {client_secret}")
        else:
            # En mode silencieux, juste afficher le secret (utile pour les scripts)
            if not client_data["publicClient"] and client_secret:
                print(client_secret)
        
        return 0
    else:
        if not args.quiet:
            print(f"\n❌ Échec de la création du client '{args.client_id}'.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 