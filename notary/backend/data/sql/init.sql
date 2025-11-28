-- ==============================================
-- Script d'initialisation PostgreSQL
-- Assistant Notaire - MVP
-- ==============================================

-- Activer les extensions nécessaires
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- Pour recherche full-text

-- ==============================================
-- Table: users
-- Gestion des utilisateurs (notaires)
-- ==============================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index pour recherche rapide par email
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ==============================================
-- Table: dossiers
-- Dossiers notariaux (transactions)
-- ==============================================
CREATE TABLE IF NOT EXISTS dossiers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nom VARCHAR(500) NOT NULL,
    type_transaction VARCHAR(100),  -- vente, hypotheque, testament, etc.
    statut VARCHAR(50) DEFAULT 'en_cours',  -- en_cours, complete, archive
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    -- Métadonnées d'analyse
    analyse_complete BOOLEAN DEFAULT FALSE,
    score_confiance FLOAT,  -- 0.0 à 1.0
    requiert_validation BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    analyse_at TIMESTAMP WITH TIME ZONE
);

-- Index pour recherches fréquentes
CREATE INDEX IF NOT EXISTS idx_dossiers_user_id ON dossiers(user_id);
CREATE INDEX IF NOT EXISTS idx_dossiers_statut ON dossiers(statut);
CREATE INDEX IF NOT EXISTS idx_dossiers_created_at ON dossiers(created_at DESC);

-- ==============================================
-- Table: documents
-- Documents uploadés (PDFs, etc.)
-- ==============================================
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dossier_id UUID REFERENCES dossiers(id) ON DELETE CASCADE,

    -- Informations fichier
    nom_fichier VARCHAR(500) NOT NULL,
    chemin_stockage TEXT NOT NULL,  -- Chemin sur disque ou S3
    taille_bytes BIGINT,
    type_mime VARCHAR(100),
    hash_sha256 VARCHAR(64),  -- Pour détecter les doublons

    -- Métadonnées
    type_document VARCHAR(100),  -- promesse_vente, titre_propriete, etc.
    extrait BOOLEAN DEFAULT FALSE,

    -- Timestamps
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index pour recherches
CREATE INDEX IF NOT EXISTS idx_documents_dossier_id ON documents(dossier_id);
CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(hash_sha256);

-- ==============================================
-- Table: donnees_extraites
-- Informations extraites des documents par l'IA
-- ==============================================
CREATE TABLE IF NOT EXISTS donnees_extraites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dossier_id UUID REFERENCES dossiers(id) ON DELETE CASCADE,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,

    -- Données extraites (JSON pour flexibilité)
    donnees JSONB NOT NULL,

    -- Confiance de l'extraction
    score_confiance FLOAT,

    -- Timestamps
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index pour recherches dans JSON
CREATE INDEX IF NOT EXISTS idx_donnees_extraites_dossier ON donnees_extraites(dossier_id);
CREATE INDEX IF NOT EXISTS idx_donnees_extraites_donnees ON donnees_extraites USING gin(donnees);

-- ==============================================
-- Table: checklists
-- Checklists générées par l'IA
-- ==============================================
CREATE TABLE IF NOT EXISTS checklists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dossier_id UUID REFERENCES dossiers(id) ON DELETE CASCADE,

    -- Contenu de la checklist (JSON)
    items JSONB NOT NULL,

    -- Métadonnées
    score_confiance FLOAT,
    validee_par_notaire BOOLEAN DEFAULT FALSE,

    -- Timestamps
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    validated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_checklists_dossier ON checklists(dossier_id);

-- ==============================================
-- Table: audit_log
-- Traçabilité de toutes les actions
-- ==============================================
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    dossier_id UUID REFERENCES dossiers(id) ON DELETE SET NULL,

    -- Détails de l'action
    action VARCHAR(100) NOT NULL,  -- view, edit, delete, etc.
    ressource_type VARCHAR(100),   -- dossier, document, etc.
    ressource_id UUID,

    -- Contexte
    ip_address INET,
    user_agent TEXT,
    details JSONB,

    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index pour recherches d'audit
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_dossier ON audit_log(dossier_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at DESC);

-- ==============================================
-- Triggers pour updated_at automatique
-- ==============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_dossiers_updated_at BEFORE UPDATE ON dossiers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ==============================================
-- Données de test (développement seulement)
-- ==============================================
-- Utilisateur de test (mot de passe: "test123")
INSERT INTO users (email, hashed_password, full_name, is_superuser)
VALUES (
    'notaire.test@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5UhT4xo7L5xw6',  -- test123
    'Notaire Test',
    TRUE
) ON CONFLICT (email) DO NOTHING;

-- Message de confirmation
DO $$
BEGIN
    RAISE NOTICE 'Base de données initialisée avec succès!';
    RAISE NOTICE 'Utilisateur de test: notaire.test@example.com / test123';
END $$;
