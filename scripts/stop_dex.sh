#!/bin/bash

# ========================================================================
# Script d'arrêt de Dex
# ========================================================================
# 
# Ce script arrête proprement le conteneur Dex lancé en standalone
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
DEX_CONTAINER_NAME="kc_aas_dex"

echo -e "${BLUE}========================================================================${NC}"
echo -e "${BLUE}                        ARRÊT DE DEX${NC}"
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

# Vérifier si le conteneur existe
if ! docker ps -a --format 'table {{.Names}}' | grep -q "$DEX_CONTAINER_NAME"; then
    warning "Aucun conteneur Dex trouvé avec le nom : $DEX_CONTAINER_NAME"
    info "Le conteneur Dex n'est peut-être pas en cours d'exécution ou a été supprimé"
    exit 0
fi

# Vérifier si le conteneur est en cours d'exécution
if docker ps --format 'table {{.Names}}' | grep -q "$DEX_CONTAINER_NAME"; then
    info "Arrêt du conteneur Dex : $DEX_CONTAINER_NAME"
    docker stop "$DEX_CONTAINER_NAME"
    success "Conteneur Dex arrêté"
else
    info "Le conteneur Dex n'est pas en cours d'exécution"
fi

# Supprimer le conteneur
info "Suppression du conteneur Dex..."
docker rm "$DEX_CONTAINER_NAME" &> /dev/null || true
success "Conteneur Dex supprimé"

echo ""
success "Dex a été arrêté et supprimé avec succès"
echo ""
info "Pour relancer Dex, utilisez : ./scripts/run_dex.sh"
echo "" 