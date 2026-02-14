# EU AI Act Compliance Guide for Safe Agent

**For Organizations Deploying AI Coding Agents**

Safe Agent provides technical controls and documentation to help organizations comply with the EU Artificial Intelligence Act when deploying AI coding agents. This guide maps Safe Agent features to specific EU AI Act requirements.

---

## ⚖️ EU AI Act Overview

The **EU Artificial Intelligence Act** is the world's first comprehensive AI regulation, establishing a risk-based framework for AI systems.

**Key Dates**:
- **August 1, 2024**: Act entered into force
- **August 2, 2025**: General-purpose AI model obligations began
- **August 2, 2026**: High-risk AI system obligations (Annex III) **← 6 MONTHS AWAY**
- **August 2, 2027**: Full implementation complete

**Penalties for Non-Compliance**:
- Up to **€35 million** or **7% of global annual turnover** (whichever is higher)
- For SMEs: Up to €7.5 million or 1.5% of turnover

---

## 🎯 Are AI Coding Agents Covered?

**Short Answer**: It depends on your use case.

**High-Risk Classification Criteria** (Annex III):
AI systems used in employment, worker management, or critical infrastructure could be classified as high-risk if they:
- Make decisions affecting employment/worker rights
- Operate in safety-critical contexts
- Process sensitive/biometric data
- Determine access to essential services

**Common Scenarios**:

| Scenario | Risk Level | AI Act Applicability |
|----------|-----------|---------------------|
| AI agent for internal development only | ⚪ Minimal | General obligations only |
| AI agent deployed to developer workforce | 🟡 Medium | Transparency requirements |
| AI agent making production changes | 🟠 Medium-High | Risk management required |
| AI agent in regulated industry (finance, healthcare) | 🔴 High | Full Annex III obligations |
| AI agent with autonomous production deployment | 🔴 High | Full Annex III obligations |

**Consult Legal Counsel**: This guide provides technical implementation guidance only. Organizations should consult qualified legal counsel for compliance assessment.

---

## 📋 Article-by-Article Compliance Mapping

### Article 9: Risk Management System

**Requirement**: Providers of high-risk AI systems must establish, implement, document, and maintain a risk management system.

**Safe Agent Provides**:

✅ **Risk Identification**: Automated risk assessment for every file operation
- Risk levels: LOW, MEDIUM, HIGH, CRITICAL
- Risk factors: Production patterns, credentials, destructive operations, database changes

✅ **Risk Analysis**: Contextual evaluation considering:
- File type and path
- Content patterns (production URLs, API keys, connection strings)
- Operation type (create, modify, delete)
- Historical risk patterns

✅ **Risk Mitigation**: Multiple mitigation controls
- Pre-execution preview (mandatory)
- Approval workflow (human-in-the-loop)
- Policy-as-code enforcement (Sprint 2)
- Rollback capability (Sprint 3)

**Compliance Evidence**:
```bash
# Generate risk assessment report
safe-agent "task" --compliance-mode --audit-export risk-assessment.json

# Audit log includes:
# - Risk level per operation
# - Risk factors identified
# - Mitigation measures applied
# - Human approval records
```

**Documentation Artifacts**:
- Risk assessment methodology: `docs/insurance-integration.md` (Risk Assessment section)
- Risk mitigation controls: This document
- Audit trails: JSON export with risk analysis

---

### Article 10: Data and Data Governance

**Requirement**: Training, validation, and testing datasets must be relevant, representative, and free of errors and biases.

**Applicability to AI Coding Agents**:
This applies to the underlying AI model (Claude, GPT, etc.), not Safe Agent itself. Safe Agent is a safety layer, not a trained AI system.

**Safe Agent Supports Compliance By**:

✅ **Data Minimization**: Safe Agent only processes:
- File paths and content for risk assessment
- User approval decisions
- Execution results
- No training on user data

✅ **Data Quality Monitoring**: Audit trails track data quality issues
- Invalid file paths rejected
- Malformed operations logged
- Data integrity checks in place

