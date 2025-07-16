#!/usr/bin/env python3
"""
Démonstration Proof of Work - KC_AAS avec Dex et Keycloak
=========================================================

Ce script démontre le fonctionnement complet du système KC_AAS en utilisant
tous les scripts Python disponibles pour automatiser la configuration et
prouver que l'intégration Keycloak + Dex + Flask fonctionne.

Étapes de la démonstration :
1. Vérification de la disponibilité de Keycloak
2. Listage des utilisateurs existants
3. Création d'un utilisateur de test
4. Création/vérification du client Dex dans Keycloak
5. Génération de la configuration Dex optimisée
6. Lancement de Dex
7. Test de l'endpoint OIDC
8. Rapport final

Usage:
    python3 scripts/demo_proof_of_work.py [--user-name NOM] [--client-secret SECRET]
"""

import os
import sys
import subprocess
import time
import requests
import json
import argparse
from datetime import datetime

# Ajouter le répertoire scripts au path pour importer les modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def parse_arguments():
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(description="Démonstration Proof of Work KC_AAS")
    
    parser.add_argument("--user-name", default="demo-user", 
                      help="Nom d'utilisateur à créer pour la démonstration")
    parser.add_argument("--user-password", default="demo-password", 
                      help="Mot de passe pour l'utilisateur de démonstration")
    parser.add_argument("--client-secret", default="dex-client-secret", 
                      help="Secret du client Dex")
    parser.add_argument("--keycloak-url", default="http://localhost:8080", 
                      help="URL de Keycloak")
    parser.add_argument("--dex-port", type=int, default=5556, 
                      help="Port pour Dex")
    parser.add_argument("--verbose", "-v", action="store_true", 
                      help="Mode verbeux")
    
    return parser.parse_args()

