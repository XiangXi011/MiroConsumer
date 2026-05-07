# Changelog

## [0.7.0] - 2026-05-07

### Added
- API authentication & authorization system (JWT + API Key + RBAC)
- ConsumerCognitionEngine three-layer cognitive architecture
- Enterprise-grade population model (30+ fields, three generation modes)
- Monte Carlo validation framework (three-mode experiments)
- Social graph (Watts-Strogatz, Barabasi-Albert)
- RuntimeControlLayer (checkpoint + early stop)
- DOE experiment design (A/B/n, price ladder, stratified assignment)
- LLM Governor (circuit breaker, budget management, retry)
- Structured logging, security headers, three-tier rate limiting
- Pydantic input validation for key API endpoints
- Dry run mode for simulation preview
- BusinessBrief schema versioning (v1.0.0)
- Unified error response format (success_response, paginated_response)

### Fixed
- WEAK_SECRET_KEYS typo
- Cognition engine Pydantic output validation

### Security
- SECRET_KEY strong validation (length >= 32, weak value blocklist)
- CORS production environment disallow * wildcard
- Trivy image vulnerability scanning
- SAST + dependency audit CI
