-- Table: public.insurance_details

-- DROP TABLE IF EXISTS public.insurance_details;

CREATE TABLE IF NOT EXISTS public.insurance_details
(
    insurance_id uuid NOT NULL DEFAULT gen_random_uuid(),
    name character varying(255) COLLATE pg_catalog."default" NOT NULL,
    plan_type character varying(100) COLLATE pg_catalog."default",
    price numeric(10,2) NOT NULL,
    discount numeric(5,2),
    trip_cancellation_coverage numeric(10,2),
    medical_coverage numeric(10,2),
    baggage_delay_coverage numeric(10,2),
    baggage_loss_coverage numeric(10,2),
    emergency_evacuation boolean DEFAULT false,
    gadget_coverage boolean DEFAULT false,
    rewards character varying(255) COLLATE pg_catalog."default",
    express_buy_link character varying(255) COLLATE pg_catalog."default",
    additional_info text COLLATE pg_catalog."default",
    policy text COLLATE pg_catalog."default",
    CONSTRAINT insurances_pkey PRIMARY KEY (insurance_id)
)

TABLESPACE pg_default;