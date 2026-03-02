## 🔐Security Architecture & Validation Report

# 🏗 1️⃣ System Overview

This is a secure web-based application designed using layered security architecture and defense-in-depth principles.

## Architecture Components

- Frontend (HTML/CSS/JavaScript – Vercel)
- Backend API (FastAPI – Railway)
- PostgreSQL Database
- JWT-based Authentication System
- Role-Based Access Control (RBAC)
- Rule-Based Cyberbullying Detection Engine
- Behavioral Escalation & Auto-Ban System

## Core Security Features

- JWT stateless authentication
- Access & refresh token lifecycle
- Password hashing (bcrypt via passlib)
- Password strength validation (frontend + backend)
- Gmail domain validation
- Brute-force protection (account lockout mechanism)
- Role-Based Access Control (Admin/User separation)
- Rate limiting via SlowAPI
- SQL injection protection (ORM-based queries)
- Environment-based secret management
- Security event logging
- HTTPS production deployment
- CORS configuration control

The system processes authentication, text moderation, behavioral enforcement, and administrative review while enforcing strict access control and abuse prevention mechanisms.

# 🧠 2️⃣ Threat Model – Cyberbullying Detection & Escalation System

## Assets Protected

- User credentials (hashed passwords)
- JWT access & refresh tokens
- Admin privileges
- User behavioral violation history
- Security logs
- Environment secrets (JWT_SECRET)

## Threat Actors

- Anonymous internet users
- Malicious registered users
- Brute-force attackers
- Privilege escalation attackers
- Automated bots
- 
## STRIDE-Based Risk Analysis

### 🛑 Spoofing (Identity Attacks)

Mitigations:
- JWT signature validation (HS256)
- Short-lived access tokens
- Password hashing
- Account lockout after 5 failed attempts
- Strong password policy enforcement

Risk Level: Low

### 🛑 Tampering

Mitigations:
- SQLAlchemy ORM (no raw SQL)
- Role extracted from verified JWT
- Admin route protection
- Server-side validation

Risk Level: Low

### 🛑 Repudiation

Mitigations:
- Failed login logging
- Admin access logging
- IP-based event tracking
- Timestamped database records

Risk Level: Low

### 🛑 Information Disclosure

Mitigations:
- Secrets stored in environment variables
- No hardcoded credentials
- HTTPS deployment
- Controlled CORS configuration
- Secure password storage (no plaintext)

Risk Level: Low

### 🛑 Denial of Service (DoS)

Mitigations:
- Rate limiting via SlowAPI
- Endpoint-specific request limits
- Login lockout mechanism
- Behavioral ban system

Risk Level: Medium 

### 🛑 Elevation of Privilege

Mitigations:
- Role-Based Access Control (RBAC)
- Admin-only endpoint enforcement
- JWT validation middleware

Risk Level: Low

Overall System Risk Rating: **Low–Medium**

The system implements defense-in-depth and least privilege principles across all layers.

# 🌐 3️⃣ Dynamic Security Testing (DAST)

## Tool Used: OWASP ZAP

OWASP ZAP was used to perform automated dynamic security testing against:

- Backend API (Railway deployment)
- Frontend application (Vercel deployment)

## Backend Scan Results

- No High severity vulnerabilities detected
- No Medium severity vulnerabilities detected
- No SQL Injection vulnerabilities detected
- No XSS vulnerabilities detected
- No authentication bypass detected
- Only informational cache-control observation

Backend Risk Level: **Low**

## Frontend Scan Results

Informational security header recommendations identified:

- Content Security Policy (CSP) header not set
- X-Content-Type-Options header missing
- Anti-clickjacking header missing
- Cache-control recommendations

No injection, authentication, or sensitive data exposure vulnerabilities were identified.

Frontend Risk Level: **Low**

Conclusion:

The application shows no critical dynamic security vulnerabilities under automated DAST testing.

# 🔐 4️⃣ Security Testing & Hardening

The project incorporates structured security validation aligned with secure development lifecycle principles.

## 🧪 Static Application Security Testing (SAST)

Tool Used: Bandit

Results:

- High Severity Issues: 0
- Medium Severity Issues: 1
- Low Severity Issues: 1

All findings were reviewed manually.  
No exploitable vulnerabilities were identified.

Security areas covered:

- Hardcoded secret detection
- Unsafe function usage
- Injection risks
- Insecure cryptographic patterns

## 📦 Software Composition Analysis (SCA)

Tool Used: pip-audit

Results:

- No critical dependency vulnerabilities detected
- No exploitable high-risk CVEs affecting application logic

Security areas covered:

- CVE-based dependency scanning
- Vulnerable package version detection
- 
## 🛡 Production Hardening Measures

- Secrets stored in environment variables
- JWT_SECRET enforced at application startup
- HTTPS enabled at deployment level
- CORS restricted to trusted frontend domain
- Rate limiting on sensitive endpoints
- Role-based route protection
- Behavioral escalation enforcement

# 🏁 Final Security Posture Statement

The system implements layered security controls across authentication, authorization, abuse prevention, configuration management, and logging.

Major OWASP Top 10 risks (A01–A07) are mitigated through architectural and code-level controls, including:

- JWT-based stateless authentication
- Role-Based Access Control (RBAC)
- Brute-force mitigation and rate limiting
- Secure password storage and validation
- SQL injection prevention via ORM
- Environment-based secret management
- Static (SAST), Dependency (SCA), and Dynamic (DAST) security testing

The system follows defense-in-depth and least privilege principles, resulting in a low-to-moderate overall risk profile appropriate for secure portfolio deployment.
