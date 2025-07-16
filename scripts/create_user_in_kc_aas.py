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
TARGET_REALM = "KC_AAS"

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

def create_user(token, realm_name, user_data):
    """Crée un utilisateur dans un realm spécifique."""
    users_url = f"{KEYCLOAK_URL}/admin/realms/{realm_name}/users"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        # Vérifier si l'utilisateur existe déjà
        response = requests.get(
            f"{users_url}?username={user_data['username']}", 
            headers=headers, 
            verify=False
        )
        response.raise_for_status()
        existing_users = response.json()
        
        if existing_users:
            print(f"L'utilisateur '{user_data['username']}' existe déjà dans le realm '{realm_name}'.")
            return existing_users[0]['id']
        
        # Créer l'utilisateur
        response = requests.post(users_url, headers=headers, json=user_data, verify=False)
        
        if response.status_code == 201 or response.status_code == 204:
            # L'utilisateur a été créé avec succès, récupérer son ID
            user_id = None
            get_response = requests.get(
                f"{users_url}?username={user_data['username']}", 
                headers=headers, 
                verify=False
            )
            
            if get_response.status_code == 200:
                users = get_response.json()
                if users:
                    user_id = users[0]['id']
            
            print(f"Utilisateur '{user_data['username']}' créé avec succès dans le realm '{realm_name}'. ID: {user_id}")
            return user_id
        else:
            print(f"Erreur lors de la création de l'utilisateur: {response.status_code}")
            if hasattr(response, 'text'):
                print(f"Réponse: {response.text}")
            return None
    except Exception as e:
        print(f"Erreur lors de la création de l'utilisateur: {e}")
        return None

def set_user_password(token, realm_name, user_id, password, temporary=False):
    """Définit le mot de passe d'un utilisateur."""
    password_url = f"{KEYCLOAK_URL}/admin/realms/{realm_name}/users/{user_id}/reset-password"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "type": "password",
        "value": password,
        "temporary": temporary
    }
    
    try:
        response = requests.put(password_url, headers=headers, json=payload, verify=False)
        
        if response.status_code == 204:
            print(f"Mot de passe défini avec succès pour l'utilisateur (ID: {user_id}).")
            return True
        else:
            print(f"Erreur lors de la définition du mot de passe: {response.status_code}")
            if hasattr(response, 'text'):
                print(f"Réponse: {response.text}")
            return False
    except Exception as e:
        print(f"Erreur lors de la définition du mot de passe: {e}")
        return False

def get_or_create_group(token, realm_name, group_name):
    """Récupère ou crée un groupe dans un realm."""
    groups_url = f"{KEYCLOAK_URL}/admin/realms/{realm_name}/groups"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        # Vérifier si le groupe existe déjà
        response = requests.get(groups_url, headers=headers, verify=False)
        response.raise_for_status()
        groups = response.json()
        
        for group in groups:
            if group['name'] == group_name:
                print(f"Le groupe '{group_name}' existe déjà dans le realm '{realm_name}'. ID: {group['id']}")
                return group['id']
        
        # Créer le groupe s'il n'existe pas
        payload = {"name": group_name}
        response = requests.post(groups_url, headers=headers, json=payload, verify=False)
        
        if response.status_code == 201:
            # Le groupe a été créé, récupérer son ID
            response = requests.get(groups_url, headers=headers, verify=False)
            response.raise_for_status()
            groups = response.json()
            
            for group in groups:
                if group['name'] == group_name:
                    print(f"Groupe '{group_name}' créé avec succès dans le realm '{realm_name}'. ID: {group['id']}")
                    return group['id']
            
            print(f"Groupe créé mais impossible de récupérer son ID.")
            return None
        else:
            print(f"Erreur lors de la création du groupe: {response.status_code}")
            if hasattr(response, 'text'):
                print(f"Réponse: {response.text}")
            return None
    except Exception as e:
        print(f"Erreur lors de la récupération/création du groupe: {e}")
        return None