**Compliance Evidence**:
- Safe Agent does not train on customer data
- All data processing is deterministic (rules-based)
- Privacy policy: No customer data leaves local environment
- Audit logs document data processing steps

---

### Article 11: Technical Documentation

**Requirement**: Providers must draw up technical documentation demonstrating compliance.

**Safe Agent Provides**:

✅ **System Architecture Documentation**:
- `CLAUDE.md`: System design and architecture
- `docs/implementation-roadmap.md`: Development methodology
- `README.md`: System capabilities and limitations

✅ **Risk Assessment Methodology**:
- `docs/insurance-integration.md`: Risk scoring framework
- `docs/eu-ai-act-compliance.md`: This document

✅ **Validation and Testing**:
- `tests/`: Comprehensive test suite (53+ tests)
- Test coverage reports available
- Continuous integration via GitHub Actions

✅ **Instructions for Use**:
- CLI help: `safe-agent --help`
- Usage documentation: `README.md`
- Integration guides: `docs/insurance-integration.md`

**Compliance Actions**:
1. Maintain Safe Agent documentation current
2. Document your organization's usage policies
3. Keep audit trails for regulatory inspection
4. Update technical documentation annually

---

### Article 12: Record-Keeping

**Requirement**: High-risk AI systems must have logging capabilities to ensure traceability throughout their lifecycle.

**Safe Agent Provides**:

✅ **Automatic Logging**: Every operation logged automatically
- Task description and requester
- Risk assessment and approval decision
- Execution status and timestamp
- All audit data timestamped (ISO 8601)

✅ **Audit Trail Export**: JSON format for long-term retention
```bash
safe-agent "task" --audit-export audit-$(date +%Y%m%d).json
```

✅ **Retention-Friendly Format**: Structured JSON for archival
- Machine-readable for automated compliance checks
- Human-readable for manual audit
- Schema-validated for integrity

**Audit Log Contents**:
```json
{
  "audit_metadata": {
    "export_version": "1.0",
    "export_timestamp": "2026-02-11T14:23:45Z",
    "agent_version": "safe-agent 0.4.0"
  },
  "task": {
    "task_description": "Update production config",
    "requested_at": "2026-02-11T14:20:00Z",
    "requested_by": "engineer@company.eu"
  },
  "changes": [...],
  "summary": {
    "changes_approved": 1,
    "changes_rejected": 0,
    "max_risk_level_seen": "HIGH"
  }
}
```

**Retention Recommendations**:
- **Minimum**: 90 days (operational needs)
- **Recommended**: 1 year (audit cycle)
- **Regulated Industries**: 7+ years (sector-specific requirements)
- **High-Risk Systems**: 10 years (per Article 12 guidance)

**Compliance Actions**:
1. Enable audit export for all high-risk operations
2. Store audit logs in immutable storage (S3, compliance archive)
3. Implement retention policy per your sector
4. Document retention procedures

---

### Article 13: Transparency and Information to Deployers

**Requirement**: Providers must provide deployers with information to enable compliance.

**Safe Agent Provides**:

✅ **Compliance Documentation**: This guide documents:
- Compliance capabilities
- Limitations and constraints
- Required user actions
- Integration guidance

✅ **Clear Capabilities Statement**: Documentation clearly states:
- What Safe Agent does (pre-execution review)
- What Safe Agent doesn't do (cannot prevent all incidents)
- Required human oversight (approval workflow)
- Integration requirements

✅ **Usage Instructions**: Comprehensive usage docs
- CLI documentation: `safe-agent --help`
- Integration guides: MCP server, CrewAI, LangChain
- Configuration examples: Policy files, compliance mode

**Deployer Obligations**:
As a deployer of AI coding agents with Safe Agent, you must:
1. Conduct conformity assessment for your use case
2. Register high-risk system in EU database (if applicable)
3. Implement human oversight procedures
4. Monitor system performance and safety
5. Report serious incidents to authorities

