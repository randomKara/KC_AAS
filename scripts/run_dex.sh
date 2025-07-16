#!/bin/bash

# ========================================================================
# Script de lancement de Dex en standalone
# ========================================================================
# 
# Ce script lance Dex (serveur OIDC) en tant que conteneur Docker 
# indépendant pour servir d'intermédiaire d'authentification pour 
# l'application Flask.
#
# CHOIX TECHNIQUES ET JUSTIFICATIONS :
# ========================================================================
#
# 1. LANCEMENT STANDALONE VS DOCKER COMPOSE
#    - Avantage : Contrôle granulaire du cycle de vie de Dex
#    - Avantage : Possibilité de lancer Dex uniquement quand nécessaire
#    - Avantage : Configuration plus flexible et explicite
#    - Avantage : Débogage plus facile (logs isolés)
#
# 2. UTILISATION DE DOCKER AU LIEU D'UNE INSTALLATION NATIVE
#    - Portabilité : Fonctionne sur n'importe quel système avec Docker
#    - Isolation : Pas de pollution de l'environnement hôte
#    - Versions : Contrôle précis de la version de Dex utilisée
#    - Maintenance : Pas de gestion des dépendances système
#
# 3. RÉSEAU BRIDGE PERSONALISE
#    - Permet la communication avec Keycloak via le réseau Docker
#    - Isolation réseau des autres conteneurs
#    - Résolution DNS automatique entre conteneurs
#
# 4. MONTAGE DE CONFIGURATION
#    - Configuration externalisée et modifiable sans rebuild
#    - Facilite les tests et le développement
#    - Permet la personnalisation selon l'environnement
#
# 5. GESTION DES DÉPENDANCES
#    - Attente active de Keycloak avant le démarrage
#    - Évite les erreurs de connexion au démarrage
#    - Robustesse face aux redémarrages de services
#
# ========================================================================

set -e  # Arrêt du script en cas d'erreur

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEX_IMAGE="ghcr.io/dexidp/dex:v2.37.0"
DEX_CONTAINER_NAME="kc_aas_dex"
DEX_CONFIG_PATH="$(dirname "$0")/../dex/config.yaml"
NETWORK_NAME="auth-network"
KEYCLOAK_URL="http://keycloak:8080"
MAX_WAIT_TIME=120  # 2 minutes maximum d'attente

echo -e "${BLUE}========================================================================${NC}"
echo -e "${BLUE}                    LANCEMENT DE DEX (Serveur OIDC)${NC}"
echo -e "${BLUE}========================================================================${NC}"
echo ""

# Fonction pour afficher les messages d'information
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Fonction pour afficher les messages de succès
success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Fonction pour afficher les messages d'avertissement
warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Fonction pour afficher les messages d'erreur
error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Vérification des prérequis
info "Vérification des prérequis..."

# Vérifier que Docker est installé et en cours d'exécution
if ! command -v docker &> /dev/null; then
    error "Docker n'est pas installé ou n'est pas dans le PATH"
    exit 1
fi

if ! docker info &> /dev/null; then
    error "Docker n'est pas en cours d'exécution"
    exit 1
fi

success "Docker est disponible et en cours d'exécution"

# Vérifier que le fichier de configuration existe
if [ ! -f "$DEX_CONFIG_PATH" ]; then
    error "Le fichier de configuration Dex n'existe pas : $DEX_CONFIG_PATH"
    exit 1
fi

success "Fichier de configuration Dex trouvé : $DEX_CONFIG_PATH"

# Vérifier si le réseau existe
if ! docker network ls | grep -q "$NETWORK_NAME"; then
    warning "Le réseau '$NETWORK_NAME' n'existe pas. Création en cours..."
    docker network create "$NETWORK_NAME" --driver bridge
    success "Réseau '$NETWORK_NAME' créé avec succès"
else
    info "Le réseau '$NETWORK_NAME' existe déjà"
fi

# Vérifier si un conteneur Dex existe déjà
if docker ps -a --format 'table {{.Names}}' | grep -q "$DEX_CONTAINER_NAME"; then
    warning "Un conteneur Dex existe déjà : $DEX_CONTAINER_NAME"
    info "Suppression du conteneur existant..."
    docker rm -f "$DEX_CONTAINER_NAME" &> /dev/null || true
    success "Conteneur existant supprimé"
fi

