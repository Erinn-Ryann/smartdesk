# Frontend SmartDesk
npm install && npm run dev   # http://localhost:5173 (backend sur :8000)
# SmartDesk : prototype de relation client avec assistant IA

Prototype réalisé à partir de l'offre « Alternance Développeur Full Stack & IA » (équipes CRM). Il illustre trois cas d'usage : support client, vente terrain et télévente.

## Le besoin
Un conseiller reçoit beaucoup de demandes et un commercial prend des notes après chaque appel. SmartDesk trie, résume et propose une action, **mais c'est toujours l'humain qui valide**.

## Fonctionnalités
- **Clients** : ajout, consultation, modification, suppression.
- **Demandes** : statut (nouvelle, en cours, résolue). L'IA détermine le sujet et la priorité, et propose une réponse.
- **Appels commerciaux** : résumé, niveau d'intérêt (chaud, tiède, froid) et prochaine action.
- **Tableau de bord** : volumes, urgences, prospects chauds.
- **Plan B** : sans clé IA, ou si l'IA échoue, des règles simples prennent le relais.

## Stack
FastAPI (Python), SQLite, React (Vite), API d'IA générative, Pytest, Docker, GitHub Actions.

## Lancer le projet
```bash
# Backend
cd backend && pip install -r requirements.txt && uvicorn main:app --reload
# Frontend (autre terminal)
cd frontend && npm install && npm run dev
# Tests
cd backend && python -m pytest -v
```
Option IA : définir la variable d'environnement `ANTHROPIC_API_KEY` (ne jamais la mettre dans le code).

## Estimation de charge (prévu contre réel)
| Lot | Estimé | Réel |
|---|---|---|
| Maquettes et modèle de données | 2 h | _à compléter_ |
| API et CRUD | 4 h | _à compléter_ |
| Frontend | 4 h | _à compléter_ |
| Assistant IA | 3 h | _à compléter_ |
| Module appels commerciaux | 3 h | _à compléter_ |
| Tests, Docker, CI | 3 h | _à compléter_ |

## Lien avec un CRM comme Salesforce
| SmartDesk | Équivalent Salesforce (à confirmer en formation) |
|---|---|
| Client | Account / Contact |
| Demande | Case |
| Appel commercial | Activity / Task |

## IA responsable
- L'IA propose, le conseiller valide.
- Les messages envoyés à l'IA sont limités en taille, et sa réponse est vérifiée avant utilisation.
- Si l'IA est indisponible, l'application reste utilisable.

## Limites connues et pistes
Pas d'authentification, SQLite uniquement, un seul fichier backend. Suite : découpage en modules, PostgreSQL, comptes utilisateurs.