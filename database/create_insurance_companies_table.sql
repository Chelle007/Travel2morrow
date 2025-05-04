-- Table: public.insurance_companies

-- DROP TABLE IF EXISTS public.insurance_companies;

CREATE TABLE IF NOT EXISTS public.insurance_companies
(
    insurance_company_id uuid NOT NULL DEFAULT gen_random_uuid(),
    name character varying(255) NOT NULL,
    webscraping_needed bool,
    url character varying(255),
    CONSTRAINT insurance_companies_pkey PRIMARY KEY (insurance_company_id)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.insurance_companies
    OWNER to postgres;