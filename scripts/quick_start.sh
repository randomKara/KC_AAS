#!/bin/bash

# ========================================================================
# Script de démarrage rapide KC_AAS - Proof of Work
# ========================================================================
# 
# Ce script lance une démonstration complète du système KC_AAS en utilisant
# tous les scripts Python disponibles pour automatiser la configuration.
# 
# Il s'agit d'un wrapper simplifié autour du script demo_proof_of_work.py
# 
# ========================================================================

set -e

# Couleurs pour les messages
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================================================${NC}"
echo -e "${BLUE}                   KC_AAS - DÉMARRAGE RAPIDE${NC}"
echo -e "${BLUE}                     Proof of Work Complet${NC}"
echo -e "${BLUE}========================================================================${NC}"
echo ""

# Vérifier si Python3 est disponible
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERREUR]${NC} Python3 n'est pas installé"
    echo "Veuillez installer Python3 pour utiliser ce script"
    exit 1
fi

# Vérifier si le script de démonstration existe
if [ ! -f "scripts/demo_proof_of_work.py" ]; then
    echo -e "${RED}[ERREUR]${NC} Script de démonstration non trouvé"
    exit 1
fi

echo -e "${BLUE}[INFO]${NC} Vérification des dépendances Python..."

# Installer les dépendances si nécessaire
if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}[INFO]${NC} Installation des dépendances Python..."
    pip3 install -r requirements.txt --quiet --user || {
        echo -e "${YELLOW}[WARNING]${NC} Impossible d'installer automatiquement les dépendances"
        echo "Installez manuellement avec: pip3 install -r requirements.txt"
    }
fi

echo -e "${GREEN}[INFO]${NC} Lancement de la démonstration complète..."
echo ""

# Lancer le script de démonstration avec les arguments fournis
python3 scripts/demo_proof_of_work.py "$@"

echo ""
echo -e "${BLUE}========================================================================${NC}"
echo -e "${BLUE}                        DÉMARRAGE RAPIDE TERMINÉ${NC}"
echo -e "${BLUE}========================================================================${NC}" 