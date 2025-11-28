-- ============================================================================
-- SCHEMA SURREALDB - Notary Assistant
-- ============================================================================
-- Définition des tables, champs, relations et permissions pour le système
-- d'analyse de dossiers notariaux avec workflows Agno
--
-- Usage:
--   surreal import --conn http://localhost:8001 --user root --pass root \
--     --ns notary --db notary_db schema.surql
-- ============================================================================

-- ============================================================================
-- TABLE: user
-- Description: Utilisateurs du système (notaires, assistants)
-- ============================================================================
DEFINE TABLE user SCHEMAFULL;

-- Champs de base
DEFINE FIELD email ON TABLE user TYPE string
  ASSERT string::is::email($value);
DEFINE FIELD nom ON TABLE user TYPE string;
DEFINE FIELD prenom ON TABLE user TYPE option<string>;
DEFINE FIELD password_hash ON TABLE user TYPE string;
DEFINE FIELD role ON TABLE user TYPE string
  ASSERT $value IN ["notaire", "assistant", "admin"];
DEFINE FIELD actif ON TABLE user TYPE bool DEFAULT true;
DEFINE FIELD created_at ON TABLE user TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON TABLE user TYPE datetime DEFAULT time::now();

-- Index unique sur email
DEFINE INDEX unique_email ON TABLE user COLUMNS email UNIQUE;

-- ============================================================================
-- TABLE: dossier
-- Description: Dossiers notariaux (transactions immobilières)
-- ============================================================================
DEFINE TABLE dossier SCHEMAFULL;

-- Champs de base
DEFINE FIELD nom_dossier ON TABLE dossier TYPE string;
DEFINE FIELD type_transaction ON TABLE dossier TYPE option<string>
  ASSERT !$value OR $value IN ["vente", "hypotheque", "testament", "donation", "autre"];
DEFINE FIELD statut ON TABLE dossier TYPE string DEFAULT "nouveau"
  ASSERT $value IN ["nouveau", "en_analyse", "termine", "en_erreur", "archive"];

-- Relation avec l'utilisateur
DEFINE FIELD user_id ON TABLE dossier TYPE record<user>;

-- Métadonnées
DEFINE FIELD created_at ON TABLE dossier TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON TABLE dossier TYPE datetime DEFAULT time::now();
DEFINE FIELD analyse_started_at ON TABLE dossier TYPE option<datetime>;
DEFINE FIELD analyse_completed_at ON TABLE dossier TYPE option<datetime>;

-- Résumé de l'analyse (flexible, pas de schéma strict)
DEFINE FIELD metadata ON TABLE dossier FLEXIBLE TYPE option<object>;

-- Épinglage du dossier
DEFINE FIELD pinned ON TABLE dossier TYPE bool DEFAULT false;