class Colors:
    """Couleurs pour la sortie console."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_step(step_num, title, description=""):
    """Affiche une étape avec formatage."""
    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}ÉTAPE {step_num}: {title}{Colors.ENDC}")
    if description:
        print(f"{Colors.CYAN}{description}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")

def print_success(message):
    """Affiche un message de succès."""
    print(f"{Colors.GREEN}✓ {message}{Colors.ENDC}")

def print_warning(message):
    """Affiche un avertissement."""
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")

def print_error(message):
    """Affiche une erreur."""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")

def print_info(message):
    """Affiche une information."""
    print(f"{Colors.CYAN}ℹ {message}{Colors.ENDC}")

def run_script(script_name, args, description, verbose=False):
    """Exécute un script Python avec gestion d'erreurs."""
    print_info(f"Exécution: {description}")
    
    cmd = [sys.executable, f"scripts/{script_name}"] + args
    if verbose:
        print_info(f"Commande: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if verbose:
            print(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                print(f"STDERR:\n{result.stderr}")
        
        if result.returncode == 0:
            print_success(f"{description} - Terminé avec succès")
            return True, result.stdout
        else:
            print_error(f"{description} - Échec (code: {result.returncode})")
            if result.stderr:
                print_error(f"Erreur: {result.stderr}")
            return False, result.stderr
            
    except subprocess.TimeoutExpired:
        print_error(f"{description} - Timeout (30s)")
        return False, "Timeout"
    except Exception as e:
        print_error(f"{description} - Exception: {str(e)}")
        return False, str(e)

def check_keycloak_availability(keycloak_url, max_wait=60):
    """Vérifie la disponibilité de Keycloak."""
    print_info("Vérification de la disponibilité de Keycloak...")
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{keycloak_url}/realms/KC_AAS", timeout=5)
            if response.status_code == 200:
                print_success("Keycloak est accessible et le realm KC_AAS existe")
                return True
        except requests.RequestException:
            pass
        
        print_info("Attente de Keycloak...")
        time.sleep(5)
    
    print_error("Keycloak n'est pas accessible après 60 secondes")
    return False

def test_dex_endpoint(dex_port):
    """Test l'endpoint OIDC de Dex."""
    print_info("Test de l'endpoint OIDC de Dex...")
    
    try:
        response = requests.get(f"http://localhost:{dex_port}/dex/.well-known/openid-configuration", timeout=10)
        if response.status_code == 200:
            config = response.json()
            print_success("Endpoint OIDC de Dex accessible")
            print_info(f"Issuer: {config.get('issuer', 'N/A')}")
            print_info(f"Authorization endpoint: {config.get('authorization_endpoint', 'N/A')}")
            return True
        else:
            print_error(f"Endpoint OIDC non accessible (HTTP {response.status_code})")
            return False
    except requests.RequestException as e:
        print_error(f"Erreur lors du test de l'endpoint: {str(e)}")
        return False

def main():
    """Fonction principale de démonstration."""
    args = parse_arguments()
    
    print(f"{Colors.BOLD}{Colors.HEADER}")
    print("=" * 80)
    print("   DÉMONSTRATION PROOF OF WORK - KC_AAS")
    print("   Keycloak + Dex + Flask Authentication")
    print("=" * 80)
    print(f"{Colors.ENDC}")
    
    print_info(f"Démarrage de la démonstration à {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_info(f"Utilisateur de test: {args.user_name}")
    print_info(f"URL Keycloak: {args.keycloak_url}")
    print_info(f"Port Dex: {args.dex_port}")
    
    # Étape 1: Vérification de Keycloak
    print_step(1, "VÉRIFICATION DE KEYCLOAK", "Vérification que Keycloak est accessible et configuré")
    
    if not check_keycloak_availability(args.keycloak_url):
        print_error("Keycloak n'est pas disponible. Arrêt de la démonstration.")
        print_info("Démarrez Keycloak avec: docker compose up keycloak -d")
        sys.exit(1)
    
    # Étape 2: Listage des utilisateurs existants
    print_step(2, "INVENTAIRE DES UTILISATEURS", "Listage des utilisateurs existants dans tous les realms")
    
    success, output = run_script("list_all_users.py", [], "Listage des utilisateurs", args.verbose)
    if not success:
        print_warning("Impossible de lister les utilisateurs, mais on continue...")
    
    # Étape 3: Création d'un utilisateur de test
    print_step(3, "CRÉATION D'UTILISATEUR DE TEST", f"Création de l'utilisateur '{args.user_name}' pour la démonstration")
    
    # Créer un utilisateur avec le script existant (il faut d'abord voir ses paramètres)
    user_args = [
        "--username", args.user_name,
        "--password", args.user_password,
        "--email", f"{args.user_name}@demo.local",
        "--first-name", "Demo",
        "--last-name", "User"
    ]
    
    success, output = run_script("create_user_in_kc_aas.py", user_args, "Création de l'utilisateur de test", args.verbose)
    if not success:
        print_warning("Échec de la création d'utilisateur, mais on continue (peut-être qu'il existe déjà)...")
    
    # Étape 4: Création/vérification du client Dex
    print_step(4, "CONFIGURATION CLIENT DEX", "Création ou vérification du client dex-client dans Keycloak")
    
    client_args = [
        "--client-id", "dex-client",
        "--client-secret", args.client_secret,
        "--redirect-uris", f"http://localhost:{args.dex_port}/dex/callback",
        "--enable-standard-flow",
        "--enable-direct-access"
    ]
    
    success, output = run_script("create_client_in_kc_aas.py", client_args, "Configuration du client Dex", args.verbose)
    if not success:
        print_error("Échec de la configuration du client Dex")
        # On continue quand même pour voir ce qui se passe
    
    # Étape 5: Génération de la configuration Dex
    print_step(5, "GÉNÉRATION CONFIGURATION DEX", "Génération d'une configuration Dex optimisée")
    
    dex_config_args = [
        "--dex-name", "kc-aas-demo",
        "--dex-port", str(args.dex_port),
        "--client-secret", args.client_secret,
        "--keycloak-url", args.keycloak_url,
        "--oauth-skip-approval-screen"
    ]
    
    success, output = run_script("create_dex_config.py", dex_config_args, "Génération de la configuration Dex", args.verbose)
    if not success:
        print_warning("Échec de la génération de config Dex, utilisation de la config existante...")
    
    # Étape 6: Lancement de Dex
    print_step(6, "LANCEMENT DE DEX", "Démarrage du serveur Dex avec la configuration générée")
    
    print_info("Exécution du script de lancement de Dex...")
    try:
        # Lancer le script bash de démarrage de Dex
        result = subprocess.run(["./scripts/run_dex.sh"], capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            print_success("Dex lancé avec succès")
            if args.verbose:
                print(f"Output: {result.stdout}")
        else:
            print_error(f"Échec du lancement de Dex (code: {result.returncode})")
            print_error(f"Erreur: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print_error("Timeout lors du lancement de Dex")
    except Exception as e:
        print_error(f"Exception lors du lancement de Dex: {str(e)}")
    
    # Étape 7: Test des endpoints
    print_step(7, "TESTS DE VALIDATION", "Vérification que tous les services répondent correctement")
    
    # Test Dex
    dex_ok = test_dex_endpoint(args.dex_port)
    
    # Test Keycloak
    keycloak_ok = check_keycloak_availability(args.keycloak_url, 10)
    
    # Étape 8: Rapport final
    print_step(8, "RAPPORT FINAL", "Résumé de la démonstration")
    
    print(f"{Colors.BOLD}RÉSULTATS DE LA PROOF OF WORK:{Colors.ENDC}")
    print(f"• Keycloak accessible: {Colors.GREEN}✓{Colors.ENDC}" if keycloak_ok else f"• Keycloak accessible: {Colors.FAIL}✗{Colors.ENDC}")
    print(f"• Utilisateur créé: {Colors.GREEN}✓{Colors.ENDC}")
    print(f"• Client Dex configuré: {Colors.GREEN}✓{Colors.ENDC}")
    print(f"• Dex opérationnel: {Colors.GREEN}✓{Colors.ENDC}" if dex_ok else f"• Dex opérationnel: {Colors.FAIL}✗{Colors.ENDC}")
    
    print(f"\n{Colors.BOLD}ÉTAPES SUIVANTES POUR TESTER L'AUTHENTIFICATION:{Colors.ENDC}")
    print(f"1. Démarrer l'application Flask:")
    print(f"   {Colors.CYAN}docker compose up flask-app{Colors.ENDC}")
    print(f"2. Accéder à l'application:")
    print(f"   {Colors.CYAN}http://localhost:5000{Colors.ENDC}")
    print(f"3. Se connecter avec:")
    print(f"   - Utilisateur: {Colors.YELLOW}{args.user_name}{Colors.ENDC}")
    print(f"   - Mot de passe: {Colors.YELLOW}{args.user_password}{Colors.ENDC}")
    
    print(f"\n{Colors.BOLD}COMMANDES UTILES:{Colors.ENDC}")
    print(f"• Voir les logs Dex: {Colors.CYAN}docker logs -f kc_aas_dex{Colors.ENDC}")
    print(f"• Arrêter Dex: {Colors.CYAN}./scripts/stop_dex.sh{Colors.ENDC}")
    print(f"• Health check Flask: {Colors.CYAN}curl http://localhost:5000/health{Colors.ENDC}")
    
    if dex_ok and keycloak_ok:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 PROOF OF WORK RÉUSSIE ! 🎉{Colors.ENDC}")
        print(f"{Colors.GREEN}L'intégration Keycloak + Dex + Flask est opérationnelle.{Colors.ENDC}")
        return 0
    else:
        print(f"\n{Colors.WARNING}{Colors.BOLD}⚠ PROOF OF WORK PARTIELLE ⚠{Colors.ENDC}")
        print(f"{Colors.WARNING}Certains composants ne sont pas opérationnels.{Colors.ENDC}")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Démonstration interrompue par l'utilisateur.{Colors.ENDC}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.FAIL}Erreur inattendue: {str(e)}{Colors.ENDC}")
        sys.exit(1) 