--
-- PostgreSQL database dump
--

\restrict BQKs8jYIOWs1shmWP8CuN79OGOMlRE1dvIhVu0BEx2HT40dMcDAz3caWxILr6Ra

-- Dumped from database version 14.19
-- Dumped by pg_dump version 14.19

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

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: knowledge_share_offers; Type: TABLE; Schema: public; Owner: apexsigma_user
--

CREATE TABLE public.knowledge_share_offers (
    id integer NOT NULL,
    request_id integer NOT NULL,
    offering_agent_id character varying(255) NOT NULL,
    memory_id integer NOT NULL,
    confidence_score double precision NOT NULL,
    status character varying(255) NOT NULL,
    created_at timestamp without time zone
);


ALTER TABLE public.knowledge_share_offers OWNER TO apexsigma_user;

--
-- Name: knowledge_share_offers_id_seq; Type: SEQUENCE; Schema: public; Owner: apexsigma_user
--

CREATE SEQUENCE public.knowledge_share_offers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.knowledge_share_offers_id_seq OWNER TO apexsigma_user;

--
-- Name: knowledge_share_offers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: apexsigma_user
--

ALTER SEQUENCE public.knowledge_share_offers_id_seq OWNED BY public.knowledge_share_offers.id;


--
-- Name: knowledge_share_requests; Type: TABLE; Schema: public; Owner: apexsigma_user
--

CREATE TABLE public.knowledge_share_requests (
    id integer NOT NULL,
    requester_agent_id character varying(255) NOT NULL,
    target_agent_id character varying(255) NOT NULL,
    query text NOT NULL,
    confidence_threshold double precision NOT NULL,
    sharing_policy character varying(255) NOT NULL,
    status character varying(255) NOT NULL,
    created_at timestamp without time zone
);


ALTER TABLE public.knowledge_share_requests OWNER TO apexsigma_user;

--
-- Name: knowledge_share_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: apexsigma_user
--

CREATE SEQUENCE public.knowledge_share_requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.knowledge_share_requests_id_seq OWNER TO apexsigma_user;

--
-- Name: knowledge_share_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: apexsigma_user
--

ALTER SEQUENCE public.knowledge_share_requests_id_seq OWNED BY public.knowledge_share_requests.id;


--
-- Name: memories; Type: TABLE; Schema: public; Owner: apexsigma_user
--