-- Résumé en une ligne (éditable par l'utilisateur)
DEFINE FIELD summary ON TABLE dossier TYPE option<string>;

-- ============================================================================
-- TABLE: document
-- Description: Documents PDF uploadés dans les dossiers
-- ============================================================================
DEFINE TABLE document SCHEMAFULL;

-- Champs de base
DEFINE FIELD nom_fichier ON TABLE document TYPE string;
DEFINE FIELD chemin_fichier ON TABLE document TYPE string;
DEFINE FIELD type_mime ON TABLE document TYPE string DEFAULT "application/pdf";
DEFINE FIELD taille_bytes ON TABLE document TYPE int;

-- Relation avec le dossier
DEFINE FIELD dossier_id ON TABLE document TYPE record<dossier>;

-- Type de document (identifié par l'IA)
DEFINE FIELD type_document ON TABLE document TYPE option<string>
  ASSERT !$value OR $value IN [
    "promesse_achat_vente",
    "offre_achat",
    "titre_propriete",
    "certificat_localisation",
    "hypotheque",
    "piece_identite",
    "autre"
  ];

-- Contenu extrait (stocké en JSON flexible)
DEFINE FIELD contenu_extrait ON TABLE document FLEXIBLE TYPE option<object>;

-- Métadonnées
DEFINE FIELD created_at ON TABLE document TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON TABLE document TYPE datetime DEFAULT time::now();
DEFINE FIELD hash_sha256 ON TABLE document TYPE option<string>;

-- Index pour rechercher par dossier
DEFINE INDEX idx_document_dossier ON TABLE document COLUMNS dossier_id;

-- ============================================================================
-- TABLE: agent_execution
-- Description: Historique d'exécution des agents Agno
-- ============================================================================
DEFINE TABLE agent_execution SCHEMALESS;

-- Permet un stockage totalement flexible des états d'agents
-- Champs typiques (non forcés):
-- - dossier_id: record<dossier>
-- - agent_name: string (extracteur, classificateur, verificateur, generateur)
-- - status: string (pending, running, completed, failed)
-- - input: object (données d'entrée)
-- - output: object (résultat de l'agent)
-- - error: string (si erreur)
-- - prompt_used: string (prompt envoyé au LLM)
-- - llm_response: string (réponse brute du LLM)
-- - tokens_used: int
-- - duration_ms: int
-- - created_at: datetime
-- - completed_at: datetime

-- ============================================================================
-- TABLE: checklist
-- Description: Checklists générées pour les dossiers
-- ============================================================================
DEFINE TABLE checklist SCHEMAFULL;

-- Relation avec le dossier
DEFINE FIELD dossier_id ON TABLE checklist TYPE record<dossier>;

-- Contenu de la checklist (flexible)
DEFINE FIELD items ON TABLE checklist FLEXIBLE TYPE array;
DEFINE FIELD score_confiance ON TABLE checklist TYPE option<float>
  ASSERT !$value OR ($value >= 0 AND $value <= 1);
DEFINE FIELD points_attention ON TABLE checklist FLEXIBLE TYPE option<array>;
DEFINE FIELD documents_manquants ON TABLE checklist FLEXIBLE TYPE option<array>;

-- Métadonnées
DEFINE FIELD created_at ON TABLE checklist TYPE datetime DEFAULT time::now();
DEFINE FIELD generated_by ON TABLE checklist TYPE string DEFAULT "agno_workflow";

-- Index pour rechercher par dossier
DEFINE INDEX idx_checklist_dossier ON TABLE checklist COLUMNS dossier_id;

-- ============================================================================
-- TABLE: audit_log
-- Description: Logs d'audit pour traçabilité complète
-- ============================================================================
DEFINE TABLE audit_log SCHEMALESS;

-- Permet un stockage flexible des événements
-- Champs typiques (non forcés):
-- - timestamp: datetime
-- - user_id: record<user>
-- - action: string
-- - resource_type: string
-- - resource_id: string
-- - details: object
-- - ip_address: string
-- - user_agent: string

-- ============================================================================
-- RELATIONS (GRAPH)
-- ============================================================================

-- Relation: un utilisateur possède des dossiers
DEFINE TABLE possede SCHEMAFULL;
DEFINE FIELD in ON TABLE possede TYPE record<user>;
DEFINE FIELD out ON TABLE possede TYPE record<dossier>;
DEFINE FIELD created_at ON TABLE possede TYPE datetime DEFAULT time::now();

-- Relation: un dossier contient des documents
DEFINE TABLE contient SCHEMAFULL;
DEFINE FIELD in ON TABLE contient TYPE record<dossier>;
DEFINE FIELD out ON TABLE contient TYPE record<document>;
DEFINE FIELD created_at ON TABLE contient TYPE datetime DEFAULT time::now();

-- ============================================================================
-- DONNÉES DE TEST
-- ============================================================================

-- Utilisateur de test (notaire) - mot de passe: notaire123
-- password_hash = SHA256("notaire123")
CREATE user:demo_notaire CONTENT {
  email: "notaire@test.com",
  nom: "Jean Tremblay",
  prenom: "",
  password_hash: "8b7435cd7d4f361cd54fc38e549bbc95a917ac872cee12fc61e00d02ddc0cee7",
  role: "notaire",
  actif: true
};

-- Utilisateur admin - mot de passe: admin1234
-- password_hash = SHA256("admin1234")
CREATE user:admin CONTENT {
  email: "admin@test.com",
  nom: "Admin User",
  prenom: "",
  password_hash: "ac9689e2272427085e35b9d3e3e8bed88cb3434828b43b86fc0596cad4c6e270",
  role: "admin",
  actif: true
};

-- ============================================================================
-- FIN DU SCHEMA
-- ============================================================================