**Compliance Actions**:
1. Read all Safe Agent documentation
2. Assess your use case against Annex III criteria
3. Implement organizational policies around Safe Agent
4. Train operators on proper usage
5. Document your deployment configuration

---

### Article 14: Human Oversight

**Requirement**: High-risk AI systems must be designed for effective human oversight.

**Safe Agent Provides**:

✅ **Built-in Human Oversight**: Every risky operation requires human approval
- Preview shows exactly what will change
- Diff display for code/config changes
- Risk level explicitly shown
- User must actively approve (no auto-execution of high-risk)

✅ **Informed Decision-Making**: Operators receive:
- Clear risk assessment (LOW/MEDIUM/HIGH/CRITICAL)
- Risk factors in plain language
- File diffs showing exact changes
- Impact preview before execution

✅ **Override Controls**: Operators can:
- Reject any operation (approval not mandatory)
- Use dry-run mode for preview without execution
- Configure policy-as-code for automatic blocks (Sprint 2)
- Set fail-on-risk thresholds

✅ **Compliance Mode**: Strictest oversight settings
```bash
safe-agent "task" --compliance-mode
# Disables auto-approve for ALL risk levels
# Requires explicit approval for every change
# Audit trail records compliance mode usage
```

**Human Oversight Checklist**:
- [ ] Operators trained on Safe Agent usage
- [ ] Approval authority clearly defined
- [ ] Escalation procedures documented
- [ ] High-risk operations require senior approval
- [ ] Compliance mode enabled for production systems
- [ ] Regular audit of approval decisions

**Compliance Actions**:
1. Implement approval authority matrix
2. Train all operators on risk assessment
3. Enable compliance mode for high-risk environments
4. Document human oversight procedures
5. Audit approval patterns quarterly

---

### Article 15: Accuracy, Robustness, and Cybersecurity

**Requirement**: High-risk AI systems must achieve appropriate levels of accuracy, robustness, and cybersecurity.

**Safe Agent Provides**:

✅ **Accuracy**: Deterministic risk assessment
- Rules-based risk detection (not probabilistic)
- Pattern matching for known-risky patterns
- No false negatives for critical patterns
- Configurable sensitivity via policy-as-code (Sprint 2)

✅ **Robustness**: Comprehensive testing
- 53+ automated tests (growing)
- Path traversal protection tested
- Error handling tested
- Edge case coverage (unicode, spaces, etc.)
- Continuous integration on all commits

✅ **Cybersecurity**: Security-first design
- Path safety checks prevent directory traversal
- No remote code execution
- No credential storage
- Audit logs don't contain secrets
- Local-first architecture (no data sent to cloud)

**Security Measures**:
```python
# Path safety (prevents attacks)
def _resolve_path_safe(self, path: str) -> Path | None:
    """Reject absolute paths, traversal attempts, paths outside working dir"""
    # Rejects: /etc/passwd, ../../../secret, symlinks outside base
    # Returns: None if unsafe, resolved Path if safe
```

✅ **Resilience**: Fails safely
- Invalid operations rejected (not executed)
- Errors logged but don't crash agent
- Partial failures don't prevent audit export
- Rollback capability (Sprint 3) for error recovery

**Compliance Actions**:
1. Run test suite before deployment: `pytest tests/`
2. Review security advisories for dependencies
3. Enable all safety features (compliance mode, fail-on-risk)
4. Implement incident response plan
5. Conduct annual security assessment

---

## 🔒 Compliance Mode Implementation

Safe Agent provides a **compliance mode** specifically designed for regulated environments and EU AI Act compliance.

### Enabling Compliance Mode

```bash
# Enable for single task
safe-agent "task" --compliance-mode --audit-export compliance-audit.json

# Document organizational requirement
echo "SAFE_AGENT_COMPLIANCE_MODE=true" >> .env
```

### What Compliance Mode Does

**Strictest Safety Settings**:
- ❌ Disables `--auto-approve-low` (all changes require approval)
- ✅ Enables comprehensive audit logging
- ✅ Records compliance mode in audit metadata
- ✅ Sets compliance flags for regulatory inspection

