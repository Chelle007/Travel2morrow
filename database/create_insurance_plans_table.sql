-- Table: public.insurance_plans

-- DROP TABLE IF EXISTS public.insurance_plans;

CREATE TABLE IF NOT EXISTS public.insurance_plans
(
    insurance_plan_id uuid NOT NULL DEFAULT gen_random_uuid(),
    insurance_company_id uuid NOT NULL,
	region character varying(255) COLLATE pg_catalog."default" NOT NULL,
    coverage_type character varying(100) COLLATE pg_catalog."default",
    policy_type character varying(100) COLLATE pg_catalog."default",
    plan_name character varying(255) COLLATE pg_catalog."default" NOT NULL,
    adult_price numeric(10,2) NOT NULL,
	child_price numeric(10,2) NOT NULL,
    discount numeric(5,2),
    medical_coverage numeric(10,2),
    trip_cancellation_coverage numeric(10,2),
    travel_delay_coverage numeric(10,2),
    baggage_loss_coverage numeric(10,2),
    emergency_evacuation boolean DEFAULT false,
    gadget_coverage boolean DEFAULT false,
    rewards character varying(255) COLLATE pg_catalog."default",
    additional_info text COLLATE pg_catalog."default",
    policy_detail text COLLATE pg_catalog."default",
    CONSTRAINT insurance_plans_pkey PRIMARY KEY (insurance_plan_id),
    CONSTRAINT fk_insurance_company FOREIGN KEY (insurance_company_id)
        REFERENCES public.insurance_companies (insurance_company_id)
        ON DELETE CASCADE
)

TABLESPACE pg_default;