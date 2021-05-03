SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;
CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;
SET default_tablespace = '';
SET default_table_access_method = heap;

DROP TABLE IF EXISTS public.url CASCADE;
CREATE TABLE public.url (
    url_id bigint NOT NULL,
    uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    url_group_id integer,
    url character varying(255) NOT NULL,
    note character varying(255),
    rsp_regex character varying(255),
    rsp_code smallint,
    sequence smallint
);
ALTER TABLE public.url OWNER TO postgres;

DROP TABLE IF EXISTS public.url_group CASCADE;
CREATE TABLE public.url_group (
    url_group_id bigint NOT NULL,
    uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name character varying(255) NOT NULL,
    notes character varying(255)
);
ALTER TABLE public.url_group OWNER TO postgres;
ALTER TABLE public.url_group ALTER COLUMN url_group_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.url_group_url_group_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

DROP TABLE IF EXISTS public.url_history CASCADE;
CREATE TABLE public.url_history (
    url_history_id bigint NOT NULL,
    url_id bigint,
    error varchar(255),
    event_timestamp timestamp(6) with time zone NOT NULL,
    dns jsonb,
    http_rsp_time numeric(14,8) DEFAULT 0.0000 NOT NULL,
    rsp_regex_count smallint,
    rsp_status_code smallint,
    ts_created_at timestamp(6) with time zone DEFAULT now()
);
ALTER TABLE public.url_history OWNER TO postgres;
ALTER TABLE public.url_history ALTER COLUMN url_history_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.url_history_url_history_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
ALTER TABLE public.url ALTER COLUMN url_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.url_url_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

ALTER TABLE ONLY public.url_group
    ADD CONSTRAINT url_group_pkey PRIMARY KEY (url_group_id);
ALTER TABLE ONLY public.url_group
    ADD CONSTRAINT url_group_uuid_key UNIQUE (uuid);
ALTER TABLE ONLY public.url_history
    ADD CONSTRAINT url_history_pkey PRIMARY KEY (url_history_id);
ALTER TABLE ONLY public.url
    ADD CONSTRAINT url_pkey PRIMARY KEY (url_id);
ALTER TABLE ONLY public.url_history
    ADD CONSTRAINT url_history_url_id_fkey FOREIGN KEY (url_id) REFERENCES public.url(url_id);
ALTER TABLE ONLY public.url
    ADD CONSTRAINT url_url_group_id_fkey FOREIGN KEY (url_group_id) REFERENCES public.url_group(url_group_id);
