#!/usr/bin/env python
import os
import json
import time
import urllib3
import requests

# Désactiver les avertissements liés aux certificats SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
KEYCLOAK_URL = "http://localhost:8080"
KEYCLOAK_ADMIN_USER = "admin"
KEYCLOAK_ADMIN_PASSWORD = "admin"

def get_admin_token():
    """Obtient un token d'accès administrateur pour Keycloak."""
    token_url = f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token"
    payload = {
        "username": KEYCLOAK_ADMIN_USER,
        "password": KEYCLOAK_ADMIN_PASSWORD,
        "grant_type": "password",
        "client_id": "admin-cli"
    }
    
    try:
        response = requests.post(token_url, data=payload, verify=False)
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        print(f"Erreur lors de l'obtention du token: {e}")
        if hasattr(response, 'text'):
            print(f"Réponse: {response.text}")
        return None

def get_realms(token):
    """Liste tous les realms disponibles."""
    realms_url = f"{KEYCLOAK_URL}/admin/realms"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(realms_url, headers=headers, verify=False)
        response.raise_for_status()
        realms = response.json()
        
        print("\n=== REALMS DISPONIBLES ===")
        for realm in realms:
            print(f"- {realm['realm']} (ID: {realm['id']})")
        return realms
    except Exception as e:
        print(f"Erreur lors de la récupération des realms: {e}")
        if hasattr(response, 'text'):
            print(f"Réponse: {response.text}")
        return []

def list_users_in_realm(token, realm_name):
    """Liste tous les utilisateurs dans un realm spécifique."""
    users_url = f"{KEYCLOAK_URL}/admin/realms/{realm_name}/users"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(users_url, headers=headers, verify=False)
        response.raise_for_status()
        users = response.json()
        
        if not users:
            print(f"Aucun utilisateur trouvé dans le realm {realm_name}")
            return []
        
        print(f"\n=== UTILISATEURS DU REALM {realm_name} ===")
        for user in users:
            print(f"ID: {user['id']}")
            print(f"Username: {user['username']}")
            if 'email' in user:
                print(f"Email: {user.get('email', 'Non défini')}")
            if 'firstName' in user or 'lastName' in user:
                print(f"Nom: {user.get('firstName', '')} {user.get('lastName', '')}")
            print(f"Activé: {user.get('enabled', False)}")
            
            # Récupérer les groupes de l'utilisateur
            try:
                user_groups = get_user_groups(token, realm_name, user['id'])
                if user_groups:
                    print(f"Groupes: {', '.join([g['name'] for g in user_groups])}")
            except Exception as e:
                print(f"Erreur lors de la récupération des groupes: {e}")
            
            print("---")
        
        print(f"Total: {len(users)} utilisateur(s) dans le realm {realm_name}")
        return users
    except Exception as e:
        print(f"Erreur lors de la récupération des utilisateurs dans {realm_name}: {e}")
        return []

def get_user_groups(token, realm_name, user_id):
    """Récupère les groupes d'un utilisateur."""
    groups_url = f"{KEYCLOAK_URL}/admin/realms/{realm_name}/users/{user_id}/groups"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(groups_url, headers=headers, verify=False)
        response.raise_for_status()
        return response.json()
    except:
        return []

def list_groups_in_realm(token, realm_name):
    """Liste tous les groupes dans un realm spécifique."""
    groups_url = f"{KEYCLOAK_URL}/admin/realms/{realm_name}/groups"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(groups_url, headers=headers, verify=False)
        response.raise_for_status()
        groups = response.json()
        
        if not groups:
            print(f"Aucun groupe trouvé dans le realm {realm_name}")
            return
        
        print(f"\n=== GROUPES DU REALM {realm_name} ===")
        for group in groups:
            print(f"- {group['name']} (ID: {group['id']})")
            
            # Récupérer les membres du groupe
            members_url = f"{KEYCLOAK_URL}/admin/realms/{realm_name}/groups/{group['id']}/members"
            members_response = requests.get(members_url, headers=headers, verify=False)
            
            if members_response.status_code == 200:
                members = members_response.json()
                if members:
                    print("  Membres:")
                    for member in members:
                        print(f"  * {member['username']}")
                else:
                    print("  Aucun membre")
            else:
                print(f"  Erreur lors de la récupération des membres: {members_response.status_code}")
    except Exception as e:
        print(f"Erreur lors de la récupération des groupes dans {realm_name}: {e}")

if __name__ == "__main__":
    print("Diagnostic Keycloak - Liste de tous les utilisateurs dans tous les realms")
    print("Attente de 3 secondes pour s'assurer que Keycloak est prêt...")
    time.sleep(3)
    
    # Obtenir un token d'accès administrateur
    token = get_admin_token()
    if not token:
        print("Impossible d'obtenir un token d'accès. Arrêt du script.")
        exit(1)
    
    # Récupérer tous les realms
    realms = get_realms(token)
    
    # Pour chaque realm, lister les utilisateurs et les groupes
    for realm in realms:
        realm_name = realm['realm']
        print(f"\n--- Informations pour le realm: {realm_name} ---")
        list_users_in_realm(token, realm_name)
        list_groups_in_realm(token, realm_name)
    
    print("\n=== RÉSUMÉ ===")
    print("Tous les utilisateurs de tous les realms ont été listés.")
    print("Vous pouvez maintenant voir clairement quels utilisateurs existent dans chaque realm.") 