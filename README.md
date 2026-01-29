# Générateur de Factures Factur-X

Une application Flask moderne pour générer des factures électroniques au format Factur-X avec une interface Bootstrap élégante.

## 🚀 Fonctionnalités

- ✅ Interface web responsive avec Bootstrap 5
- ✅ Saisie complète des informations de facturation
- ✅ Calcul automatique des totaux HT, TVA et TTC
- ✅ Choix des taux de TVA (0%, 5.5%, 10%, 20%)
- ✅ Génération de PDF professionnel
- ✅ Support du format Factur-X (PDF + XML)
- ✅ Téléchargement automatique de la facture

## 📋 Prérequis

- Python 3.7+
- pip

## 🛠️ Installation

1. **Cloner ou télécharger le projet**
   ```bash
   cd FACTURRRRRR
   ```

2. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

3. **Lancer l'application**
   ```bash
   python app.py
   ```

4. **Ouvrir votre navigateur**
   Rendez-vous sur: `http://localhost:5000`

## 🎯 Utilisation

1. **Remplir les informations générales**
   - Date de facturation
   - Numéro de facture (optionnel - auto-généré)

2. **Saisir les informations de l'émetteur**
   - Raison sociale, adresse complète
   - SIRET et numéro de TVA (optionnels)

3. **Saisir les informations du destinataire**
   - Raison sociale, adresse complète
   - SIRET et numéro de TVA (optionnels)

4. **Ajouter les articles/prestations**
   - Description, quantité, prix unitaire HT
   - Choix du taux de TVA
   - Calcul automatique des totaux

5. **Générer la facture**
   - Cliquer sur "Générer la facture Factur-X"
   - Téléchargement automatique du PDF

## 📁 Structure du projet

```
FACTURRRRRR/
├── app.py                 # Application Flask principale
├── facturx_generator.py   # Générateur de documents Factur-X
├── requirements.txt       # Dépendances Python
├── templates/
│   └── invoice_form.html  # Interface utilisateur
└── generated_invoices/    # Dossier des factures générées
```

## 🎨 Interface

L'interface utilise Bootstrap 5 avec:
- Design moderne et responsive
- Dégradés colorés élégants
- Calcul en temps réel des totaux
- Icônes Font Awesome
- Messages de statut (succès/erreur)

## ⚙️ Fonctionnalités techniques

### Format Factur-X
- **PDF lisible** : Document traditionnel pour impression
- **XML embarqué** : Données structurées selon les standards européens
- **Conformité** : Respect des normes EN 16931 et UN/CEFACT

### Calculs automatiques
- Total HT par ligne
- TVA par ligne selon le taux choisi
- Totaux généraux (HT, TVA, TTC)

### Validation des données
- Champs obligatoires marqués
- Validation côté client et serveur
- Messages d'erreur explicites

## 🛡️ Sécurité

- Validation des entrées utilisateur
- Protection contre les injections
- Gestion des erreurs robuste

## 🔧 Personnalisation

Vous pouvez facilement personnaliser :
- **Styles CSS** : Modifier les couleurs et le design
- **Taux de TVA** : Ajouter d'autres taux dans le formulaire
- **Format PDF** : Personnaliser la mise en page dans `facturx_generator.py`
- **Champs** : Ajouter des champs supplémentaires selon vos besoins

## 📞 Support

Pour toute question ou amélioration, n'hésitez pas à créer une issue ou contribuer au projet.

---
**Note** : Cette application génère des documents au format Factur-X basic. Pour une conformité complète en production, des ajustements peuvent être nécessaires selon votre contexte d'utilisation.