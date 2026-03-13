# 🔐 Secure-Web-Application-Architecture

Security-focused full-stack web application implementing a Cyberbullying Detection and Behavioral Escalation System with abuse prevention mechanisms, layered defense architecture, secure authentication, authorization controls, and structured security validation aligned with OWASP risk mitigation principles.

## 🏗 Architecture

Frontend: HTML, CSS, JavaScript  
Backend: FastAPI  
Database: PostgreSQL

##  Core Security Features

- JSON Web Token (JWT) Authentication  
- Role-Based Access Control (RBAC)  
- Password Hashing (bcrypt)  
- Password Policy Enforcement  
- Account Lockout (Brute-Force Mitigation)  
- Rate Limiting (SlowAPI)  
- SQL Injection Prevention (SQLAlchemy ORM)  
- Cross-Origin Resource Sharing (CORS) Control  
- Behavioral Escalation & Auto-Ban System  
- Audit Logging & Security Monitoring
  
##  Security Validation

- Static Application Security Testing (SAST) – Bandit  
- Software Composition Analysis (SCA) – pip-audit  
- Dynamic Application Security Testing (DAST) – OWASP ZAP
  
No critical vulnerabilities identified.

See **SECURITY.md** for threat model and detailed testing documentation.

##  Security Principles
Defense in Depth • Least Privilege • Secure Configuration • Server-Side Validation • Abuse Mitigation