def add_user_to_group(token, realm_name, user_id, group_id):
    """Ajoute un utilisateur à un groupe."""
    group_url = f"{KEYCLOAK_URL}/admin/realms/{realm_name}/users/{user_id}/groups/{group_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # Vérifier si l'utilisateur est déjà dans le groupe
        groups_url = f"{KEYCLOAK_URL}/admin/realms/{realm_name}/users/{user_id}/groups"
        response = requests.get(groups_url, headers=headers, verify=False)
        response.raise_for_status()
        
        user_groups = response.json()
        for group in user_groups:
            if group['id'] == group_id:
                print(f"L'utilisateur (ID: {user_id}) est déjà membre du groupe (ID: {group_id}).")
                return True
        
        # Ajouter l'utilisateur au groupe
        response = requests.put(group_url, headers=headers, verify=False)
        
        if response.status_code == 204:
            print(f"Utilisateur (ID: {user_id}) ajouté au groupe (ID: {group_id}) avec succès.")
            return True
        else:
            print(f"Erreur lors de l'ajout de l'utilisateur au groupe: {response.status_code}")
            if hasattr(response, 'text'):
                print(f"Réponse: {response.text}")
            return False
    except Exception as e:
        print(f"Erreur lors de l'ajout de l'utilisateur au groupe: {e}")
        return False

def verify_user_exists(token, realm_name, username):
    """Vérifie si un utilisateur existe dans un realm."""
    users_url = f"{KEYCLOAK_URL}/admin/realms/{realm_name}/users?username={username}"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(users_url, headers=headers, verify=False)
        response.raise_for_status()
        
        users = response.json()
        if users:
            user = users[0]
            print(f"\n=== VÉRIFICATION DE L'UTILISATEUR ===")
            print(f"L'utilisateur '{username}' existe dans le realm '{realm_name}':")
            print(f"ID: {user['id']}")
            if 'email' in user:
                print(f"Email: {user['email']}")
            if 'firstName' in user and 'lastName' in user:
                print(f"Nom: {user['firstName']} {user['lastName']}")
            print(f"Activé: {user['enabled']}")
            
            # Vérifier les groupes
            groups_url = f"{KEYCLOAK_URL}/admin/realms/{realm_name}/users/{user['id']}/groups"
            groups_response = requests.get(groups_url, headers=headers, verify=False)
            
            if groups_response.status_code == 200:
                groups = groups_response.json()
                if groups:
                    group_names = [g['name'] for g in groups]
                    print(f"Groupes: {', '.join(group_names)}")
            
            return True
        else:
            print(f"L'utilisateur '{username}' n'existe pas dans le realm '{realm_name}'.")
            return False
    except Exception as e:
        print(f"Erreur lors de la vérification de l'existence de l'utilisateur: {e}")
        return False

if __name__ == "__main__":
    print("Création d'un utilisateur dans le realm KC_AAS...")
    print("Attente de 3 secondes pour s'assurer que Keycloak est prêt...")
    time.sleep(3)
    
    # 1. Obtenir un token d'administrateur
    token = get_admin_token()
    if not token:
        print("Impossible d'obtenir un token d'accès. Arrêt du script.")
        exit(1)
    
    # 2. Définir les données de l'utilisateur à créer
    username = "test1"
    email = "test1@example.com"
    password = "password"
    
    user_data = {
        "username": username,
        "email": email,
        "enabled": True,
        "firstName": "Test",
        "lastName": "User1",
        "emailVerified": True
    }
    
    # 3. Créer l'utilisateur dans KC_AAS
    user_id = create_user(token, TARGET_REALM, user_data)
    
    if user_id:
        # 4. Définir le mot de passe
        set_user_password(token, TARGET_REALM, user_id, password)
        
        # 5. Récupérer ou créer le groupe "users"
        group_id = get_or_create_group(token, TARGET_REALM, "users")
        
        if group_id:
            # 6. Ajouter l'utilisateur au groupe
            add_user_to_group(token, TARGET_REALM, user_id, group_id)
        
        # 7. Vérifier que l'utilisateur existe bien
        verify_user_exists(token, TARGET_REALM, username)
        
        print(f"\n✅ Utilisateur '{username}' créé avec succès dans le realm '{TARGET_REALM}'.")
        print(f"Vous pouvez maintenant vous connecter avec:")
        print(f"  - Nom d'utilisateur: {username}")
        print(f"  - Mot de passe: {password}")
        print(f"  - Realm: {TARGET_REALM}")
    else:
        print(f"\n❌ Échec de la création de l'utilisateur '{username}'.") 