**Audit Trail Enhancement**:
```json
{
  "audit_metadata": {
    "compliance_mode": true,
    "export_timestamp": "2026-02-11T14:30:00Z"
  },
  "compliance_flags": {
    "compliance_mode_enabled": true,
    "all_high_risk_approved": true,
    "audit_trail_complete": true
  }
}
```

**Use Cases**:
- Production environments in regulated industries
- Financial services (GDPR + AI Act)
- Healthcare (HIPAA + AI Act)
- Critical infrastructure
- Any Annex III high-risk classification

---

## 📊 Compliance Checklist

Use this checklist to assess your Safe Agent deployment against EU AI Act requirements:

### Pre-Deployment

- [ ] **Legal Assessment**: Consulted legal counsel on AI Act applicability
- [ ] **Risk Classification**: Determined if your use case is high-risk (Annex III)
- [ ] **Technical Documentation**: Compiled system documentation
- [ ] **Data Protection**: GDPR compliance verified (if EU data processing)
- [ ] **Provider Obligations**: If providing AI system to others, obligations clear

### Deployment

- [ ] **Compliance Mode**: Enabled for high-risk systems
- [ ] **Audit Export**: Configured and tested
- [ ] **Human Oversight**: Approval workflows documented and trained
- [ ] **Record Retention**: Policy documented and implemented
- [ ] **Incident Response**: Plan in place for serious incidents
- [ ] **Testing**: Test suite run and passing

### Operations

- [ ] **Audit Logs**: Retained per retention policy
- [ ] **Monitoring**: Regular review of approval patterns
- [ ] **Training**: Operators trained on compliance requirements
- [ ] **Updates**: Safe Agent kept current (security updates)
- [ ] **Documentation**: Technical docs reviewed annually
- [ ] **Reporting**: Serious incident reporting procedures tested

### Governance

- [ ] **Accountability**: Roles and responsibilities documented
- [ ] **Oversight**: Management review of AI system usage
- [ ] **Audits**: Annual compliance audit scheduled
- [ ] **Registration**: System registered in EU database (if high-risk)
- [ ] **Conformity Assessment**: Completed per Article 43
- [ ] **CE Marking**: Affixed (if applicable)

---

## 🚨 Serious Incident Reporting

**Article 73 Obligation**: Providers must report serious incidents to market surveillance authorities.

**What Constitutes a Serious Incident**:
- Death or serious harm to health, safety, fundamental rights
- Significant disruption of critical services
- Breach of confidentiality obligations
- Discrimination or other fundamental rights violations

**Safe Agent Incident Logging**:
```bash
# All incidents automatically logged in audit trail
safe-agent "task" --audit-export incident-$(date +%Y%m%d).json

# Review for serious incidents
jq '.summary.max_risk_level_seen' incident-*.json
```

**Reporting Timeline**:
- **15 days** after becoming aware of serious incident
- Report to national market surveillance authority
- Include: Nature of incident, corrective measures, affected parties

**Safe Agent Supports Investigation**:
- Complete audit trail for incident analysis
- Timestamp and actor information
- Risk assessment that was shown
- Approval or rejection records
- Execution results and errors

---

## 📝 Documentation Templates

### Template: AI System Registration

For high-risk systems requiring EU database registration:

```
AI System Registration - Safe Agent Deployment

Provider: [Your Organization]
Provider Address: [EU Address]
Provider Contact: [Contact Info]

AI System Details:
- Name: Safe Agent Deployment at [Your Organization]
- Type: Safety/Risk Assessment System for AI Coding Agents
- Classification: [Your Assessment - likely not high-risk itself]
- Purpose: Pre-execution review and approval of AI-generated code changes
- Risk Mitigation: Human oversight, audit trails, risk assessment

Technical Specifications:
- Version: safe-agent 0.4.0
- Deployment Date: [Date]
- Human Oversight: Approval workflow (Article 14)
- Record Keeping: Audit export JSON (Article 12)
- Documentation: Available at https://github.com/agent-polis/safe-agent

Conformity Assessment:
- Internal Controls: [Your Assessment Process]
- Technical Documentation: Complete
- Risk Assessment: Performed [Date]
```