# Vérifier si Keycloak est accessible
info "Vérification de la disponibilité de Keycloak..."
wait_time=0
while [ $wait_time -lt $MAX_WAIT_TIME ]; do
    if docker exec -it $(docker ps --filter "name=keycloak" --format "{{.Names}}" | head -1) curl -s "$KEYCLOAK_URL/realms/KC_AAS" &> /dev/null; then
        success "Keycloak est accessible et le realm KC_AAS est disponible"
        break
    fi
    
    if [ $wait_time -eq 0 ]; then
        info "Attente de la disponibilité de Keycloak..."
    fi
    
    sleep 5
    wait_time=$((wait_time + 5))
    
    if [ $wait_time -ge $MAX_WAIT_TIME ]; then
        error "Timeout : Keycloak n'est pas accessible après $MAX_WAIT_TIME secondes"
        error "Assurez-vous que Keycloak est démarré avec 'docker compose up keycloak'"
        exit 1
    fi
done

# Option pour vérifier/créer automatiquement le client Dex (si Python disponible)
if command -v python3 &> /dev/null && [ -f "scripts/create_client_in_kc_aas.py" ]; then
    info "Python3 détecté - Vérification automatique du client Dex..."
    python3 scripts/create_client_in_kc_aas.py \
        --client-id "dex-client" \
        --client-secret "dex-client-secret" \
        --redirect-uris "http://localhost:5556/dex/callback" \
        --enable-standard-flow \
        --enable-direct-access &> /dev/null
    
    if [ $? -eq 0 ]; then
        success "Client dex-client vérifié/créé automatiquement"
    else
        warning "Impossible de créer automatiquement le client dex-client"
        info "Assurez-vous que le client existe dans Keycloak ou utilisez le script de démonstration"
    fi
else
    info "Python3 non disponible - Vérification manuelle du client Dex requise"
fi

# Lancement de Dex
info "Lancement du conteneur Dex..."
echo ""
info "Commande Docker exécutée :"
echo -e "${YELLOW}docker run -d \\"
echo "  --name $DEX_CONTAINER_NAME \\"
echo "  --network $NETWORK_NAME \\"
echo "  -p 5556:5556 \\"
echo "  -v \"$(readlink -f "$DEX_CONFIG_PATH"):/etc/dex/config.yaml:ro\" \\"
echo "  $DEX_IMAGE \\"
echo "  dex serve /etc/dex/config.yaml${NC}"
echo ""

docker run -d \
    --name "$DEX_CONTAINER_NAME" \
    --network "$NETWORK_NAME" \
    -p 5556:5556 \
    -v "$(readlink -f "$DEX_CONFIG_PATH"):/etc/dex/config.yaml:ro" \
    "$DEX_IMAGE" \
    dex serve /etc/dex/config.yaml

if [ $? -eq 0 ]; then
    success "Conteneur Dex démarré avec succès"
else
    error "Échec du démarrage du conteneur Dex"
    exit 1
fi

# Attendre que Dex soit prêt
info "Attente de la disponibilité de Dex..."
wait_time=0
while [ $wait_time -lt 60 ]; do
    if curl -s http://localhost:5556/dex/.well-known/openid-configuration &> /dev/null; then
        success "Dex est maintenant disponible !"
        break
    fi
    sleep 2
    wait_time=$((wait_time + 2))
    
    if [ $wait_time -ge 60 ]; then
        error "Timeout : Dex n'est pas disponible après 60 secondes"
        info "Vérification des logs du conteneur..."
        docker logs "$DEX_CONTAINER_NAME"
        exit 1
    fi
done

echo ""
echo -e "${GREEN}========================================================================${NC}"
echo -e "${GREEN}                            DEX EST PRÊT !${NC}"
echo -e "${GREEN}========================================================================${NC}"
echo ""
success "Dex (serveur OIDC) est maintenant en cours d'exécution"
echo ""
info "Informations de connexion :"
echo "  • URL de découverte OIDC : http://localhost:5556/dex/.well-known/openid-configuration"
echo "  • Interface d'authentification : http://localhost:5556/dex/auth"
echo "  • Nom du conteneur : $DEX_CONTAINER_NAME"
echo "  • Réseau Docker : $NETWORK_NAME"
echo ""
info "L'application Flask peut maintenant s'authentifier via Dex"
echo "  • Démarrez l'application Flask avec : docker compose up flask-app"
echo "  • Accédez à l'application : http://localhost:5000"
echo ""
info "Pour arrêter Dex :"
echo "  • docker stop $DEX_CONTAINER_NAME"
echo "  • docker rm $DEX_CONTAINER_NAME"
echo ""
info "Pour voir les logs de Dex :"
echo "  • docker logs -f $DEX_CONTAINER_NAME"
echo ""
warning "RAPPEL : Dex doit rester en cours d'exécution pour que l'authentification fonctionne"
echo "" 