CREATE TABLE public.memories (
    id integer NOT NULL,
    content text NOT NULL,
    memory_metadata json,
    embedding_id character varying(255),
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.memories OWNER TO apexsigma_user;

--
-- Name: memories_id_seq; Type: SEQUENCE; Schema: public; Owner: apexsigma_user
--

CREATE SEQUENCE public.memories_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.memories_id_seq OWNER TO apexsigma_user;

--
-- Name: memories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: apexsigma_user
--

ALTER SEQUENCE public.memories_id_seq OWNED BY public.memories.id;


--
-- Name: registered_tools; Type: TABLE; Schema: public; Owner: apexsigma_user
--

CREATE TABLE public.registered_tools (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text NOT NULL,
    usage text NOT NULL,
    tags json,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.registered_tools OWNER TO apexsigma_user;

--
-- Name: registered_tools_id_seq; Type: SEQUENCE; Schema: public; Owner: apexsigma_user
--

CREATE SEQUENCE public.registered_tools_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.registered_tools_id_seq OWNER TO apexsigma_user;

--
-- Name: registered_tools_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: apexsigma_user
--

ALTER SEQUENCE public.registered_tools_id_seq OWNED BY public.registered_tools.id;


--
-- Name: knowledge_share_offers id; Type: DEFAULT; Schema: public; Owner: apexsigma_user
--

ALTER TABLE ONLY public.knowledge_share_offers ALTER COLUMN id SET DEFAULT nextval('public.knowledge_share_offers_id_seq'::regclass);


--
-- Name: knowledge_share_requests id; Type: DEFAULT; Schema: public; Owner: apexsigma_user
--

ALTER TABLE ONLY public.knowledge_share_requests ALTER COLUMN id SET DEFAULT nextval('public.knowledge_share_requests_id_seq'::regclass);


--
-- Name: memories id; Type: DEFAULT; Schema: public; Owner: apexsigma_user
--

ALTER TABLE ONLY public.memories ALTER COLUMN id SET DEFAULT nextval('public.memories_id_seq'::regclass);


--
-- Name: registered_tools id; Type: DEFAULT; Schema: public; Owner: apexsigma_user
--

ALTER TABLE ONLY public.registered_tools ALTER COLUMN id SET DEFAULT nextval('public.registered_tools_id_seq'::regclass);


--
-- Data for Name: knowledge_share_offers; Type: TABLE DATA; Schema: public; Owner: apexsigma_user
--

COPY public.knowledge_share_offers (id, request_id, offering_agent_id, memory_id, confidence_score, status, created_at) FROM stdin;
\.


--
-- Data for Name: knowledge_share_requests; Type: TABLE DATA; Schema: public; Owner: apexsigma_user
--

COPY public.knowledge_share_requests (id, requester_agent_id, target_agent_id, query, confidence_threshold, sharing_policy, status, created_at) FROM stdin;
\.


--
-- Data for Name: memories; Type: TABLE DATA; Schema: public; Owner: apexsigma_user
--

COPY public.memories (id, content, memory_metadata, embedding_id, created_at, updated_at) FROM stdin;
1	Neo4j knowledge graph is now operational for Operation Asgard Rebirth	{"type": "system_status", "priority": "high", "phase": "asgard_preparation"}	0d49a89f-1b1b-49c4-b073-e79c94ba19bc	2025-08-31 21:37:56.936603	2025-08-31 21:37:56.973201
2	ApexSigma Docker Network Topology - Complete infrastructure map with 13 active services on 172.26.0.0/16 subnet. Critical Tier 1 services: memOS (172.26.0.13), Neo4j (172.26.0.14), PostgreSQL (172.26.0.2), InGest-LLM (172.26.0.12). All services operational with health monitoring via Grafana dashboard. Network secured with internal-only access for critical services.	{"type": "infrastructure_map", "source": "verified_network_topology", "security_level": "protected", "verification_date": "2025-08-31", "document_location": "secure_verified_docs/VERIFIED_DOCKER_NETWORK_MAP.md", "service_count": 13, "network_subnet": "172.26.0.0/16", "tier_1_services": ["memOS", "Neo4j", "PostgreSQL", "InGest-LLM"], "omega_ingest_category": "infrastructure_truth"}	0eea2d4d-dba5-4466-a5b3-83c857ad1c95	2025-08-31 21:57:31.553493	2025-08-31 21:57:31.577877
3	OMEGA INGEST LAWS established - Immutable Truth Protocol for ApexSigma ecosystem. Dual verification required for all Omega Ingest uploads. Tier 1 protected services: memOS API (172.26.0.13), Neo4j Knowledge Graph (172.26.0.14), PostgreSQL Main (172.26.0.2), InGest-LLM API (172.26.0.12). All agents must query Omega Ingest via InGest-LLM before code changes. Continuous monitoring required with <99% uptime triggering immediate alerts. MAR (Mandatory Agent Review) protocol enforced.	{"type": "governance_protocol", "source": "omega_ingest_laws", "security_level": "tier_1", "establishment_date": "2025-08-31", "authority": "ApexSigma_Ecosystem_Governance", "enforcement": "automated_and_human", "protected_services": ["memOS", "Neo4j", "PostgreSQL", "InGest-LLM"], "verification_requirement": "dual_party", "omega_ingest_category": "governance_law"}	71aa52ec-d559-401c-b6bc-65698bd52c4d	2025-08-31 22:13:33.968982	2025-08-31 22:13:34.009355
4	VERIFIED BASELINE BUNDLES CAPTURED: DevEnviro.as (1,994 files, early development, 10+ empty files requiring implementation), MemOS.as (865 files, OPERATIONAL, 51 modules, 24 API endpoints, 2+ hours uptime), InGest-LLM.as (2,724 files, 33 modules, 23+ endpoints, 11+ hours uptime, 2 disabled routers), Tools.as (109 files, 23 modules, 70/100 production ready, API offline). ECOSYSTEM HEALTH: 65/100 overall, with memOS as stable foundation. INFRASTRUCTURE STATUS: 13+ Docker services on 172.26.0.0/16 network, complete observability stack, Neo4j + PostgreSQL + Redis + Qdrant operational. CRITICAL GAPS: Implementation completeness, service deployment, database schemas, authentication, test coverage. OPERATION ASGARD REBIRTH READY: Strong foundation established, requires service deployment and implementation completion.	{"operation": "Asgard Rebirth", "phase": "Pre-Operation Baseline", "verification_status": "DUAL_VERIFIED", "ecosystem_health": "65/100", "date_created": "2025-09-01", "total_projects": 4, "operational_services": 1, "infrastructure_score": "READY_WITH_CONDITIONS"}	13299e53-ba0f-4567-b0bf-3b4887988e0e	2025-09-01 03:44:07.629621	2025-09-01 03:44:07.779437
\.


--
-- Data for Name: registered_tools; Type: TABLE DATA; Schema: public; Owner: apexsigma_user
--

COPY public.registered_tools (id, name, description, usage, tags, created_at, updated_at) FROM stdin;
1	test_tool_integration	A test tool for integration testing	Use this tool for testing purposes	["testing", "integration"]	2025-09-04 21:42:32.179312	2025-09-04 21:42:32.179316
\.


--
-- Name: knowledge_share_offers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: apexsigma_user
--

SELECT pg_catalog.setval('public.knowledge_share_offers_id_seq', 1, false);


--
-- Name: knowledge_share_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: apexsigma_user
--

SELECT pg_catalog.setval('public.knowledge_share_requests_id_seq', 1, false);


--
-- Name: memories_id_seq; Type: SEQUENCE SET; Schema: public; Owner: apexsigma_user
--

SELECT pg_catalog.setval('public.memories_id_seq', 4, true);


--
-- Name: registered_tools_id_seq; Type: SEQUENCE SET; Schema: public; Owner: apexsigma_user
--

SELECT pg_catalog.setval('public.registered_tools_id_seq', 6, true);


--
-- Name: knowledge_share_offers knowledge_share_offers_pkey; Type: CONSTRAINT; Schema: public; Owner: apexsigma_user
--

ALTER TABLE ONLY public.knowledge_share_offers
    ADD CONSTRAINT knowledge_share_offers_pkey PRIMARY KEY (id);


--
-- Name: knowledge_share_requests knowledge_share_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: apexsigma_user
--

ALTER TABLE ONLY public.knowledge_share_requests
    ADD CONSTRAINT knowledge_share_requests_pkey PRIMARY KEY (id);


--
-- Name: memories memories_pkey; Type: CONSTRAINT; Schema: public; Owner: apexsigma_user
--

ALTER TABLE ONLY public.memories
    ADD CONSTRAINT memories_pkey PRIMARY KEY (id);


--
-- Name: registered_tools registered_tools_name_key; Type: CONSTRAINT; Schema: public; Owner: apexsigma_user
--

ALTER TABLE ONLY public.registered_tools
    ADD CONSTRAINT registered_tools_name_key UNIQUE (name);


--
-- Name: registered_tools registered_tools_pkey; Type: CONSTRAINT; Schema: public; Owner: apexsigma_user
--

ALTER TABLE ONLY public.registered_tools
    ADD CONSTRAINT registered_tools_pkey PRIMARY KEY (id);


--
-- PostgreSQL database dump complete
--

\unrestrict BQKs8jYIOWs1shmWP8CuN79OGOMlRE1dvIhVu0BEx2HT40dMcDAz3caWxILr6Ra