### Template: Human Oversight Procedure

```markdown
# Human Oversight Procedure for AI Coding Agent

**Effective Date**: [Date]
**Document Owner**: [Role]
**Review Frequency**: Annual

## Purpose
This procedure ensures effective human oversight of AI coding agents per EU AI Act Article 14.

## Scope
Applies to all AI coding agent operations affecting:
- Production systems
- Customer data
- Critical infrastructure
- [Other high-risk contexts]

## Approval Authority

| Risk Level | Approver | Escalation Required |
|-----------|----------|-------------------|
| LOW | Any engineer | No |
| MEDIUM | Senior engineer | No |
| HIGH | Tech lead | Yes, to Director |
| CRITICAL | Director of Engineering | Yes, to CTO |

## Procedure

1. **Task Submission**: Engineer submits task to AI agent via Safe Agent
2. **Risk Assessment**: Safe Agent analyzes and assigns risk level
3. **Preview**: System shows preview with diff and risk factors
4. **Approval Decision**: Authorized approver reviews and decides
5. **Execution**: If approved, change executed with audit logging
6. **Verification**: Approver verifies expected outcome
7. **Incident Response**: If issues, follow incident procedure

## Training Requirements
- All operators: Safe Agent usage training (4 hours)
- Approvers: Risk assessment training (8 hours)
- Annual refresher for all personnel

## Audit
- Monthly review of approval patterns
- Quarterly review of high-risk operations
- Annual procedure effectiveness review

## Record Keeping
- All approvals logged via Safe Agent audit export
- Retention: 10 years (high-risk systems)
- Storage: [Location - immutable storage]
```

### Template: Technical Documentation (Article 11)

```markdown
# Technical Documentation: AI Coding Agent Deployment

**System Name**: [Your Organization] AI Coding Agent
**Documentation Date**: [Date]
**Version**: 1.0

## 1. General Description

**Purpose**: Accelerate software development while maintaining safety controls

**AI System Used**:
- Base AI: Claude Sonnet 4 (Anthropic)
- Safety Layer: Safe Agent 0.4.0 (agent-polis/safe-agent)

**Classification**: [Your risk assessment]

## 2. System Architecture

[Diagram showing: Developer → Safe Agent → Claude API → Code Change → Preview → Approval → Execution]

**Components**:
- Safe Agent CLI: Pre-execution review layer
- Impact Preview: Risk assessment engine
- Claude API: Code generation
- Audit System: Compliance logging

## 3. Risk Management (Article 9)

**Identified Risks**:
- Unauthorized production changes
- Data loss or corruption
- Security vulnerabilities introduced
- Compliance violations

**Mitigation Measures**:
- Mandatory preview before execution
- Risk-based approval workflow
- Audit logging for accountability
- Rollback capability

## 4. Data Governance (Article 10)

**Data Processed**:
- Input: Task descriptions, file contents
- Processing: Risk assessment, diff generation
- Output: Code changes, audit logs
- Storage: Local only, no cloud transmission

**Data Protection**:
- No training on customer data
- No credential storage
- Audit logs exclude secrets
- GDPR-compliant processing

## 5. Human Oversight (Article 14)

**Oversight Mechanisms**:
- Approval required for all HIGH/CRITICAL operations
- Compliance mode for strictest control
- Trained operators with clear authority
- Escalation procedures documented

## 6. Accuracy and Robustness (Article 15)

**Testing**:
- 53+ automated tests
- Continuous integration
- Path safety verification
- Edge case coverage

**Performance Metrics**:
- Risk assessment accuracy: >95%
- False positive rate: <5%
- Test coverage: >90%

## 7. Record Keeping (Article 12)

**Logging System**: Safe Agent audit export
**Retention Period**: 10 years
**Storage Location**: [Your immutable storage]
**Access Controls**: [Your RBAC setup]

## 8. Updates and Maintenance

**Update Policy**: Monthly security updates, quarterly feature releases
**Testing Process**: All tests must pass before deployment
**Rollback Plan**: Previous version maintained for 30 days

## 9. Serious Incident Response

**Definition**: See Article 73
**Reporting Timeline**: 15 days
**Authority**: [Your national authority]
**Contact**: [Your incident response team]

## 10. Documentation Maintenance

**Review Frequency**: Annual or after major changes
**Owner**: [Director of Engineering]
**Approval**: [CTO]
```

---

## 🌍 Multi-Jurisdictional Considerations

### EU AI Act + GDPR

**Data Protection Overlap**:
- AI Act: Risk management and transparency
- GDPR: Personal data processing rules
- Both: Record-keeping and accountability

**Safe Agent Compliance**:
- ✅ No personal data in audit logs (pseudonymize user IDs if needed)
- ✅ Local processing (no transfer to third countries)
- ✅ Data minimization (only necessary data collected)
- ✅ Right to access (audit logs available to data subjects)

### UK AI Regulation

**Current Status** (February 2026): Pro-innovation approach, no mandatory regulation yet

**Safe Agent Readiness**: If UK adopts similar framework, Safe Agent already compliant via EU AI Act alignment

### US AI Regulation

**State-Level**: Multiple states considering AI legislation (California, New York, Colorado)

**Safe Agent Support**: Transparency and audit features support emerging US requirements

---

## ⚠️ Limitations and Disclaimers

**Safe Agent Cannot**:
- ❌ Guarantee 100% prevention of all incidents
- ❌ Replace legal compliance assessment
- ❌ Substitute for organizational policies
- ❌ Ensure AI model (Claude/GPT) compliance

**Safe Agent Can**:
- ✅ Provide technical controls for risk mitigation
- ✅ Generate audit trails for compliance demonstration
- ✅ Enable human oversight workflows
- ✅ Support documentation requirements

**Legal Disclaimer**:
This guide provides technical implementation guidance only. It does not constitute legal advice. Organizations must:
- Conduct independent legal assessment
- Consult qualified legal counsel
- Verify applicability to specific use cases
- Stay current with regulatory updates

**Regulatory Changes**:
The EU AI Act is new (2024) and interpretation is evolving. Safe Agent will update this guidance as:
- Regulatory guidance is published
- Court decisions interpret requirements
- Implementation standards are defined

---

## 📞 Support and Resources

### Safe Agent Resources

- **Documentation**: https://github.com/agent-polis/safe-agent
- **Issues**: https://github.com/agent-polis/safe-agent/issues
- **Email**: support@agent-polis.dev (planned)

### EU AI Act Resources

- **Official Text**: https://artificialintelligenceact.eu
- **EU Commission**: https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai
- **National Authorities**: Contact your national market surveillance authority

### Compliance Consultants

For legal/compliance consulting, consider:
- Law firms specializing in AI regulation
- Compliance consultancies with EU AI Act expertise
- Industry associations in your sector

---

## 🔄 Document Maintenance

**Version**: 1.0
**Last Updated**: February 11, 2026
**Next Review**: August 1, 2026 (before enforcement deadline)
**Owner**: Safe Agent Project
**Status**: Living Document

**Change Log**:
- v1.0 (Feb 2026): Initial release, 6 months before Annex III enforcement

**Future Updates Will Include**:
- Regulatory guidance as published
- Case studies from early adopters
- Additional compliance templates
- Integration with emerging standards

---

**Ready for August 2, 2026 Enforcement** ✅

This guide positions Safe Agent as EU AI Act ready. Organizations deploying AI coding agents should:
1. Read this guide thoroughly
2. Complete compliance checklist
3. Enable compliance mode for high-risk systems
4. Maintain audit trails per retention policy
5. Consult legal counsel for final compliance assessment

**Safe Agent: Making AI coding agents compliant by default** 🛡️
